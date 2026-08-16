from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_routing import load_vit_lineage

REGISTER_PATH = Path("registries/development/skills/VIT_ROUTING_COVERAGE_REGISTER_v0_1.json")
LINEAGE_MARKER = re.compile(r"(?im)^VIT-Lineage-Ref:\s*(\S+)\s*$")


def _load_json(path: Path) -> Mapping[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise RuntimeError(f"expected JSON object: {path}")
    return raw


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


def check_pull_request_event(*, root: Path, event: Mapping[str, Any]) -> str:
    pr = event.get("pull_request")
    if not isinstance(pr, Mapping):
        raise RuntimeError("pull_request event payload is missing")
    pr_number = int(event.get("number", pr.get("number", -1)))
    head = pr.get("head")
    if not isinstance(head, Mapping):
        raise RuntimeError("pull_request head is missing")
    head_sha = str(head.get("sha", "")).strip()
    head_branch = str(head.get("ref", "")).strip()
    body = str(pr.get("body") or "")

    register = _load_json(root / REGISTER_PATH)
    if register.get("unregistered_bypass_policy") != "FAIL_CLOSED":
        raise RuntimeError("VIT routing register is not fail-closed")

    exceptions = register.get("registered_pr_exceptions", [])
    if not isinstance(exceptions, list):
        raise RuntimeError("registered_pr_exceptions must be a list")
    for exception in exceptions:
        if isinstance(exception, Mapping) and _exception_matches(
            exception,
            pr_number=pr_number,
            head_sha=head_sha,
            head_branch=head_branch,
        ):
            if bool(exception.get("siq_bypass_authority", True)):
                raise RuntimeError("registered VIT exception cannot grant SIQ bypass authority")
            return f"REGISTERED_EXCEPTION:{exception.get('exception_class', 'UNKNOWN')}"

    match = LINEAGE_MARKER.search(body)
    if not match:
        raise RuntimeError("VIT_LINEAGE_REQUIRED: add `VIT-Lineage-Ref: <repository-relative-json-path>` to the PR body")
    lineage_ref = match.group(1)
    try:
        lineage = load_vit_lineage(root, lineage_ref)
    except (VitContractError, ValueError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"VIT_LINEAGE_INVALID: {exc}") from exc
    if lineage.route_class != "VIT_MANDATORY":
        raise RuntimeError("permanent integration PR lineage must be VIT_MANDATORY")
    return f"VIT_MANDATORY:{lineage.packet_id}:{lineage.placement_id}"


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "").strip()
    if event_name != "pull_request":
        print("OVC_VIT_ROUTING_PREFLIGHT=PASS NON_PULL_REQUEST")
        return 0
    event_path = Path(os.environ["GITHUB_EVENT_PATH"])
    root = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    event = _load_json(event_path)
    result = check_pull_request_event(root=root, event=event)
    print(f"OVC_VIT_ROUTING_PREFLIGHT=PASS {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
