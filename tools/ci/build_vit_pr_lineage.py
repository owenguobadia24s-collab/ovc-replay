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
from ovc.development.skills.vit_routing import (
    build_vit_lineage_record,
    build_vit_payload_lineage_record,
)
from tools.ci.vit_qualification_store import (
    build_qualification_envelope,
    publish_qualification_envelope,
)

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
            changes.append({"op": "DELETE", "path": path})
            continue
        mode, object_type, object_sha = after
        if object_type not in {"blob", "commit"}:
            raise RuntimeError(f"unsupported Git object type {object_type!r} for {path}")
        op = "ADD" if before is None else "MODIFY"
        changes.append({"op": op, "path": path, "blob_sha": object_sha, "mode": mode})
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
    completion_transition: Mapping[str, Any],
    legacy_placement: bool = False,
    train_generation_id: str = "LEGACY",
    ordinal: int = 0,
) -> dict[str, Any]:
    if not SHA64.fullmatch(authority_manifest_id) or not SHA64.fullmatch(dependency_frontier_id):
        raise RuntimeError("authority/dependency identities must be lowercase SHA-256 values")
    validate_non_churning_completion_transition(
        packet_id=packet_id,
        completion_transition=completion_transition,
    )
    pip = {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": programme_id,
        "packet_id": packet_id,
        "logical_changes": build_logical_changes(repo, base, head),
        "authority_manifest_id": authority_manifest_id,
        "dependency_frontier_id": dependency_frontier_id,
        "completion_transition": dict(completion_transition),
    }
    if not legacy_placement:
        return build_vit_payload_lineage_record(
            programme_id=programme_id,
            packet_id=packet_id,
            pip_identity_payload=pip,
        )

    base_tree = _git(repo, ["rev-parse", f"{base}^{{tree}}"])
    head_tree = _git(repo, ["rev-parse", f"{head}^{{tree}}"])
    return build_vit_lineage_record(
        programme_id=programme_id,
        packet_id=packet_id,
        pip_identity_payload=pip,
        train_generation_id=train_generation_id,
        ordinal=ordinal,
        predecessor_tree_sha=base_tree,
        result_tree_sha=head_tree,
        apply_profile=REFERENCE_APPLY_PROFILE,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical payload-only VIT qualification for a permanent PR candidate.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", required=True, help="Diff origin only; not a physical-main placement binding.")
    parser.add_argument("--head", required=True)
    parser.add_argument("--programme-id", required=True)
    parser.add_argument("--packet-id", required=True)
    parser.add_argument("--authority-manifest-id", required=True)
    parser.add_argument("--dependency-frontier-id", required=True)
    parser.add_argument("--completion-transition-json", default='{"status":"COMPLETED"}')
    parser.add_argument("--publish-detached", action="store_true", help="Publish the immutable qualification envelope and exact-head pointer to the detached VIT ledger.")
    parser.add_argument("--replace-head-qualification", action="store_true", help="Lawfully supersede the pointer for the same Git head while preserving the prior immutable envelope.")
    parser.add_argument("--emit-legacy-pr-marker", action="store_true", help="Migration/recovery only: also print the legacy VIT-Lineage-B64 PR-body marker.")
    parser.add_argument("--legacy-placement", action="store_true", help="Historical v1 early-placement output only.")
    parser.add_argument("--train-generation-id", default="LEGACY")
    parser.add_argument("--ordinal", type=int, default=0)
    args = parser.parse_args()
    transition = json.loads(args.completion_transition_json)
    if not isinstance(transition, Mapping):
        raise SystemExit("completion transition must be a JSON object")
    repo = Path(args.repo).resolve()
    record = build_record(
        repo=repo,
        base=args.base,
        head=args.head,
        programme_id=args.programme_id,
        packet_id=args.packet_id,
        authority_manifest_id=args.authority_manifest_id,
        dependency_frontier_id=args.dependency_frontier_id,
        completion_transition=transition,
        legacy_placement=args.legacy_placement,
        train_generation_id=args.train_generation_id,
        ordinal=args.ordinal,
    )
    print(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False))

    if args.publish_detached:
        if args.legacy_placement:
            raise RuntimeError("detached qualification publication requires payload-only late-binding lineage")
        envelope = build_qualification_envelope(repo=repo, root=repo, head_sha=args.head, lineage_record=record) if False else build_qualification_envelope(root=repo, head_sha=args.head, lineage_record=record)
        qualification_id = publish_qualification_envelope(
            envelope,
            replace_head_binding=args.replace_head_qualification,
        )
        print(f"VIT-Qualification-ID: {qualification_id}")

    if args.emit_legacy_pr_marker:
        print(f"VIT-Lineage-B64: {encode_lineage(record)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
