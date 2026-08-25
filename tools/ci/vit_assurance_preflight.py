from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping
import urllib.error
import urllib.request

from ovc.development.skills.vit_assurance_decoupling import validate_aa0_reuse_authorization
from ovc.development.skills.vit_local_completion_executor import build_live_transaction_freeze, encode_freeze_marker
from ovc.development.skills.vit_routing import validate_vit_lineage_record
from ovc.development.skills.vit_core import VitContractError
from tools.ci.vit_lineage_source import resolve_candidate_lineage
from tools.ci.vit_no_late_surprises import compile_prequalification

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


def _git_tree(root: Path, commit: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{commit}^{{tree}}"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "VIT_ASSURANCE_GIT_TREE_RESOLUTION_FAILED")
    return proc.stdout.strip()


def _emit_prewrite_freeze(*, event: Mapping[str, Any], pr: Mapping[str, Any], lineage_record: Mapping[str, Any]) -> None:
    head = pr.get("head")
    base = pr.get("base")
    if not isinstance(head, Mapping) or not isinstance(base, Mapping):
        raise RuntimeError("VIT_ASSURANCE_LIVE_PR_HEAD_BASE_MISSING")
    root = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    freeze = build_live_transaction_freeze(
        lineage_record=lineage_record,
        pr_number=int(event.get("number", pr.get("number", -1))),
        base_sha=str(base.get("sha", "")),
        head_sha=str(head.get("sha", "")),
        base_tree=_git_tree(root, str(base.get("sha", ""))),
        head_tree=_git_tree(root, str(head.get("sha", ""))),
        workflow_run_id=os.environ.get("GITHUB_RUN_ID", ""),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", ""),
    )
    print(encode_freeze_marker(freeze))


def _live_pr_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
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
        "User-Agent": "ovc-vit-assurance-preflight/3",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com/repos/{repo}/pulls/{pr_number}", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"VIT_ASSURANCE_LIVE_PR_RESOLUTION_FAILED:{exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError("VIT_ASSURANCE_LIVE_PR_PAYLOAD_INVALID")
    return value


def main() -> int:
    if os.environ.get("GITHUB_EVENT_NAME", "") != "pull_request":
        sha = os.environ.get("GITHUB_SHA", "NON_PR")
        for name in ("aa0_identity", "generation_id", "pip_id", "lineage_ref", "qualification_id"):
            _write_output(name, sha)
        _write_output("lineage_source", "NON_PR")
        _write_output("aa0_reuse_authorized", "false")
        _write_output("aa0_reuse_reason", "NON_PULL_REQUEST")
        return 0

    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    event_pr = event.get("pull_request")
    event_pr = event_pr if isinstance(event_pr, Mapping) else {}
    event_head_sha = str((event_pr.get("head") or {}).get("sha") or "")
    pr = _live_pr_payload(event)
    body = str(pr.get("body") or "")
    head_sha = str((pr.get("head") or {}).get("sha") or "")
    if head_sha != event_head_sha:
        raise RuntimeError(
            f"VIT_ASSURANCE_SUPERSEDED_EVENT_HEAD:event {event_head_sha}, live {head_sha}; obsolete generation may not acquire assurance identity"
        )

    root = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    allow_legacy_body = os.environ.get("OVC_VIT_ALLOW_LEGACY_PR_BODY_LINEAGE", "").lower() == "true"
    lineage_source = resolve_candidate_lineage(
        root=root,
        head_sha=head_sha,
        body=body,
        require=False,
        allow_legacy_pr_body=allow_legacy_body,
    )
    reuse_record = _decode(REUSE, body, "VIT_AA0_REUSE")
    if lineage_source is None:
        if reuse_record is not None:
            raise RuntimeError("AA0_REUSE_WITHOUT_VIT_QUALIFICATION")
        for name in ("aa0_identity", "generation_id", "pip_id", "lineage_ref", "qualification_id"):
            _write_output(name, head_sha)
        _write_output("lineage_source", "REGISTERED_EXCEPTION_OR_NO_QUALIFICATION")
        _write_output("aa0_reuse_authorized", "false")
        _write_output("aa0_reuse_reason", "REGISTERED_EXCEPTION_OR_NO_QUALIFICATION")
        return 0

    lineage_record = lineage_source.record
    lineage = validate_vit_lineage_record(lineage_record)
    if lineage.late_binding:
        prequalification = compile_prequalification(
            root=root,
            head_sha=head_sha,
            lineage_record=lineage_record,
        )
        print(f"OVC_NO_LATE_SURPRISES_PREFLIGHT=PASS {prequalification['receipt_id']}")
    else:
        print("OVC_NO_LATE_SURPRISES_PREFLIGHT=LEGACY_PLACEMENT_REPLAY_ONLY")
    _write_output("aa0_identity", lineage.pip_id)
    _write_output("generation_id", lineage_source.immutable_ref)
    _write_output("pip_id", lineage.pip_id)
    _write_output("lineage_source", lineage_source.source)
    _write_output("lineage_ref", lineage_source.immutable_ref)
    _write_output("qualification_id", lineage_source.immutable_ref)

    if lineage.late_binding:
        print("OVC_VIT_PREWRITE_FREEZE_DEFERRED=LATE_BINDING_NO_PHYSICAL_PLACEMENT")
    else:
        try:
            _emit_prewrite_freeze(event=event, pr=pr, lineage_record=lineage_record)
        except VitContractError as exc:
            if "PREDECESSOR_TREE_MISMATCH" not in str(exc) and "RESULT_TREE_MISMATCH" not in str(exc):
                raise
            print(f"OVC_VIT_PREWRITE_FREEZE_DEFERRED=LEGACY_PLACEMENT_SENSITIVE:{exc}")

    if reuse_record is None:
        _write_output("aa0_reuse_authorized", "false")
        _write_output("aa0_reuse_reason", "NO_REUSE_AUTHORIZATION")
        return 0
    if lineage.late_binding:
        _write_output("aa0_reuse_authorized", "false")
        _write_output("aa0_reuse_reason", "LATE_BINDING_PIP_STABLE_NO_PLACEMENT_REUSE_NEEDED")
        return 0

    validate_aa0_reuse_authorization(reuse_record, current_lineage=lineage_record)
    _write_output("aa0_reuse_authorized", "true")
    _write_output("aa0_reuse_reason", "LEGACY_PLACEMENT_ONLY_PIP_REUSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
