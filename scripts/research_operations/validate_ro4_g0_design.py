#!/usr/bin/env python3
"""Validate the proposed RO4-G0 design canon and retained authority boundary."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTRACTS = [
    "contracts/research_operations/v0_4/OVC_RO4_AUTHORITY_AND_DEPENDENCY_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_C2_STATE_TRANSITION_INSPECTION_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_MATRIX_PERSISTENCE_CONFLICT_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_SEQUENCE_EVIDENCE_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_BOUNDARY_ANNOTATION_AND_FRICTION_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_OPERATION_MODE_AND_CUTOFF_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_CONSOLE_PROJECTION_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RC_G5_CONSUMPTION_GATE_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_PATTERN_DISCOVERY_ISOLATION_AND_TRACE_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_FULL_CORPUS_PERFORMANCE_AND_SAMPLING_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_COUNT_ONLY_PRESENTATION_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_C2E_DESIGN_OPENING_THRESHOLD_CONTRACT_v0_1.md",
    "contracts/research_operations/v0_4/RO4_AXIS_ABLATION_MACHINE_ASSURANCE_CONTRACT_v0_1.md",
]

SCHEMAS = [
    "schemas/research_operations/v0_4/c2_release_ref_v0_1.schema.json",
    "schemas/research_operations/v0_4/c2_state_ref_v0_1.schema.json",
    "schemas/research_operations/v0_4/c2_transition_ref_v0_1.schema.json",
    "schemas/research_operations/v0_4/transition_matrix_v0_1.schema.json",
    "schemas/research_operations/v0_4/persistence_run_v0_1.schema.json",
    "schemas/research_operations/v0_4/conflict_run_v0_1.schema.json",
    "schemas/research_operations/v0_4/sequence_window_v0_1.schema.json",
    "schemas/research_operations/v0_4/sequence_signature_v0_1.schema.json",
    "schemas/research_operations/v0_4/neutral_recurrence_candidate_v0_1.schema.json",
    "schemas/research_operations/v0_4/sequence_boundary_annotation_v0_1.schema.json",
    "schemas/research_operations/v0_4/c2e_friction_record_v0_1.schema.json",
    "schemas/research_operations/v0_4/prospective_sequence_review_v0_1.schema.json",
    "schemas/research_operations/v0_4/ro4_console_projection_v0_1.schema.json",
    "schemas/research_operations/v0_4/ro4_gate_packet_v0_1.schema.json",
    "schemas/research_operations/v0_4/signature_diversity_audit_v0_1.schema.json",
    "schemas/research_operations/v0_4/pd_trigger_trace_ref_v0_1.schema.json",
    "schemas/research_operations/v0_4/ro4_performance_benchmark_v0_1.schema.json",
    "schemas/research_operations/v0_4/declared_sample_manifest_v0_1.schema.json",
    "schemas/research_operations/v0_4/c2e_design_opening_assessment_v0_1.schema.json",
    "schemas/research_operations/v0_4/count_denominator_cell_v0_1.schema.json",
]

REGISTRIES = [
    "registries/research_operations/v0_4/RO4_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_PROGRAMME_STATE_v0_1.json",
    "registries/research_operations/v0_4/RO4_ROLE_ACCESS_MATRIX_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_CAPABILITY_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_TYPED_OBJECT_AND_SCHEMA_CATALOGUE_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_SEQUENCE_WINDOW_POLICY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_SEQUENCE_DISTANCE_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_CONTROL_SAMPLING_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_OPERATION_MODE_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_FRICTION_REASON_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_ROUTE_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_QA_CHECK_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_C2_SEQUENCE_INVARIANT_REGISTRY_v0_1.json",
    "registries/research_operations/v0_4/RO4_SIGNATURE_DIVERSITY_POLICY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_PD_TRACE_ALLOWLIST_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_AXIS_ABLATION_ASSURANCE_POLICY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_PERFORMANCE_AND_SAMPLE_POLICY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_COUNT_PRESENTATION_POLICY_v0_1.yaml",
    "registries/research_operations/v0_4/RO4_C2E_DESIGN_OPENING_THRESHOLD_v0_1.yaml",
]

OTHER = [
    "fixtures/research_operations/v0_4/RO4_FIXTURE_MATRIX_v0_1.yaml",
    "fixtures/research_operations/v0_4/RO4_G0_FIXTURE_PACK_v0_1.json",
    "docs/research-console/v0_4/RO4_C2_CONSOLE_PROJECTION_MAP_v0_1.md",
    "docs/releases/research-operations-foundation-v0-4/ro4-00/RO4_00_BASELINE_AND_SOURCE_HASH_PACKET.json",
    "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_DESIGN_CANON_CATALOGUE.json",
    "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_GATE_PACKET.json",
    "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_QA_PACKET.json",
    "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_OPERATOR_RATIFICATION.md",
    "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_CHANGE_SUMMARY.md",
]

REQUIRED = CONTRACTS + SCHEMAS + REGISTRIES + OTHER


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, tokens: list[str]) -> None:
    body = read(path)
    missing = [token for token in tokens if token not in body]
    if missing:
        raise AssertionError(f"{path}: missing {missing}")


def canonical_sha256(data: object) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing RO4-G0 files: {missing}")

    for path in SCHEMAS:
        parsed = json.loads(read(path))
        assert parsed["$schema"] == "https://json-schema.org/draft/2020-12/schema", path
        assert parsed["type"] == "object", path
        assert parsed["additionalProperties"] is False, path

    baseline = json.loads(read(OTHER[3]))
    catalogue = json.loads(read(OTHER[4]))
    gate = json.loads(read(OTHER[5]))
    qa = json.loads(read(OTHER[6]))
    state = json.loads(read(REGISTRIES[1]))
    invariants = json.loads(read(REGISTRIES[12]))
    fixtures = json.loads(read(OTHER[1]))

    assert baseline["court_record_main_tip"] == "1d436299c770a7043f95d7772b7550526de3ec73"
    assert baseline["plan_docx_sha256"] == "89d71f9740ce27203ab50f8d9cfaca76144215c640ee6e87870f7160a4d9badf"
    assert baseline["source_canon"]["discovery_release_id"] == "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2"
    assert baseline["source_canon"]["development_release_id"] == "OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v2"
    assert baseline["source_canon"]["state_record_count"] == 404434
    assert baseline["source_canon"]["transition_record_count"] == 323910
    assert baseline["source_canon"]["validation_consumption"] == "LOCKED_UNCONSUMED"
    assert baseline["open_pull_requests"][0]["number"] == 161
    assert baseline["open_pull_requests"][0]["dependency"] == "NONE"

    assert gate["gate_id"] == "RO4-G0"
    assert gate["status"] == "GATE_READY_OPERATOR_DECISION_REQUIRED"
    assert gate["recommended_decision"] == "PASS"
    assert gate["proposed_authority_delta"] == "DESIGN_CANON_ONLY_AND_BOUNDED_IMPLEMENTATION_RO4_WP1"
    assert gate["next_packet"] == "RO4-WP1"
    assert set(gate["allowed_decisions"]) == {"PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"}

    assert qa["status"] == "PASS_GATE_READY_OPERATOR_REQUIRED"
    assert qa["checks"]["runtime_implementation_started"] == "NO"
    assert qa["checks"]["canonical_annotation_or_friction_record_active"] == "NO"
    assert qa["checks"]["reserved_authority_delta"] == "NONE"
    assert not qa["blocking_issues"]

    assert state["programme_status"] == "GATE_READY"
    assert state["operator_decision_required"] is True
    assert state["current_packet"] == "RO4-00"
    assert state["packets"][0]["status"] == "GATE_READY"
    assert state["packets"][0]["authority_required"] == "OPERATOR_REQUIRED"
    assert state["packets"][1]["packet_id"] == "RO4-WP1"
    assert state["packets"][1]["status"] == "PLANNED"
    assert "VALIDATION_CONSUMPTION" in state["retained_prohibitions"]
    assert "C2E_EPISODE_AUTHORITY" in state["retained_prohibitions"]

    assert invariants["source_of_expectations"] == "INDEPENDENT_FROZEN_C2_AND_RO4_CONTRACT_CANON_NOT_IMPLEMENTATION"
    assert invariants["invariant_count"] == 24
    assert len(invariants["invariants"]) == 24
    assert len({row["invariant_id"] for row in invariants["invariants"]}) == 24
    assert all(row["mutation_required"] is True for row in invariants["invariants"])

    assert fixtures["synthetic"] is True
    assert fixtures["market_authority"] == "NONE"
    expected = {case["expected"] for case in fixtures["cases"]}
    assert {"ACCEPT", "REJECT", "QUARANTINE", "REJECT_DECISION_OPTION"}.issubset(expected)

    listed = catalogue["artifacts"]
    assert catalogue["status"] == "PROPOSED_AT_RO4_G0"
    assert len(listed) == len(CONTRACTS) + len(SCHEMAS) + len(REGISTRIES) + 3
    for item in listed:
        path = ROOT / item["path"]
        data = path.read_bytes()
        assert len(data) == item["size_bytes"], item["path"]
        assert hashlib.sha256(data).hexdigest() == item["sha256"], item["path"]

    require_tokens(
        CONTRACTS[0],
        [
            "Pattern Discovery remains a parallel isolated population",
            "Validation is denied before path, object, timestamp or record resolution",
            "RO4-G0, RO4-G4, RC-G5 and RO4-G6 are operator-required",
        ],
    )
    require_tokens(
        CONTRACTS[3],
        [
            "NON_CANONICAL_SEQUENCE_EVIDENCE",
            "signature concentration",
            "No signature exceeds 20%",
            "INSUFFICIENT_SAMPLE_FOR_DIVERSITY_AUDIT",
        ],
    )
    require_tokens(
        CONTRACTS[8],
        [
            "RO4.SEQUENCE.*",
            "PD.CANDIDATE.*",
            "trigger provenance",
            "future integration requires",
        ],
    )
    require_tokens(
        CONTRACTS[9],
        [
            "<=10 minutes",
            "<=8 GiB",
            "DECLARED_SAMPLE_MODE",
            "SAMPLED_NON_CANONICAL_EXPLORATORY",
        ],
    )
    require_tokens(
        CONTRACTS[10],
        [
            "counts are not probabilities",
            "eligible denominator visible",
            "Percentages",
            "uniform and non-data-driven",
        ],
    )
    require_tokens(
        CONTRACTS[11],
        [
            "At least 3 independent",
            "At least 10 accepted",
            "At least 5 counterexample",
            "drafting a separate C2E implementation plan only",
        ],
    )
    require_tokens(
        CONTRACTS[12],
        [
            "synthetic QA operations only",
            "cannot enter blinded operator batches",
            "may not describe an axis as important",
        ],
    )
    require_tokens(
        "docs/research-console/v0_4/RO4_C2_CONSOLE_PROJECTION_MAP_v0_1.md",
        [
            "DISABLED_PENDING_RC_G5",
            "separate population",
            "No synthetic or axis-ablated control",
            "No write form, button, action or remote deployment",
        ],
    )
    require_tokens(
        REGISTRIES[13],
        [
            "minimum_candidate_count_for_pass: 100",
            "normalized_shannon_entropy_warning_below: '0.55'",
            "operator_batch_signature_cap_share: '0.20'",
            "derived_share_values: DENIED",
        ],
    )
    require_tokens(
        REGISTRIES[14],
        [
            "allowed_fields:",
            "pd_trigger_id",
            "denied_fields:",
            "joint_review_batch: DENIED",
            "ro4_to_pd_evidence_bridge: DENIED",
        ],
    )
    require_tokens(
        REGISTRIES[15],
        [
            "artifact_class: MACHINE_QA_ONLY",
            "operator_facing_schemas: DENY",
            "importance_language: PROHIBITED",
        ],
    )
    require_tokens(
        REGISTRIES[16],
        [
            "full_discovery_index_seconds: 600",
            "window_cardinality_cap_per_role_clock_side_calendar_partition: 100000",
            "silent_substitution: PROHIBITED",
        ],
    )
    require_tokens(
        REGISTRIES[17],
        [
            "exact count and visible denominator",
            "percentage",
            "distribution_shaped_styling",
        ],
    )
    require_tokens(
        REGISTRIES[18],
        [
            "minimum_strata: 3",
            "minimum_accepted_annotations: 10",
            "minimum_counterexample_sets_where_per_bar_c2_is_sufficient: 5",
            "DRAFT_SEPARATE_C2E_IMPLEMENTATION_PLAN_ONLY",
        ],
    )

    sample = json.loads(read("schemas/research_operations/v0_4/declared_sample_manifest_v0_1.schema.json"))
    assert sample["properties"]["banner"]["const"] == "SAMPLED_NON_CANONICAL_EXPLORATORY"
    assert sample["properties"]["hash_expression"]["const"].startswith("SHA256")

    count_schema = json.loads(read("schemas/research_operations/v0_4/count_denominator_cell_v0_1.schema.json"))
    denied_count_fields = {item["required"][0] for item in count_schema["not"]["anyOf"]}
    assert {"percentage", "ratio", "normalized_frequency", "probability", "rank", "colour_intensity", "bar_length"}.issubset(denied_count_fields)

    pd_schema = json.loads(read("schemas/research_operations/v0_4/pd_trigger_trace_ref_v0_1.schema.json"))
    denied_pd_fields = {item["required"][0] for item in pd_schema["not"]["anyOf"]}
    assert {"pd_candidate_id", "fingerprint", "novelty", "medoid", "cluster", "review", "answer_key", "promotion"}.issubset(denied_pd_fields)

    projection = json.loads(read("schemas/research_operations/v0_4/ro4_console_projection_v0_1.schema.json"))
    assert projection["properties"]["route_state"]["const"] == "DISABLED_PENDING_RC_G5"
    assert projection["properties"]["writes"]["const"] == "NONE"
    assert projection["properties"]["remote_deployment"]["const"] == "DENIED"

    assessment = json.loads(read("schemas/research_operations/v0_4/c2e_design_opening_assessment_v0_1.schema.json"))
    assert assessment["properties"]["decision_effect"]["const"] == "DRAFT_SEPARATE_PLAN_ONLY_NO_C2E_AUTHORITY"

    # A stable digest of the critical boundary is printed for evidence comparison.
    digest = canonical_sha256(
        {
            "plan": baseline["plan_docx_sha256"],
            "discovery": baseline["source_canon"]["discovery_manifest_sha256"],
            "development": baseline["source_canon"]["development_manifest_sha256"],
            "gate": gate["gate_id"],
            "delta": gate["proposed_authority_delta"],
            "invariants": [row["invariant_id"] for row in invariants["invariants"]],
        }
    )
    print(f"RO4_G0_BOUNDARY_DIGEST={digest}")
    print("PASS: RO4-G0 proposed design canon, source boundary and operator gate are complete")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        raise SystemExit(1)
