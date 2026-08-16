from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Mapping, Sequence
import urllib.error
import urllib.request

from ovc.development.skills.vit_apply import REFERENCE_APPLY_PROFILE
from ovc.development.skills.vit_core import TREE_IDENTITY_PROFILE, VitContractError
from ovc.development.skills.vit_routing import validate_vit_lineage_record

REGISTER_PATH = Path("registries/development/skills/VIT_ROUTING_COVERAGE_REGISTER_v0_1.json")
LINEAGE_B64_MARKER = re.compile(r"(?im)^VIT-Lineage-B64:\s*([A-Za-z0-9_\-=]+)\s*$")
SAFE_REF = re.compile(r"[A-Za-z0-9._/-]+")


def _load_json(path: Path) -> Mapping[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise RuntimeError(f"expected JSON object: {path}")
    return raw


def _git(root: Path, args: Sequence[str], *, env: Mapping[str, str] | None = None) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=dict(os.environ, **dict(env or {})),
        timeout=30,
    )
    return proc.stdout.strip()


def _tree(root: Path, commitish: str) -> str:
    return _git(root, ["rev-parse", f"{commitish}^{{tree}}"])


def _fetch_commit_if_needed(root: Path, sha: str) -> None:
    try:
        _git(root, ["cat-file", "-e", f"{sha}^{{commit}}"])
        return
    except subprocess.CalledProcessError:
        pass
    try:
        _git(root, ["fetch", "--no-tags", "--depth=1", "origin", sha])
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("VIT_LIVE_BASE_FETCH_FAILED") from exc


