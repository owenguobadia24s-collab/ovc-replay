#!/usr/bin/env python3
"""Write the PGN-WP2E census as a deterministic, reviewable file bundle."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MATERIALIZER = ROOT / "scripts/governance/materialize_pgn_wp2e_census.py"
OUT = ROOT / "registries/governance/programme_genesis/pgn_census"
MAIN = OUT / "PGN_REPOSITORY_GENESIS_CENSUS_v0_2.json"
CHUNK_SIZE = 10


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_materializer():
    spec = importlib.util.spec_from_file_location("materialize_pgn_wp2e_census", MATERIALIZER)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {MATERIALIZER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write(path: Path, value: Any) -> dict[str, Any]:
    data = json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": digest_bytes(data),
        "bytes": len(data),
    }


def build_bundle(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    compact = load_materializer().materialize(root)
    files: dict[str, dict[str, Any]] = {}
    object_refs: list[dict[str, Any]] = []
    objects = compact["objects"]
    for index, start in enumerate(range(0, len(objects), CHUNK_SIZE)):
        chunk = {
            "schema": "ovc-pgn-repository-genesis-object-ledger/v2",
            "packet_id": compact["packet_id"],
            "gate_id": compact["gate_id"],
            "chunk_index": index,
            "start_index": start,
            "object_count": len(objects[start : start + CHUNK_SIZE]),
            "objects": objects[start : start + CHUNK_SIZE],
        }
        path = OUT / f"PGN_REPOSITORY_GENESIS_OBJECTS_v0_2_{index:02d}.jsonc"
        ref = write(path, chunk)
        files[ref["path"]] = chunk
        object_refs.append({**ref, "object_count": chunk["object_count"], "start_index": start})

    exclusion = {
        "schema": "ovc-pgn-repository-genesis-exclusion-ledger/v2",
        "packet_id": compact["packet_id"],
        "gate_id": compact["gate_id"],
        "entry_count": len(compact["exclusion_ledger"]),
        "entries": compact["exclusion_ledger"],
    }
    exclusion_path = OUT / "PGN_REPOSITORY_GENESIS_EXCLUSIONS_v0_2.jsonc"
    exclusion_ref = write(exclusion_path, exclusion)
    files[exclusion_ref["path"]] = exclusion

    lineage = {
        "schema": "ovc-pgn-repository-genesis-lineage-ledger/v2",
        "packet_id": compact["packet_id"],
        "gate_id": compact["gate_id"],
        "entry_count": len(compact["lineage_consolidation_ledger"]),
        "entries": compact["lineage_consolidation_ledger"],
    }
    lineage_path = OUT / "PGN_REPOSITORY_GENESIS_LINEAGE_v0_2.jsonc"
    lineage_ref = write(lineage_path, lineage)
    files[lineage_ref["path"]] = lineage

    unresolved = {
        "schema": "ovc-pgn-repository-genesis-coverage-unresolved-ledger/v2",
        "packet_id": compact["packet_id"],
        "gate_id": compact["gate_id"],
        "coverage": compact["coverage"],
        **compact["coverage_and_unresolved_ledger"],
    }
    unresolved_path = OUT / "PGN_REPOSITORY_GENESIS_COVERAGE_UNRESOLVED_v0_2.jsonc"
    unresolved_ref = write(unresolved_path, unresolved)
    files[unresolved_ref["path"]] = unresolved

    child_refs = object_refs + [
        {**exclusion_ref, "entry_count": exclusion["entry_count"]},
        {**lineage_ref, "entry_count": lineage["entry_count"]},
        {**unresolved_ref, "unresolved_count": unresolved["unresolved_count"]},
    ]
    child_identity = [
        {"path": item["path"], "sha256": item["sha256"], "bytes": item["bytes"]}
        for item in child_refs
    ]
    main: dict[str, Any] = {
        "schema": "ovc-pgn-repository-genesis-census-bundle/v2",
        "programme_id": compact["programme_id"],
        "plan_id": compact["plan_id"],
        "packet_id": compact["packet_id"],
        "gate_id": compact["gate_id"],
        "baseline_main": compact["baseline_main"],
        "policy_path": compact["policy_path"],
        "policy_sha256": compact["policy_sha256"],
        "classification_enum": compact["classification_enum"],
        "object_count": compact["object_count"],
        "classification_counts": compact["classification_counts"],
        "object_kind_counts": compact["object_kind_counts"],
        "detailed_census_sha256": compact["detailed_census_sha256"],
        "materialized_census_sha256": compact["materialized_census_sha256"],
        "object_ledgers": object_refs,
        "exclusion_ledger": {**exclusion_ref, "entry_count": exclusion["entry_count"]},
        "lineage_consolidation_ledger": {**lineage_ref, "entry_count": lineage["entry_count"]},
        "coverage_and_unresolved_ledger": {**unresolved_ref, "unresolved_count": unresolved["unresolved_count"]},
        "child_file_identity_sha256": digest_bytes(canonical(child_identity)),
        "authority": compact["authority"],
        "next_action": compact["next_action"],
        "rollback": compact["rollback"],
    }
    main["bundle_manifest_sha256"] = digest_bytes(canonical(main))
    return main, files


def main() -> int:
    main_record, _ = build_bundle()
    main_ref = write(MAIN, main_record)
    print(
        "PGN_WP2E_BUNDLE="
        + json.dumps(
            {
                **main_ref,
                "object_count": main_record["object_count"],
                "classification_counts": main_record["classification_counts"],
                "bundle_manifest_sha256": main_record["bundle_manifest_sha256"],
                "child_file_identity_sha256": main_record["child_file_identity_sha256"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
