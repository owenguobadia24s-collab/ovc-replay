from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Sequence
import urllib.error
import urllib.request

from ovc.development.skills.vit_apply import REFERENCE_APPLY_PROFILE
from ovc.development.skills.vit_core import TREE_IDENTITY_PROFILE, VitContractError
from ovc.development.skills.vit_frontier_decoupling import (
    SourceHead,
    build_frontier_lineage,
    classify_frontier_movement,
    compose_pip_tree,
    diff_tree_paths,
    encode_record,
    git_tree,
    tree_is_in_commit_ancestry,
    waiting_predecessor_decision,
)
from ovc.development.skills.vit_routing import validate_vit_lineage_record
from tools.ci.vit_lineage_source import resolve_lineage_source

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
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _tree(root: Path, commitish: str) -> str:
    return _git(root, ["rev-parse", f"{commitish}^{{tree}}"])


def _fetch_commit_if_needed(root: Path, sha: str) -> None:
    proc = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{sha}^{{commit}}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode == 0:
        return
    try:
        _git(root, ["fetch", "--no-tags", "origin", sha])
    except RuntimeError as exc:
        raise RuntimeError("VIT_LIVE_BASE_FETCH_FAILED") from exc


def _live_pr_payload(root: Path, event: Mapping[str, Any]) -> tuple[Mapping[str, Any], bool]:
    """Resolve live PR metadata only for the actual Actions workspace."""
    event_pr = event.get("pull_request")
    if not isinstance(event_pr, Mapping):
        raise RuntimeError("pull_request event payload is missing")
    workspace = os.environ.get("GITHUB_WORKSPACE", "").strip()
    if not workspace or Path(workspace).resolve() != root.resolve():
        return event_pr, False
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    if not repo or pr_number < 1:
        if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            raise RuntimeError("VIT_LIVE_PR_CONTEXT_MISSING")
        return event_pr, False

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ovc-vit-routing-preflight/2",
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
        return event_pr, False
    if not isinstance(value, Mapping):
        raise RuntimeError("VIT_LIVE_PR_PAYLOAD_INVALID")
    return value, True


def _live_base_sha(
    root: Path,
    *,
    base_ref: str,
    event_base_sha: str,
    live_base_sha: str | None = None,
) -> str:
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
    except RuntimeError:
        return event_base_sha
    rows = [row for row in output.splitlines() if row.strip()]
    if not rows:
        return event_base_sha
    candidate = rows[0].split()[0].strip()
    if not re.fullmatch(r"[0-9a-f]{40}", candidate):
        raise RuntimeError("VIT_LIVE_BASE_SHA_INVALID")
    _fetch_commit_if_needed(root, candidate)
    return candidate


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


def _source_head(
    *,
    record: Mapping[str, Any],
    pr_number: int,
    head_sha: str,
    head_tree: str,
    head_branch: str,
) -> SourceHead:
    raw = record.get("source_head")
    if isinstance(raw, Mapping):
        source = SourceHead(**dict(raw))
        if source.commit_sha != head_sha or source.tree_sha != head_tree or source.pr_number != pr_number:
            raise RuntimeError("VIT_SOURCE_HEAD_PROVENANCE_MISMATCH")
        return source
    return SourceHead(
        commit_sha=head_sha,
        tree_sha=head_tree,
        pr_number=pr_number,
        head_ref=head_branch,
    )


