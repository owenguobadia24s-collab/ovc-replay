#!/usr/bin/env python3
"""Validate the RO4-G0 proposed design canon and operator boundary."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PLAN_ID = 'OVC-RESEARCH-OPERATIONS-FOUNDATION-v0.4-C2-STATE-SEQUENCE-EVIDENCE-IMPLEMENTATION-PLAN-0.2'
PLAN_SHA = '89d71f9740ce27203ab50f8d9cfaca76144215c640ee6e87870f7160a4d9badf'
BASELINE = '306e449acdaddbb0131fd01aca6098dd8ab0b7ef'

REQUIRED = [
    ".github/workflows/research-operations-v0-4-ro4-g0.yml",
    "contracts/research_operations/v0_4/OVC_RO4_AUTHORITY_AND_DEPENDENCY_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RC_G5_CONSUMPTION_GATE_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_AXIS_ABLATION_MACHINE_ASSURANCE_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_BOUNDARY_ANNOTATION_AND_FRICTION_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_C2E_DESIGN_OPENING_THRESHOLD_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_C2_STATE_TRANSITION_INSPECTION_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_CONSOLE_PROJECTION_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_COUNT_ONLY_PRESENTATION_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_FULL_CORPUS_PERFORMANCE_AND_SAMPLING_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_MATRIX_PERSISTENCE_CONFLICT_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_OPERATION_MODE_AND_CUTOFF_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_PATTERN_DISCOVERY_ISOLATION_AND_TRACE_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_SEQUENCE_EVIDENCE_CONTRACT_v0_1.md",
    "docs/releases/research-operations-foundation-v0-4/ro4-00/RO4_00_BASELINE_AND_SOURCE_HASH_PACKET.json",
    "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_CHANGE_SUMMARY.md",
    "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_DESIGN_CANON_CATALOGUE.json",
    "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_GATE_PACKET.json",
    "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_OPERATOR_RATIFICATION.md",
    "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_QA_PACKET.json",
    "docs/research-console/v0_4/RO4_C2_CONSOLE_PROJECTION_MAP_v0_1.md",
    "fixtures/research_operations/v0_4/RO4_FIXTURE_MATRIX_v0_1.yaml",
    "fixtures/research_operations/v0_4/RO4_G0_FIXTURE_PACK_v0_1.json",
    "registries/research_operations/v0_4/RO4_AXIS_ABLATION_ASSURANCE_POLICY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_C2E_DESIGN_OPENING_THRESHOLD_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_C2_SEQUENCE_INVARIANT_REGISTRY_v0_1.json",
    "registries/research_operations/v0_4/RO4_CAPABILITY_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_CONTROL_SAMPLING_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_COUNT_PRESENTATION_POLICY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_FRICTION_REASON_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_OPERATION_MODE_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_PD_TRACE_ALLOWLIST_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_PERFORMANCE_AND_SAMPLE_POLICY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_PROGRAMME_STATE_v0_1.json",
    "registries/research_operations/v0_4/RO4_QA_CHECK_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_ROLE_ACCESS_MATRIX_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_ROUTE_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_SEQUENCE_DISTANCE_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_SEQUENCE_WINDOW_POLICY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_SIGNATURE_DIVERSITY_POLICY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_TYPED_OBJECT_AND_SCHEMA_CATALOGUE_v0_1.yaml",
    "schemas/research_operations/v0_4/c2_release_ref_v0_1.schema.json",
    "schemas/research_operations/v0_4/c2_state_ref_v0_1.schema.json",
    "schemas/research_operations/v0_4/c2_transition_ref_v0_1.schema.json",
    "schemas/research_operations/v0_4/c2e_design_opening_assessment_v0_1.schema.json",
    "schemas/research_operations/v0_4/c2e_friction_record_v0_1.schema.json",
    "schemas/research_operations/v0_4/conflict_run_v0_1.schema.json",
    "schemas/research_operations/v0_4/count_denominator_cell_v0_1.schema.json",
    "schemas/research_operations/v0_4/declared_sample_manifest_v0_1.schema.json",
    "schemas/research_operations/v0_4/neutral_recurrence_candidate_v0_1.schema.json",
    "schemas/research_operations/v0_4/pd_trigger_trace_ref_v0_1.schema.json",
    "schemas/research_operations/v0_4/persistence_run_v0_1.schema.json",
    "schemas/research_operations/v0_4/prospective_sequence_review_v0_1.schema.json",
    "schemas/research_operations/v0_4/ro4_console_projection_v0_1.schema.json",
    "schemas/research_operations/v0_4/ro4_gate_packet_v0_1.schema.json",
    "schemas/research_operations/v0_4/ro4_performance_benchmark_v0_1.schema.json",
    "schemas/research_operations/v0_4/sequence_boundary_annotation_v0_1.schema.json",
    "schemas/research_operations/v0_4/sequence_signature_v0_1.schema.json",
    "schemas/research_operations/v0_4/sequence_window_v0_1.schema.json",
    "schemas/research_operations/v0_4/signature_diversity_audit_v0_1.schema.json",
    "schemas/research_operations/v0_4/transition_matrix_v0_1.schema.json",
    "scripts/research_operations/validate_ro4_g0_design.py",
    "tests/research_operations/v0_4/test_ro4_g0_design.py"
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, tokens: list[str]) -> None:
    content = read(path)
    missing = [token for token in tokens if token not in content]
    if missing:
        raise AssertionError(f"{path}: missing tokens {missing}")


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing RO4-G0 artifacts: {missing}")

    baseline = json.loads(read("docs/releases/research-operations-foundation-v0-4/ro4-00/RO4_00_BASELINE_AND_SOURCE_HASH_PACKET.json"))
    gate = json.loads(read("docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_GATE_PACKET.json"))
    qa = json.loads(read("docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_QA_PACKET.json"))
    catalogue = json.loads(read("docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_DESIGN_CANON_CATALOGUE.json"))
    state = json.loads(read("registries/research_operations/v0_4/RO4_PROGRAMME_STATE_v0_1.json"))
    invariants = json.loads(read("registries/research_operations/v0_4/RO4_C2_SEQUENCE_INVARIANT_REGISTRY_v0_1.json"))
    fixtures = json.loads(read("fixtures/research_operations/v0_4/RO4_G0_FIXTURE_PACK_v0_1.json"))

    assert baseline["plan_id"] == PLAN_ID
    assert baseline["plan_docx_sha256"] == PLAN_SHA
    assert baseline["court_record_main_tip"] == BASELINE
    assert baseline["source_canon"]["state_record_count"] == 404434
    assert baseline["source_canon"]["transition_record_count"] == 323910
    assert baseline["source_canon"]["validation_consumption"] == "LOCKED_UNCONSUMED"
    assert baseline["source_canon"]["development_selector"] == "NONE_REMOTE_VERIFIED_REFERENCE_ONLY"
    assert baseline["source_canon"]["b_state"] == "HISTORICAL_SUPERSEDED_RUNTIME_DENIED"
    assert baseline["open_pull_requests"] == []
    assert baseline["parent_foundations"]["june_controlled_review_disposition"] == "DEFER_NO_CONTINUATION"

    assert gate["gate_id"] == "RO4-G0"
    assert gate["status"] == "GATE_READY_OPERATOR_DECISION_REQUIRED"
    assert gate["recommended_decision"] == "PASS"
    assert gate["proposed_authority_delta"] == "DESIGN_CANON_ONLY_AND_BOUNDED_IMPLEMENTATION_RO4_WP1"
    assert set(gate["allowed_decisions"]) == {"PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"}
    assert gate["next_packet"] == "RO4-WP1"

    assert qa["status"] == "PASS_GATE_READY_OPERATOR_REQUIRED"
    assert qa["blocking_issues"] == []
    assert qa["operator_decision_required"] is True
    assert qa["checks"]["runtime_implementation_started"] == "NO"
    assert qa["checks"]["reserved_authority_delta"] == "NONE"

    assert state["programme_status"] == "GATE_READY"
    assert state["current_packet"] == "RO4-00"
    assert state["current_gate"] == "RO4-G0"
    assert state["operator_decision_required"] is True
    assert state["packets"][0]["status"] == "GATE_READY"
    assert state["packets"][1]["status"] == "PLANNED"
    assert state["packets"][1]["blockers"] == ["RO4-G0_NOT_APPROVED"]
    assert state["packets"][6]["authority_required"] == "OPERATOR_REQUIRED_NOT_AUTO_RATIFIABLE"

    assert invariants["registry_id"] == "RO4.C2.SEQUENCE.INVARIANTS.v0.1"
    assert invariants["source_of_expectations"] == "INDEPENDENT_FROZEN_C2_AND_RO4_CONTRACT_CANON_NOT_IMPLEMENTATION"
    assert invariants["invariant_count"] == 24
    assert len(invariants["invariants"]) == 24
    assert len({row["invariant_id"] for row in invariants["invariants"]}) == 24
    assert all(row["mutation_required"] for row in invariants["invariants"])

    assert fixtures["synthetic"] is True
    assert fixtures["market_authority"] == "NONE"
    assert fixtures["operator_evidence_authority"] == "NONE"
    assert {row["expected"] for row in fixtures["cases"]} >= {"ACCEPT", "REJECT", "ACCEPT_MACHINE_ONLY", "QUARANTINE", "REJECT_DECISION_OPTION"}

    catalogue_paths = {row["path"] for row in catalogue["artifacts"]}
    assert len(catalogue_paths) == len(catalogue["artifacts"])
    for row in catalogue["artifacts"]:
        payload = (ROOT / row["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == row["sha256"], row["path"]
        assert len(payload) == row["size_bytes"], row["path"]

    schema_dir = ROOT / "schemas" / "research_operations" / "v0_4"
    schemas = sorted(schema_dir.glob("*.schema.json"))
    assert len(schemas) == 20
    for path in schemas:
        obj = json.loads(path.read_text(encoding="utf-8"))
        assert obj["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert obj["type"] == "object"
        assert obj["additionalProperties"] is False

    assert len(list((ROOT / "contracts" / "research_operations" / "v0_4").glob("*.md"))) == 13
    assert len(list((ROOT / "registries" / "research_operations" / "v0_4").iterdir())) == 19
    assert len(list((ROOT / "fixtures" / "research_operations" / "v0_4").iterdir())) == 2

    require_tokens("contracts/research_operations/v0_4/OVC_RO4_AUTHORITY_AND_DEPENDENCY_CONTRACT_v0_1.md",
                   ["LOCKED_UNCONSUMED", "Pattern Discovery remains a parallel isolated population", "RO4-G0, RO4-G4, RC-G5 and RO4-G6"])
    require_tokens("contracts/research_operations/v0_4/RO4_SEQUENCE_EVIDENCE_CONTRACT_v0_1.md",
                   ["NON_CANONICAL_SEQUENCE_EVIDENCE", "entropy below 0.55", "20%"])
    require_tokens("contracts/research_operations/v0_4/RO4_PATTERN_DISCOVERY_ISOLATION_AND_TRACE_CONTRACT_v0_1.md",
                   ["pd_trigger_id", "fingerprint", "OVC_RO4_PD_INTEGRATION_IMPLEMENTATION_PLAN"])
    require_tokens("contracts/research_operations/v0_4/RO4_FULL_CORPUS_PERFORMANCE_AND_SAMPLING_CONTRACT_v0_1.md",
                   ["100,000", "DECLARED_SAMPLE_MODE", "SAMPLED_NON_CANONICAL_EXPLORATORY"])
    require_tokens("contracts/research_operations/v0_4/RO4_COUNT_ONLY_PRESENTATION_CONTRACT_v0_1.md",
                   ["DESCRIPTIVE COUNTS ONLY", "Percentages", "uniform"])
    require_tokens("contracts/research_operations/v0_4/RO4_C2E_DESIGN_OPENING_THRESHOLD_CONTRACT_v0_1.md",
                   ["At least 3 independent", ">=0.70", "drafting a separate C2E implementation plan only"])
    require_tokens("contracts/research_operations/v0_4/RO4_AXIS_ABLATION_MACHINE_ASSURANCE_CONTRACT_v0_1.md",
                   ["machine artifacts", "cannot enter blinded operator batches", "important, dominant, predictive"])

    require_tokens("registries/research_operations/v0_4/RO4_ROUTE_REGISTRY_v0_1.yaml",
                   ["DISABLED_PENDING_RC_G5", "writes: NONE", "remote_deployment: DENIED"])
    require_tokens("registries/research_operations/v0_4/RO4_ROLE_ACCESS_MATRIX_v0_1.yaml",
                   ["DENY_BEFORE_PATH_OBJECT_RECORD_TIMESTAMP_RESOLUTION", "content_resolution: DENY"])
    require_tokens("registries/research_operations/v0_4/RO4_SIGNATURE_DIVERSITY_POLICY_v0_1.yaml",
                   ["0.55", "0.20", "OPERATOR_ACKNOWLEDGEMENT_REQUIRED"])
    require_tokens("registries/research_operations/v0_4/RO4_PD_TRACE_ALLOWLIST_v0_1.yaml",
                   ["pd_trigger_id", "fingerprint", "joint_review_batch: DENIED"])
    require_tokens("registries/research_operations/v0_4/RO4_COUNT_PRESENTATION_POLICY_v0_1.yaml",
                   ["eligible_denominator", "heatmap", "FROZEN_IDENTITY_ORDER"])
    require_tokens("docs/research-console/v0_4/RO4_C2_CONSOLE_PROJECTION_MAP_v0_1.md",
                   ["Live route state: `DISABLED_PENDING_RC_G5`", "No synthetic or axis-ablated control", "No write form"])

    forbidden_runtime = [
        ROOT / "src" / "ovc" / "research_operations" / "v0_4",
        ROOT / "apps" / "research_console" / "ro4_c2_sequence_evidence.py",
    ]
    if any(path.exists() for path in forbidden_runtime):
        raise AssertionError("RO4 runtime or live Console implementation exists before RO4-G0 approval")

    print("PASS: RO4-G0 design canon is complete, source-bound, non-activating and operator-gated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError, OSError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        raise SystemExit(1)
