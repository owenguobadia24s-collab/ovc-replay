from __future__ import annotations

import argparse
import base64
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Mapping, Sequence

from ovc.development.skills.vit_apply import REFERENCE_APPLY_PROFILE
from ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest, PacketIntegrationPayload
from ovc.development.skills.vit_routing import build_vit_lineage_record


def _git(repo: Path, args: Sequence[str], *, env: Mapping[str, str] | None = None) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**dict(__import__("os").environ), **dict(env or {})},
    )
    return proc.stdout.strip()


def _safe_rel(value: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or value == ".git" or value.startswith(".git/"):
        raise RuntimeError(f"unsafe repository path: {value!r}")
    return value.replace("\\", "/")


def _base_entry(repo: Path, base: str, path: str) -> tuple[str, str, str] | None:
    raw = _git(repo, ["ls-tree", base, "--", path])
    if not raw:
        return None
    meta, listed = raw.split("\t", 1)
    if listed != path:
        raise RuntimeError(f"unexpected ls-tree path: {listed!r}")
    mode, object_type, object_sha = meta.split(" ", 2)
    return mode, object_type, object_sha


def _planned_changes(repo: Path, base: str, content_root: Path, targets: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    seen: set[str] = set()
    root = content_root.resolve()
    for target in targets:
        path = _safe_rel(str(target.get("path", "")))
        if path in seen:
            raise RuntimeError(f"duplicate planned path: {path}")
        seen.add(path)
        local = (root / path).resolve()
        if root not in local.parents:
            raise RuntimeError(f"planned content escapes root: {path}")
        if not local.is_file():
            raise RuntimeError(f"planned content missing: {path}")
        digest = str(target.get("content_sha256", ""))
        import hashlib
        if hashlib.sha256(local.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"planned content SHA-256 mismatch: {path}")
        blob_sha = _git(repo, ["hash-object", "-w", str(local)])
        before = _base_entry(repo, base, path)
        op = "ADD" if before is None else "MODIFY"
        mode = before[0] if before is not None else "100644"
        if mode not in {"100644", "100755", "120000"}:
            raise RuntimeError(f"unsupported existing mode for planned file {path}: {mode}")
        changes.append({"op": op, "path": path, "blob_sha": blob_sha, "mode": mode})
    if not changes:
        raise RuntimeError("planned PIP requires at least one target")
    return changes


def _compose_tree(repo: Path, base_tree: str, changes: Sequence[Mapping[str, str]]) -> str:
    with tempfile.TemporaryDirectory() as td:
        env = {"GIT_INDEX_FILE": str(Path(td) / "index")}
        _git(repo, ["read-tree", base_tree], env=env)
        for change in changes:
            _git(repo, ["update-index", "--add", "--cacheinfo", change["mode"], change["blob_sha"], change["path"]], env=env)
        return _git(repo, ["write-tree"], env=env)


def _b64(record: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build VIT lineage before a write actuator opens a permanent PR.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", required=True)
    parser.add_argument("--content-root", required=True)
    parser.add_argument("--targets-json", required=True, help="JSON array with path/content_sha256 rows")
    parser.add_argument("--programme-id", required=True)
    parser.add_argument("--packet-id", required=True)
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--gate-id", required=True)
    parser.add_argument("--authority-class", default="AUTO_EXECUTABLE")
    parser.add_argument("--authority-delta", default="NONE")
    parser.add_argument("--authority-sources-json", required=True)
    parser.add_argument("--reserved-boundaries-json", default="[]")
    parser.add_argument("--dependencies-json", default="[]")
    parser.add_argument("--owner-bindings-json", default="[]")
    parser.add_argument("--predecessor-requirement", default="PHYSICAL_MATERIALISATION_REQUIRED")
    parser.add_argument("--completion-transition-json", default='{"status":"COMPLETED"}')
    parser.add_argument("--train-generation-id", default="")
    parser.add_argument("--ordinal", type=int, default=1)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    content_root = Path(args.content_root).resolve()
    targets = json.loads(args.targets_json)
    authority_sources = tuple(json.loads(args.authority_sources_json))
    reserved_boundaries = tuple(json.loads(args.reserved_boundaries_json))
    dependencies = tuple(json.loads(args.dependencies_json))
    owner_bindings = tuple(json.loads(args.owner_bindings_json))
    completion_transition = json.loads(args.completion_transition_json)
    if not isinstance(targets, list) or not isinstance(completion_transition, Mapping):
        raise RuntimeError("targets must be a list and completion transition must be an object")

    _git(repo, ["cat-file", "-e", f"{args.base}^{{commit}}"])
    base_tree = _git(repo, ["rev-parse", f"{args.base}^{{tree}}"])
    changes = _planned_changes(repo, args.base, content_root, targets)
    result_tree = _compose_tree(repo, base_tree, changes)

    authority = IntegrationAuthorityManifest(
        plan_id=args.plan_id,
        packet_id=args.packet_id,
        gate_id=args.gate_id,
        authority_class=args.authority_class,
        authority_delta=args.authority_delta,
        authority_sources=authority_sources,
        reserved_boundaries=reserved_boundaries,
    )
    frontier = DependencyFrontier(
        dependencies=dependencies,
        predecessor_requirement=args.predecessor_requirement,
        owner_bindings=owner_bindings,
    )
    pip = PacketIntegrationPayload(
        programme_id=args.programme_id,
        packet_id=args.packet_id,
        logical_changes=tuple(changes),
        authority_manifest=authority,
        dependency_frontier=frontier,
        completion_transition=dict(completion_transition),
    )
    train_id = args.train_generation_id or f"VIT-PLANNED-{pip.payload_id[:24]}"
    record = build_vit_lineage_record(
        programme_id=args.programme_id,
        packet_id=args.packet_id,
        pip_identity_payload=pip.identity_payload(),
        train_generation_id=train_id,
        ordinal=args.ordinal,
        predecessor_tree_sha=base_tree,
        result_tree_sha=result_tree,
        apply_profile=REFERENCE_APPLY_PROFILE,
    )
    output = {
        "authority_manifest": asdict(authority),
        "authority_manifest_id": authority.logical_id,
        "dependency_frontier": asdict(frontier),
        "dependency_frontier_id": frontier.logical_id,
        "base_tree": base_tree,
        "expected_result_tree": result_tree,
        "lineage": record,
        "vit_lineage_b64": _b64(record),
    }
    print(json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
