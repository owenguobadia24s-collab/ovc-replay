#!/usr/bin/env python3
"""Validate the frozen RO3-G0 authority canon throughout later packets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = [
    "contracts/research_operations/v0_3/OVC_RO3_C1_FACT_ASSURANCE_AUTHORITY_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_3/RO3_NON_ACTIVATING_COMPARISON_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_3/RO3_AFFECTED_SURFACE_PRESENTATION_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_3/RC_G4_C1_CONSUMPTION_GATE_CONTRACT_v0_1.md",
    "registries/research_operations/v0_3/RO3_ROLE_ACCESS_POLICY_v0_1.yaml",
    "registries/research_operations/v0_3/RO3_DEPENDENCY_POLICY_v0_1.yaml",
    "registries/research_operations/v0_3/RO3_TYPED_OBJECT_AND_SCHEMA_CATALOGUE_v0_1.yaml",
    "registries/research_operations/v0_3/C1_METAMORPHIC_INVARIANT_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_3/RO3_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_3/RO3_PROGRAMME_STATE_v0_1.json",
    "schemas/research_operations/v0_3/c1_metamorphic_invariant_registry_v0_1.schema.json",
    "fixtures/research_operations/v0_3/RO3_FIXTURE_MATRIX_v0_1.yaml",
    "docs/research-console/v0_3/RO3_C1_CONSOLE_PROJECTION_MAP_v0_1.md",
    "docs/releases/research-operations-foundation-v0-3/ro3-00/RO3_00_BASELINE_AND_SOURCE_HASH_PACKET.json",
    "docs/releases/research-operations-foundation-v0-3/ro3-g0/RO3_G0_GATE_PACKET.json",
    "docs/releases/research-operations-foundation-v0-3/ro3-g0/RO3_G0_OPERATOR_RATIFICATION.md",
]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, tokens: list[str]) -> None:
    content = text(path)
    missing = [token for token in tokens if token not in content]
    if missing:
        raise AssertionError(f"{path}: missing tokens {missing}")


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing RO3-G0 files: {missing}")

    baseline = json.loads(text(REQUIRED[13]))
    gate = json.loads(text(REQUIRED[14]))
    invariants = json.loads(text(REQUIRED[7]))
    state = json.loads(text(REQUIRED[9]))

    assert baseline["court_record_main_tip"] == "0c177560b02e14a36a949626b155f616c12549e5"
    assert baseline["source_canon"]["total_record_count"] == 212764
    assert baseline["source_canon"]["total_file_count"] == 192
    assert baseline["source_canon"]["formula_count"] == 18
    assert {item["number"] for item in baseline["reconciled_open_pull_requests"]} == {56, 86, 117}

    assert gate["gate_id"] == "RO3-G0"
    assert gate["decision"] == "PASS"
    assert gate["authority_delta"] == "DESIGN_CANON_ONLY"
    assert gate["checks"]["runtime_implementation_started"] == "NO"
    assert gate["checks"]["independent_invariant_registry_frozen_18_of_18"] == "PASS"

    assert invariants["registry_id"] == "C1.METAMORPHIC.INVARIANTS.v0.1"
    assert invariants["source_of_expectations"] == "INDEPENDENT_CONTRACT_CANON_NOT_IMPLEMENTATION"
    assert invariants["formula_count"] == 18
    assert len(invariants["invariants"]) == 18
    primitive_ids = [row["primitive_id"] for row in invariants["invariants"]]
    assert len(set(primitive_ids)) == 18
    assert all(row["relations"] for row in invariants["invariants"])

    assert state["programme_status"] in {"RUNNING", "GATE_READY", "COMPLETED"}
    assert state["packets"][0]["packet_id"] == "RO3-00"
    assert state["packets"][0]["status"] in {"APPROVED", "COMPLETED"}
    assert state["packets"][-1]["authority_required"] == "OPERATOR_REQUIRED_NOT_AUTO_RATIFIABLE"

    require_tokens(REQUIRED[0], ["LOCKED_UNCONSUMED", "No reverse write", "DISABLED_PENDING_RC_G4"])
    require_tokens(REQUIRED[1], ["NON_ACTIVATING_EVIDENCE_HEADER", "ACKNOWLEDGEMENT_MISMATCH", "activation_recommendation` is always `null"])
    require_tokens(REQUIRED[2], ["DOWNSTREAM TRACE — READ ONLY", "C1 null reason and a C2 transition", "No recompute, tune, mutate, promote, activate or write control"])
    require_tokens(REQUIRED[3], ["OPERATOR_REQUIRED", "NOT_AUTO_RATIFIABLE", "LOCAL_READ_ONLY_C1_PRESENTATION"])
    require_tokens(REQUIRED[4], ["validation_guard: DENY_BEFORE_PATH_OBJECT_RECORD_TIMESTAMP_RESOLUTION", "content_resolution: DENY"])
    require_tokens(REQUIRED[5], ["R2 canonical", "C1 formulas, contracts, schemas, records, releases or selectors", "cycle_guard: REQUIRED"])
    require_tokens(REQUIRED[12], ["Live route state: `DISABLED_PENDING_RC_G4`", "No C1 null explanation and C2 transition"])

    print("PASS: RO3-G0 design canon, independent invariants and operator boundary remain frozen")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError, OSError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        raise SystemExit(1)
