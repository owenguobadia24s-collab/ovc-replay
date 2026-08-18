from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping
import urllib.error
import urllib.request

from ovc.development.skills.vit_assurance_decoupling import validate_aa0_reuse_authorization
from ovc.development.skills.vit_routing import validate_vit_lineage_record
from tools.ci.vit_lineage_source import resolve_lineage_source

REUSE = re.compile(r"(?im)^VIT-AA0-Reuse-B64:\s*([A-Za-z0-9_\-=]+)\s*$")


def _decode(marker: re.Pattern[str], body: str, label: str) -> Mapping[str, Any] | None:
    match = marker.search(body)
    if not match:
        return None
    token = match.group(1)
    token += "=" * ((4 - len(token) % 4) % 4)
    try:
        value = json.loads(base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"{label}_INVALID_ENCODING:{exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label}_INVALID_OBJECT")
    return value


def _write_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")
    print(f"OVC_VIT_ASSURANCE_{name.upper()}={value}")


def _live_pr_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Resolve the current PR generation/body in Actions; event data is provenance only."""
    event_pr = event.get("pull_request")
    if not isinstance(event_pr, Mapping):
        raise RuntimeError("pull_request event payload is missing")
    if os.environ.get("GITHUB_ACTIONS", "").lower() != "true":
        return event_pr

    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    if not repo or pr_number < 1:
        raise RuntimeError("VIT_ASSURANCE_LIVE_PR_CONTEXT_MISSING")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ovc-vit-assurance-preflight/2",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}",
        headers=headers,
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"VIT_ASSURANCE_LIVE_PR_RESOLUTION_FAILED:{exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError("VIT_ASSURANCE_LIVE_PR_PAYLOAD_INVALID")
    return value


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name != "pull_request":
        sha = os.environ.get("GITHUB_SHA", "NON_PR")
        _write_output("aa0_identity", sha)
        _write_output("generation_id", sha)
        _write_output("pip_id", sha)
        _write_output("lineage_source", "NON_PR")
        _write_output("lineage_ref", sha)
        _write_output("aa0_reuse_authorized", "false")
        _write_output("aa0_reuse_reason", "NON_PULL_REQUEST")
        _write_output("assurance_scope", "A0_PIP_ONLY")
        return 0

    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    event_pr = event.get("pull_request") or {}
    event_head_sha = str((event_pr.get("head") or {}).get("sha") or "")
    pr = _live_pr_payload(event)
    body = str(pr.get("body") or "")
    head_sha = str((pr.get("head") or {}).get("sha") or "")
    if head_sha != event_head_sha:
        raise RuntimeError(
            f"VIT_ASSURANCE_SUPERSEDED_EVENT_HEAD:event {event_head_sha}, live {head_sha}; "
            "obsolete source generation may not acquire A0 assurance identity"
        )

    lineage_source = resolve_lineage_source(body, require=False)
    reuse_record = _decode(REUSE, body, "VIT_AA0_REUSE")

    if lineage_source is None:
        if reuse_record is not None:
            raise RuntimeError("AA0_REUSE_WITHOUT_VIT_LINEAGE")
        _write_output("aa0_identity", head_sha)
        _write_output("generation_id", head_sha)
        _write_output("pip_id", head_sha)
        _write_output("lineage_source", "REGISTERED_EXCEPTION_OR_NO_LINEAGE")
        _write_output("lineage_ref", head_sha)
        _write_output("aa0_reuse_authorized", "false")
        _write_output("aa0_reuse_reason", "REGISTERED_EXCEPTION_OR_NO_LINEAGE")
        _write_output("assurance_scope", "A0_SOURCE_HEAD_EXCEPTION")
        return 0

    lineage_record = lineage_source.record
    lineage = validate_vit_lineage_record(lineage_record)
    _write_output("aa0_identity", lineage.pip_id)
    _write_output("generation_id", lineage.generation_id)
    _write_output("pip_id", lineage.pip_id)
    _write_output("lineage_source", lineage_source.source)
    _write_output("lineage_ref", lineage_source.immutable_ref)
    _write_output("source_head_sha", head_sha)
    _write_output("assurance_scope", "A0_PIP_ONLY")
    print(
        "OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_DEFERRED=SIQ_PHYSICAL_LANE; "
        "A0 is PIP-bound and does not freeze current main."
    )

    if reuse_record is None:
        _write_output("aa0_reuse_authorized", "false")
        _write_output("aa0_reuse_reason", "NO_REUSE_AUTHORIZATION")
        return 0

    validate_aa0_reuse_authorization(reuse_record, current_lineage=lineage_record)
    _write_output("aa0_reuse_authorized", "true")
    _write_output("aa0_reuse_reason", "PLACEMENT_ONLY_PIP_REUSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
