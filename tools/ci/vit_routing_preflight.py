from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Sequence
import urllib.error
import urllib.request

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_routing import validate_vit_lineage_record
from tools.ci.vit_lineage_source import resolve_candidate_lineage

REGISTER_PATH = Path("registries/development/skills/VIT_ROUTING_COVERAGE_REGISTER_v0_1.json")
SAFE_REF = re.compile(r"[A-Za-z0-9._/-]+")


def _load_json(path: Path) -> Mapping[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise RuntimeError(f"expected JSON object: {path}")
    return raw


def _git(root: Path, args: Sequence[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    return proc.stdout.strip()


def _live_pr_payload(root: Path, event: Mapping[str, Any]) -> Mapping[str, Any]:
    event_pr = event.get("pull_request")
    if not isinstance(event_pr, Mapping):
        raise RuntimeError("pull_request event payload is missing")
    if os.environ.get("GITHUB_ACTIONS", "").lower() != "true":
        return event_pr
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    if not repo or pr_number < 1:
        raise RuntimeError("VIT_LIVE_PR_CONTEXT_MISSING")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ovc-vit-payload-preflight/3",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}", headers=headers, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"VIT_LIVE_PR_RESOLUTION_FAILED:{exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError("VIT_LIVE_PR_PAYLOAD_INVALID")
    return value


def _exception_matches(exception: Mapping[str, Any], *, pr_number: int, head_sha: str, head_branch: str) -> bool:
    if int(exception.get("pr_number", -1)) != pr_number:
        return False
    pinned_sha = str(exception.get("head_sha", "")).strip()
    pinned_branch = str(exception.get("head_branch", "")).strip()
    if pinned_sha:
        return pinned_sha == head_sha
    if pinned_branch:
        return pinned_branch == head_branch and bool(exception.get("self_bootstrap", False))
    return False


def _validate_payload_against_head(root: Path, record: Mapping[str, Any], head_sha: str) -> None:
    pip = record.get("pip")
    if not isinstance(pip, Mapping):
        raise RuntimeError("VIT_PIP_INVALID")
    changes = pip.get("logical_changes")
    if not isinstance(changes, list) or not changes:
        raise RuntimeError("VIT_PIP_CHANGES_INVALID")
    seen: set[str] = set()
    for change in changes:
        if not isinstance(change, Mapping):
            raise RuntimeError("VIT_PIP_CHANGE_INVALID")
        path = str(change.get("path", ""))
        if not path or Path(path).is_absolute() or ".." in Path(path).parts or path in seen:
            raise RuntimeError(f"VIT_PIP_PATH_INVALID:{path}")
        seen.add(path)
        op = str(change.get("op", ""))
        row = _git(root, ["ls-tree", head_sha, "--", path])
        if op == "DELETE":
            if row:
                raise RuntimeError(f"VIT_PIP_DELETE_STILL_PRESENT:{path}")
            continue
        if op not in {"ADD", "MODIFY"}:
            raise RuntimeError(f"VIT_PIP_OP_INVALID:{op}:{path}")
        if not row:
            raise RuntimeError(f"VIT_PIP_HEAD_PATH_MISSING:{path}")
        meta, listed = row.split("\t", 1)
        mode, obj_type, blob_sha = meta.split(" ", 2)
        if listed != path or obj_type not in {"blob", "commit"}:
            raise RuntimeError(f"VIT_PIP_HEAD_ENTRY_INVALID:{path}")
        if blob_sha != str(change.get("blob_sha", "")) or mode != str(change.get("mode", "")):
            raise RuntimeError(f"VIT_PIP_HEAD_BLOB_MISMATCH:{path}")


def check_pull_request_event(*, root: Path, event: Mapping[str, Any]) -> str:
    event_pr = event.get("pull_request")
    if not isinstance(event_pr, Mapping):
        raise RuntimeError("pull_request event payload is missing")
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    event_head = event_pr.get("head")
    if not isinstance(event_head, Mapping):
        raise RuntimeError("pull_request head is missing")
    event_head_sha = str(event_head.get("sha", "")).strip()

    live_pr = _live_pr_payload(root, event)
    head = live_pr.get("head")
    base = live_pr.get("base")
    if not isinstance(head, Mapping) or not isinstance(base, Mapping):
        raise RuntimeError("live pull_request head/base is missing")
    head_sha = str(head.get("sha", "")).strip()
    head_branch = str(head.get("ref", "")).strip()
    base_ref = str(base.get("ref", "")).strip()
    body = str(live_pr.get("body") or "")
    if head_sha != event_head_sha:
        raise RuntimeError(
            f"VIT_SUPERSEDED_EVENT_HEAD: event {event_head_sha}, live {head_sha}; obsolete generation may not acquire assurance"
        )
    if base_ref != "main" or not SAFE_REF.fullmatch(base_ref):
        raise RuntimeError(f"VIT_BASE_REF_INVALID:{base_ref}")

    register = _load_json(root / REGISTER_PATH)
    if register.get("unregistered_bypass_policy") != "FAIL_CLOSED":
        raise RuntimeError("VIT routing register is not fail-closed")
    exceptions = register.get("registered_pr_exceptions", [])
    if not isinstance(exceptions, list):
        raise RuntimeError("registered_pr_exceptions must be a list")
    for exception in exceptions:
        if isinstance(exception, Mapping) and _exception_matches(
            exception, pr_number=pr_number, head_sha=head_sha, head_branch=head_branch
        ):
            if bool(exception.get("siq_bypass_authority", True)):
                raise RuntimeError("registered VIT exception cannot grant SIQ bypass authority")
            return f"REGISTERED_EXCEPTION:{exception.get('exception_class', 'UNKNOWN')}"

    allow_legacy_body = os.environ.get("OVC_VIT_ALLOW_LEGACY_PR_BODY_LINEAGE", "").lower() == "true"
    source = resolve_candidate_lineage(
        root=root,
        head_sha=head_sha,
        body=body,
        require=True,
        allow_legacy_pr_body=allow_legacy_body,
    )
    assert source is not None
    record = source.record
    try:
        lineage = validate_vit_lineage_record(record)
    except (VitContractError, ValueError, TypeError) as exc:
        raise RuntimeError(f"VIT_LINEAGE_INVALID:{exc}") from exc
    if lineage.route_class != "VIT_MANDATORY":
        raise RuntimeError("permanent integration PR lineage must be VIT_MANDATORY")
    _validate_payload_against_head(root, record, head_sha)

    if lineage.late_binding:
        return (
            f"VIT_MANDATORY_LATE_BINDING:{lineage.packet_id}:{lineage.pip_id}:"
            f"NO_PHYSICAL_BASE_BINDING:{source.source}:{source.immutable_ref}"
        )

    return (
        f"VIT_MANDATORY_LEGACY_PAYLOAD_ACCEPTED:{lineage.packet_id}:{lineage.pip_id}:"
        f"PLACEMENT_NON_AUTHORITATIVE:{source.source}:{source.immutable_ref}"
    )


def main() -> int:
    if os.environ.get("GITHUB_EVENT_NAME", "").strip() != "pull_request":
        print("OVC_VIT_ROUTING_PREFLIGHT=PASS NON_PULL_REQUEST")
        return 0
    root = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    event = _load_json(Path(os.environ["GITHUB_EVENT_PATH"]))
    result = check_pull_request_event(root=root, event=event)
    print(f"OVC_VIT_ROUTING_PREFLIGHT=PASS {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
