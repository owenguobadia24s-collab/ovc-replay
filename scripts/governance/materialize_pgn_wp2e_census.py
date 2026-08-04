#!/usr/bin/env python3
"""Materialise the PGN-WP2E census as a compact source-linked repository record."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/governance/build_pgn_wp2e_repository_genesis_census.py"
OUTPUT = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_REPOSITORY_GENESIS_CENSUS_v0_2.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def load_builder():
    spec = importlib.util.spec_from_file_location("build_pgn_wp2e_repository_genesis_census", BUILDER)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {BUILDER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def materialize(root: Path = ROOT) -> dict[str, Any]:
    detailed = load_builder().build_census(root)
    objects: list[dict[str, Any]] = []
    for item in detailed["objects"]:
        sources = item["sources"]
        primary = sources[0]
        objects.append(
            {
                "object_id": item["object_id"],
                "object_kind": item["object_kind"],
                "classification": item["classification"],
                "classification_rationale": item["classification_rationale"],
                "evidence_plane": item["evidence_plane"],
                "source_count": len(sources),
                "source_set_sha256": digest(sources),
                "primary_source": {
                    key: primary[key]
                    for key in ("path", "sha256", "role")
                    if key in primary
                },
                "successors": item["successors"],
                "candidate_constructed": False,
                "authority_effect": "NONE",
            }
        )
    lineage = []
    for item in detailed["lineage_consolidation_ledger"]:
        lineage.append(
            {
                "object_id": item["object_id"],
                "classification": item["classification"],
                "successors": item["successors"],
                "evidence_source_count": len(item["evidence"]),
                "evidence_source_set_sha256": digest(item["evidence"]),
            }
        )
    result: dict[str, Any] = {
        "schema": "ovc-pgn-repository-genesis-census-materialized/v2",
        "programme_id": detailed["programme_id"],
        "plan_id": detailed["plan_id"],
        "packet_id": detailed["packet_id"],
        "gate_id": detailed["gate_id"],
        "baseline_main": detailed["baseline_main"],
        "policy_path": detailed["policy_path"],
        "policy_sha256": detailed["policy_sha256"],
        "coverage": detailed["coverage"],
        "classification_enum": detailed["classification_enum"],
        "object_count": detailed["object_count"],
        "classification_counts": detailed["classification_counts"],
        "object_kind_counts": detailed["object_kind_counts"],
        "detailed_census_sha256": detailed["census_sha256"],
        "objects": objects,
        "exclusion_ledger": detailed["exclusion_ledger"],
        "lineage_consolidation_ledger": lineage,
        "coverage_and_unresolved_ledger": detailed["coverage_and_unresolved_ledger"],
        "authority": detailed["authority"],
        "next_action": detailed["next_action"],
        "rollback": detailed["rollback"],
    }
    result["materialized_census_sha256"] = digest(result)
    return result


def main() -> int:
    value = materialize()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        "PGN_WP2E_MATERIALIZED="
        + json.dumps(
            {
                "path": OUTPUT.relative_to(ROOT).as_posix(),
                "object_count": value["object_count"],
                "classification_counts": value["classification_counts"],
                "detailed_census_sha256": value["detailed_census_sha256"],
                "materialized_census_sha256": value["materialized_census_sha256"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