def _validate_source_transport(
    *, root: Path, record: Mapping[str, Any], head_tree: str
) -> None:
    generation = record["generation"]
    placement = record["placement"]
    predecessor = generation["predecessor_tree"]
    result = generation["result_tree"]
    if predecessor.get("profile") != TREE_IDENTITY_PROFILE or result.get("profile") != TREE_IDENTITY_PROFILE:
        raise RuntimeError("VIT_LINEAGE_TREE_PROFILE_INVALID")
    predecessor_tree = str(predecessor.get("tree_sha", ""))
    source_result_tree = str(result.get("tree_sha", ""))
    if source_result_tree != head_tree:
        raise RuntimeError("VIT_SOURCE_LINEAGE_RESULT_NOT_PR_HEAD_TREE")
    if placement.get("predecessor_tree") != predecessor_tree or placement.get("result_tree") != source_result_tree:
        raise RuntimeError("VIT_SOURCE_LINEAGE_PLACEMENT_TREE_MISMATCH")
    if placement.get("apply_profile") != REFERENCE_APPLY_PROFILE:
        raise RuntimeError("VIT_LINEAGE_APPLY_PROFILE_NOT_REFERENCE")
    pip = record["pip"]
    logical_changes = pip.get("logical_changes")
    if not isinstance(logical_changes, list) or not logical_changes:
        raise RuntimeError("VIT_LINEAGE_PIP_CHANGES_INVALID")
    composed_tree = compose_pip_tree(root, predecessor_tree, logical_changes)
    if composed_tree != head_tree:
        raise RuntimeError("VIT_SOURCE_PIP_DOES_NOT_REPRODUCE_PR_HEAD_TREE")


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

    live_pr, live_pr_resolved = _live_pr_payload(root, event)
    head = live_pr.get("head")
    base = live_pr.get("base")
    if not isinstance(head, Mapping) or not isinstance(base, Mapping):
        raise RuntimeError("live pull_request head/base is missing")
    head_sha = str(head.get("sha", "")).strip()
    head_branch = str(head.get("ref", "")).strip()
    base_ref = str(base.get("ref", "")).strip()
    live_base_hint = str(base.get("sha", "")).strip() if live_pr_resolved else None
    body = str(live_pr.get("body") or "")

    if head_sha != event_head_sha:
        raise RuntimeError(
            f"VIT_SUPERSEDED_EVENT_HEAD: event {event_head_sha}, live {head_sha}; obsolete source generation may not acquire assurance"
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

    source = resolve_lineage_source(body, require=True)
    assert source is not None
    record = source.record
    try:
        lineage = validate_vit_lineage_record(record)
    except (VitContractError, ValueError, TypeError) as exc:
        raise RuntimeError(f"VIT_LINEAGE_INVALID: {exc}") from exc
    if lineage.route_class != "VIT_MANDATORY":
        raise RuntimeError("permanent integration PR lineage must be VIT_MANDATORY")

    head_tree = _tree(root, head_sha)
    _validate_source_transport(root=root, record=record, head_tree=head_tree)
    source_head = _source_head(
        record=record,
        pr_number=pr_number,
        head_sha=head_sha,
        head_tree=head_tree,
        head_branch=head_branch,
    )

    live_base_sha = _live_base_sha(
        root,
        base_ref=base_ref,
        event_base_sha=event_base_sha,
        live_base_sha=live_base_hint,
    )
    live_base_tree = _tree(root, live_base_sha)
    source_predecessor_tree = str(record["generation"]["predecessor_tree"]["tree_sha"])

    if source_predecessor_tree == live_base_tree or tree_is_in_commit_ancestry(
        root, tree_sha=source_predecessor_tree, descendant_commit=live_base_sha
    ):
        changed_paths = diff_tree_paths(root, source_predecessor_tree, live_base_tree)
        movement = classify_frontier_movement(
            pip=record["pip"],
            source_predecessor_tree=source_predecessor_tree,
            current_predecessor_tree=live_base_tree,
            changed_paths=changed_paths,
        )
        if movement.disposition in {"PAYLOAD_REBUILD_REQUIRED", "AUTHORITY_REVIEW_REQUIRED"}:
            raise RuntimeError(
                f"VIT_FRONTIER_RECOMPOSITION_BLOCKED:{movement.disposition}:"
                f"{movement.decision_id}"
            )
        prospective_tree = compose_pip_tree(
            root, live_base_tree, record["pip"]["logical_changes"]
        )
        frontier = build_frontier_lineage(
            source_lineage_record=record,
            source_head=source_head,
            predecessor_commit=live_base_sha,
            predecessor_tree=live_base_tree,
            prospective_result_tree=prospective_tree,
            movement=movement,
        )
        current = validate_vit_lineage_record(frontier)
        print("OVC_VIT_FRONTIER_LINEAGE_B64=" + encode_record(frontier))
        return (
            f"VIT_MANDATORY:{current.packet_id}:{current.pip_id}:"
            f"source={lineage.generation_id}:frontier={current.generation_id}:"
            f"placement={current.placement_id}:movement={movement.disposition}:"
            f"same_pr=true:{source.source}:{source.immutable_ref}"
        )

    waiting = waiting_predecessor_decision(
        source_predecessor_tree=source_predecessor_tree,
        current_main_tree=live_base_tree,
    )
    print(
        "OVC_VIT_FRONTIER_WAITING_PREDECESSOR="
        f"{waiting.decision_id}:{source_predecessor_tree}"
    )
    return (
        f"VIT_MANDATORY:{lineage.packet_id}:{lineage.pip_id}:"
        f"source={lineage.generation_id}:placement={lineage.placement_id}:"
        "movement=WAITING_VIT_PREDECESSOR:same_pr=true:"
        f"{source.source}:{source.immutable_ref}"
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
