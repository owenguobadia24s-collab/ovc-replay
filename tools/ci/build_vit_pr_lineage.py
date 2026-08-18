from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Sequence

from ovc.development.skills.vit_apply import REFERENCE_APPLY_PROFILE
from ovc.development.skills.vit_completion_policy import validate_non_churning_completion_transition
from ovc.development.skills.vit_routing import build_vit_lineage_record

SHA64 = re.compile(r"^[0-9a-f]{64}$")


def _git(repo: Path, args: Sequence[str], *, binary: bool = False):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
    )
    return proc.stdout if binary else proc.stdout.strip()


def _ls_tree_entry(repo: Path, treeish: str, path: str) -> tuple[str, str, str] | None:
    raw = _git(repo, ["ls-tree", treeish, "--", path])
    if not raw:
        return None
    first = raw.splitlines()[0]
    meta, listed_path = first.split("\t", 1)
    if listed_path != path:
        raise RuntimeError(f"unexpected ls-tree path {listed_path!r} for {path!r}")
    mode, object_type, object_sha = meta.split(" ", 2)
    return mode, object_type, object_sha


def build_logical_changes(repo: Path, base: str, head: str) -> list[dict[str, str]]:
    raw = _git(repo, ["diff", "--name-only", "--no-renames", "-z", base, head], binary=True)
    paths = [chunk.decode("utf-8") for chunk in raw.split(b"\0") if chunk]
    changes: list[dict[str, str]] = []
    for path in sorted(set(paths)):
        before = _ls_tree_entry(repo, base, path)
        after = _ls_tree_entry(repo, head, path)
        if before is None and after is None:
            raise RuntimeError(f"changed path absent from both trees: {path}")
        if after is None:
            changes.append({"op":"DELETE","path":path})
            continue
        mode, object_type, object_sha = after
        if object_type not in {"blob", "commit"}:
            raise RuntimeError(f"unsupported Git object type {object_type!r} for {path}")
        op = "ADD" if before is None else "MODIFY"
        changes.append({"op":op,"path":path,"blob_sha":object_sha,"mode":mode})
    if not changes:
        raise RuntimeError("PIP logical changes must not be empty")
    return changes


def encode_lineage(record: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def build_record(
    *,
    repo: Path,
    base: str,
    head: str,
    programme_id: str,
    packet_id: str,
    authority_manifest_id: str,
    dependency_frontier_id: str,
    train_generation_id: str,
    ordinal: int,
    completion_transition: Mapping[str, Any],
    dependency_footprint: Mapping[str, Any] | None = None,
    pr_number: int | None = None,
    head_ref: str | None = None,
) -> dict[str, Any]:
    if not SHA64.fullmatch(authority_manifest_id) or not SHA64.fullmatch(dependency_frontier_id):
        raise RuntimeError("authority/dependency identities must be lowercase SHA-256 values")
    validate_non_churning_completion_transition(
        packet_id=packet_id,
        completion_transition=completion_transition,
    )
    base_commit = _git(repo, ["rev-parse", f"{base}^{{commit}}"])
    head_commit = _git(repo, ["rev-parse", f"{head}^{{commit}}"])
    base_tree = _git(repo, ["rev-parse", f"{base}^{{tree}}"])
    head_tree = _git(repo, ["rev-parse", f"{head}^{{tree}}"])
    pip = {
        "schema_version":"packet-integration-payload/v0.1",
        "programme_id":programme_id,
        "packet_id":packet_id,
        "logical_changes":build_logical_changes(repo, base, head),
        "authority_manifest_id":authority_manifest_id,
        "dependency_frontier_id":dependency_frontier_id,
        "completion_transition":dict(completion_transition),
    }
    if dependency_footprint is not None:
        if not isinstance(dependency_footprint, Mapping):
            raise RuntimeError("dependency footprint must be a JSON object")
        pip["dependency_footprint"] = dict(dependency_footprint)
    source_head = None
    if pr_number is not None:
        if pr_number < 1 or not str(head_ref or "").strip():
            raise RuntimeError("--pr-number requires --head-ref and a positive PR number")
        source_head = {
            "schema": "ovc-vit-source-head/v1",
            "commit_sha": head_commit,
            "tree_sha": head_tree,
            "pr_number": int(pr_number),
            "head_ref": str(head_ref),
            "development_base_commit": base_commit,
            "development_base_tree": base_tree,
        }
    return build_vit_lineage_record(
        programme_id=programme_id,
        packet_id=packet_id,
        pip_identity_payload=pip,
        train_generation_id=train_generation_id,
        ordinal=ordinal,
        predecessor_tree_sha=base_tree,
        result_tree_sha=head_tree,
        apply_profile=REFERENCE_APPLY_PROFILE,
        source_head=source_head,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical inline VIT lineage for a permanent PR candidate.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--programme-id", required=True)
    parser.add_argument("--packet-id", required=True)
    parser.add_argument("--authority-manifest-id", required=True)
    parser.add_argument("--dependency-frontier-id", required=True)
    parser.add_argument("--train-generation-id", required=True)
    parser.add_argument("--ordinal", type=int, required=True)
    parser.add_argument("--completion-transition-json", default='{"status":"COMPLETED"}')
    parser.add_argument("--dependency-footprint-json")
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--head-ref")
    args = parser.parse_args()
    transition = json.loads(args.completion_transition_json)
    if not isinstance(transition, Mapping):
        raise SystemExit("completion transition must be a JSON object")
    footprint = None
    if args.dependency_footprint_json:
        footprint = json.loads(args.dependency_footprint_json)
        if not isinstance(footprint, Mapping):
            raise SystemExit("dependency footprint must be a JSON object")
    record = build_record(
        repo=Path(args.repo).resolve(),
        base=args.base,
        head=args.head,
        programme_id=args.programme_id,
        packet_id=args.packet_id,
        authority_manifest_id=args.authority_manifest_id,
        dependency_frontier_id=args.dependency_frontier_id,
        train_generation_id=args.train_generation_id,
        ordinal=args.ordinal,
        completion_transition=transition,
        dependency_footprint=footprint,
        pr_number=args.pr_number,
        head_ref=args.head_ref,
    )
    print(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print(f"VIT-Lineage-B64: {encode_lineage(record)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