def _live_pr_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Resolve live PR metadata in Actions; event payload remains provenance only."""
    event_pr = event.get("pull_request")
    if not isinstance(event_pr, Mapping):
        raise RuntimeError("pull_request event payload is missing")
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    if not repo or pr_number < 1:
        return event_pr

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ovc-vit-routing-preflight/1",
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
        if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            raise RuntimeError(f"VIT_LIVE_PR_RESOLUTION_FAILED:{exc}") from exc
        return event_pr
    if not isinstance(value, Mapping):
        raise RuntimeError("VIT_LIVE_PR_PAYLOAD_INVALID")
    return value


def _live_base_sha(root: Path, *, base_ref: str, event_base_sha: str, live_base_sha: str | None = None) -> str:
    """Resolve current base head; event-time base remains provenance/fallback only."""
    if not base_ref or not SAFE_REF.fullmatch(base_ref) or base_ref.startswith("/") or ".." in Path(base_ref).parts:
        raise RuntimeError(f"VIT_LIVE_BASE_REF_INVALID:{base_ref!r}")
    candidate = str(live_base_sha or "").strip()
    if candidate:
        if not re.fullmatch(r"[0-9a-f]{40}", candidate):
            raise RuntimeError("VIT_LIVE_BASE_SHA_INVALID")
        _fetch_commit_if_needed(root, candidate)
        return candidate
    try:
        output = _git(root, ["ls-remote", "--heads", "origin", f"refs/heads/{base_ref}"])
    except subprocess.CalledProcessError:
        return event_base_sha
    rows = [row for row in output.splitlines() if row.strip()]
    if not rows:
        return event_base_sha
    candidate = rows[0].split()[0].strip()
    if not re.fullmatch(r"[0-9a-f]{40}", candidate):
        raise RuntimeError("VIT_LIVE_BASE_SHA_INVALID")
    _fetch_commit_if_needed(root, candidate)
    return candidate


def _safe_path(raw: object) -> str:
    value = str(raw or "")
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or value == ".git" or value.startswith(".git/"):
        raise RuntimeError(f"unsafe PIP path {value!r}")
    return value.replace("\\", "/")


def _compose_pip_tree(root: Path, predecessor_tree: str, logical_changes: Sequence[Mapping[str, Any]]) -> str:
    """Reference-apply the identity-bearing PIP changes and return the exact Git tree."""
    with tempfile.TemporaryDirectory() as td:
        env = {"GIT_INDEX_FILE": str(Path(td) / "index")}
        _git(root, ["read-tree", predecessor_tree], env=env)
        seen: set[str] = set()
        for change in logical_changes:
            path = _safe_path(change.get("path"))
            if path in seen:
                raise RuntimeError(f"duplicate PIP path mutation: {path}")
            seen.add(path)
            op = str(change.get("op", ""))
            if op == "DELETE":
                _git(root, ["update-index", "--force-remove", "--", path], env=env)
                continue
            if op not in {"ADD", "MODIFY"}:
                raise RuntimeError(f"unsupported PIP op {op!r} for {path}")
            blob_sha = str(change.get("blob_sha", ""))
            mode = str(change.get("mode", "100644"))
            if not re.fullmatch(r"[0-9a-f]{40}", blob_sha):
                raise RuntimeError(f"invalid PIP blob SHA for {path}")
            if mode not in {"100644", "100755", "120000", "160000"}:
                raise RuntimeError(f"invalid PIP mode for {path}: {mode}")
            object_type = "commit" if mode == "160000" else "blob"
            _git(root, ["cat-file", "-e", f"{blob_sha}^{{{object_type}}}"])
            _git(root, ["update-index", "--add", "--cacheinfo", mode, blob_sha, path], env=env)
        return _git(root, ["write-tree"], env=env)


def _decode_lineage(body: str) -> Mapping[str, Any]:
    match = LINEAGE_B64_MARKER.search(body)
    if not match:
        raise RuntimeError("VIT_LINEAGE_REQUIRED: add `VIT-Lineage-B64: <urlsafe-base64-canonical-lineage-json>` to the PR body")
    token = match.group(1)
    try:
        token += "=" * ((4 - len(token) % 4) % 4)
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        record = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"VIT_LINEAGE_INVALID_ENCODING: {exc}") from exc
    if not isinstance(record, Mapping):
        raise RuntimeError("VIT_LINEAGE_INVALID: decoded lineage must be a JSON object")
    return record


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
    event_pr = event.get("pull_request")
    if not isinstance(event_pr, Mapping):
        raise RuntimeError("pull_request event payload is missing")
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    event_head = event_pr.get("head")
    event_base = event_pr.get("base")
    if not isinstance(event_head, Mapping) or not isinstance(event_base, Mapping):
        raise RuntimeError("pull_request head/base is missing")
    event_head_sha = str(event_head.get("sha", "")).strip()
    event_base_sha = str(event_base.get("sha", "")).strip()

    live_pr = _live_pr_payload(event)
    head = live_pr.get("head")
    base = live_pr.get("base")
    if not isinstance(head, Mapping) or not isinstance(base, Mapping):
        raise RuntimeError("live pull_request head/base is missing")
    head_sha = str(head.get("sha", "")).strip()
    head_branch = str(head.get("ref", "")).strip()
    base_ref = str(base.get("ref", "")).strip()
    live_base_hint = str(base.get("sha", "")).strip()
    body = str(live_pr.get("body") or "")

    if head_sha != event_head_sha:
        raise RuntimeError(
            f"VIT_SUPERSEDED_EVENT_HEAD: event {event_head_sha}, live {head_sha}; obsolete generation may not acquire assurance"
        )

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

    record = _decode_lineage(body)
    try:
        lineage = validate_vit_lineage_record(record)
    except (VitContractError, ValueError, TypeError) as exc:
        raise RuntimeError(f"VIT_LINEAGE_INVALID: {exc}") from exc
    if lineage.route_class != "VIT_MANDATORY":
        raise RuntimeError("permanent integration PR lineage must be VIT_MANDATORY")

    generation = record["generation"]
    placement = record["placement"]
    predecessor = generation["predecessor_tree"]
    result = generation["result_tree"]
    if predecessor.get("profile") != TREE_IDENTITY_PROFILE or result.get("profile") != TREE_IDENTITY_PROFILE:
        raise RuntimeError("VIT_LINEAGE_TREE_PROFILE_INVALID")
    live_base_sha = _live_base_sha(
        root,
        base_ref=base_ref,
        event_base_sha=event_base_sha,
        live_base_sha=live_base_hint,
    )
    base_tree = _tree(root, live_base_sha)
    head_tree = _tree(root, head_sha)
    if predecessor.get("tree_sha") != base_tree:
        raise RuntimeError("VIT_REANCHOR_REQUIRED:VIT_LINEAGE_PREDECESSOR_NOT_LIVE_PR_BASE_TREE")
    if result.get("tree_sha") != head_tree:
        raise RuntimeError("VIT_LINEAGE_RESULT_NOT_PR_HEAD_TREE")
    if placement.get("predecessor_tree") != base_tree or placement.get("result_tree") != head_tree:
        raise RuntimeError("VIT_LINEAGE_PLACEMENT_TREE_NOT_PR_TREE")
    if placement.get("apply_profile") != REFERENCE_APPLY_PROFILE:
        raise RuntimeError("VIT_LINEAGE_APPLY_PROFILE_NOT_REFERENCE")

    pip = record["pip"]
    logical_changes = pip.get("logical_changes")
    if not isinstance(logical_changes, list) or not logical_changes:
        raise RuntimeError("VIT_LINEAGE_PIP_CHANGES_INVALID")
    composed_tree = _compose_pip_tree(root, base_tree, logical_changes)
    if composed_tree != head_tree:
        raise RuntimeError("VIT_LINEAGE_PIP_DOES_NOT_REPRODUCE_PR_HEAD_TREE")

    base_note = "LIVE_BASE" if live_base_sha != event_base_sha else "EVENT_BASE_CURRENT"
    body_note = "LIVE_PR_BODY"
    return (
        f"VIT_MANDATORY:{lineage.packet_id}:{lineage.pip_id}:{lineage.generation_id}:"
        f"{lineage.placement_id}:{base_note}:{body_note}"
    )


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
