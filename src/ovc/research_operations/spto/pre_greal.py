"""Assemble the source-free C2S-SPTOI pre-GREAL operator packet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .factorised_mechanics import content_id


PROGRAMME_ID = "OVC-EML-C2S-SPTO-CONFORMANCE-PREREG-v0.1"
PACKET_ID = "C2S-SPTOI-WP11"
GATE_ID = "C2S-SPTOI-GREAL-SCI-PREREG"
BASELINE_MAIN = "d96ca23da62e5bcf8f798d1608b54e6b0f1b47e8"
BASELINE_TREE = "b9954f828a2912b7edcb0c36a4f87dbc341726d7"

BINDINGS = {
    "ratified_plan": "docs/programmes/c2s-sptoi-v0-1/wp0/C2S_SPTOI_WP0_PLAN_MATERIALISATION_v0_1.json",
    "protocol_binding": "docs/programmes/c2s-sptoi-v0-1/gates/OVC_EML_GRAMMAR_0002_RP_BINDING_v0_1.json",
    "protocol_operator_decision": "docs/programmes/c2s-sptoi-v0-1/gates/C2S_SPTOI_G_RICH_RP_OPERATOR_DECISION_v0_1.json",
    "owner_scope_binding": "docs/programmes/c2s-sptoi-v0-1/gates/SPTO_DENSE_INTERSTITIAL_OWNER_SCOPE_BINDING_v0_1.json",
    "owner_stream_binding": "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_WP4_C2_OWNER_STREAM_BINDING_v0_1.json",
    "factorised_source_binding": "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_WP4_FACTORISED_SOURCE_BINDING_MANIFEST_v0_1.json",
    "dense_secondary_scope": "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_FACTORISED_DENSE_MICRO_SOURCE_SCOPE_BINDING_v0_1.json",
    "tvx_source_completeness": "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_TVX_EMPIRICAL_GRAMMAR_EVIDENCE_SOURCE_COMPLETENESS_MANIFEST_v0_1.json",
    "tvx_reproduction": "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_TVX_ANALYSIS_REPRODUCTION_PACK_v0_1.json",
    "c0c_concordance": "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_C0C_SOURCE_CROSS_EXPORT_CONCORDANCE_RECEIPT_v0_1.json",
    "c0b_c0c_lineage": "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_C0B_C0C_SOURCE_LINEAGE_v0_1.json",
    "mechanics_registry": "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_FACTORISED_MECHANICS_REGISTRY_v0_1.json",
    "mechanics_fixture": "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_SYNTHETIC_QUALIFICATION_FIXTURE_v0_1.json",
    "algorithmic_assurance": "docs/programmes/c2s-sptoi-v0-1/wp7/C2S_SPTOI_WP7_RICH_ALGORITHMIC_ASSURANCE_RECEIPT_v0_1.json",
    "null_qualification": "docs/programmes/c2s-sptoi-v0-1/wp8/C2S_SPTOI_WP8_FACTORISED_NULL_QUALIFICATION_PACK_v0_1.json",
    "diagnostic_qualification": "docs/programmes/c2s-sptoi-v0-1/wp9/C2S_SPTOI_WP9_FACTORISED_DIAGNOSTIC_QUALIFICATION_PACK_v0_1.json",
    "integrated_assurance": "docs/programmes/c2s-sptoi-v0-1/wp10/C2S_SPTOI_WP10_INTEGRATED_ASSURANCE_RECEIPT_v0_1.json",
    "independent_g3_review": "docs/programmes/c2s-sptoi-v0-1/wp3/C2S_SPTOI_G3_ALG_INDEPENDENT_DECISION_v0_1.json",
}

CUSTODY_BINDINGS = {
    "WP5": "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_LABORATORY_CUSTODY_RECEIPT_v0_2.json",
    "WP6": "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_LABORATORY_CUSTODY_RECEIPT_v0_1.json",
    "WP7": "docs/programmes/c2s-sptoi-v0-1/wp7/C2S_SPTOI_WP7_LABORATORY_CUSTODY_RECEIPT_v0_1.json",
    "WP8": "docs/programmes/c2s-sptoi-v0-1/wp8/C2S_SPTOI_WP8_LABORATORY_CUSTODY_RECEIPT_v0_1.json",
    "WP9": "docs/programmes/c2s-sptoi-v0-1/wp9/C2S_SPTOI_WP9_LABORATORY_CUSTODY_RECEIPT_v0_1.json",
    "WP10": "docs/programmes/c2s-sptoi-v0-1/wp10/C2S_SPTOI_WP10_LABORATORY_CUSTODY_RECEIPT_v0_1.json",
}


class PreGrealError(ValueError):
    def __init__(self, reason_code: str, detail: str):
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


def _load(root: Path, relative: str) -> dict[str, Any]:
    try:
        value = json.loads((root / relative).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreGrealError("BOUND_RECORD_UNAVAILABLE", relative) from exc
    if not isinstance(value, dict):
        raise PreGrealError("BOUND_RECORD_INVALID", relative)
    return value


def _file_binding(root: Path, role: str, relative: str) -> dict[str, Any]:
    path = root / relative
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PreGrealError("BOUND_RECORD_UNAVAILABLE", relative) from exc
    return {
        "role": role,
        "path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def _custody_summary(packet: str, path: str, value: dict[str, Any]) -> dict[str, Any]:
    frozen = value.get("frozen_bundle", {})
    return {
        "packet": packet,
        "path": path,
        "status": value.get("custody_status", value.get("catalogue_state")),
        "drive_file_id": value.get("drive_file_id", frozen.get("drive_file_id")),
        "artifact_sha256": value.get(
            "artifact_sha256", value.get("sha256", frozen.get("sha256"))
        ),
        "artifact_size_bytes": value.get(
            "artifact_size_bytes", value.get("size_bytes", frozen.get("size_bytes"))
        ),
    }


def build_pre_greal_packet(root: Path) -> dict[str, Any]:
    values = {role: _load(root, path) for role, path in BINDINGS.items()}
    plan = values["ratified_plan"]
    protocol = values["protocol_binding"]
    owner = values["owner_stream_binding"]
    factor_source = values["factorised_source_binding"]
    dense = values["dense_secondary_scope"]
    source = values["tvx_source_completeness"]
    reproduction = values["tvx_reproduction"]
    concordance = values["c0c_concordance"]
    lineage = values["c0b_c0c_lineage"]
    registry = values["mechanics_registry"]
    fixture = values["mechanics_fixture"]
    assurance = values["algorithmic_assurance"]
    nulls = values["null_qualification"]
    diagnostics = values["diagnostic_qualification"]
    integrated = values["integrated_assurance"]
    g3_review = values["independent_g3_review"]
    custody_values = {packet: _load(root, path) for packet, path in CUSTODY_BINDINGS.items()}

    if plan["plan_id"] != "OVC-EML-C2S-SPTO-CONFORMANCE-PREREG-IMPLEMENTATION-PLAN-0.1-R3-TVX-R31-PRR1-RATIFIED":
        raise PreGrealError("PLAN_IDENTITY_MISMATCH", plan["plan_id"])
    if protocol["operator_decision"] != "PASS" or protocol["protocol_id"] != "OVC-EML-GRAMMAR-0002-RP-0.1-R1":
        raise PreGrealError("PROTOCOL_AUTHORITY_MISSING", str(protocol.get("protocol_id")))
    if any(value.get("protected_source_access") not in (None, "NONE") for value in values.values()):
        raise PreGrealError("PROTECTED_SOURCE_LEAK", "bound input")

    file_bindings = [
        _file_binding(root, role, path) for role, path in sorted(BINDINGS.items())
    ] + [
        _file_binding(root, f"laboratory_custody_{packet.lower()}", path)
        for packet, path in sorted(CUSTODY_BINDINGS.items())
    ]

    missing_rounds = [
        row["round_id"] for row in source["sources"] if row["current_exact_source"] != "BOUND_EXACT"
    ]
    population = diagnostics["population_manifest"]
    fixture_population = fixture["population_manifest"]
    body = {
        "schema": "ovc-c2s-sptoi-pre-greal-operator-packet/v0.1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "gate_id": GATE_ID,
        "gate_class": "OPERATOR_REQUIRED",
        "status": "GREAL_PACKET_READY",
        "baseline_main": BASELINE_MAIN,
        "baseline_tree": BASELINE_TREE,
        "governing_authority": {
            "plan_id": plan["plan_id"],
            "plan_docx_sha256": plan["exact_external_plan_docx"]["sha256"],
            "plan_docx_size_bytes": plan["exact_external_plan_docx"]["size_bytes"],
            "accepted_er3_amendments": plan["r3_review"]["accepted_amendments"],
            "protocol_id": protocol["protocol_id"],
            "protocol_docx_sha256": protocol["ratified_docx_sha256"],
            "protocol_docx_size_bytes": protocol["ratified_docx_size_bytes"],
            "protocol_operator_decision": values["protocol_operator_decision"]["decision"],
            "owner_scope_amendment_id": dense["owner_scope_amendment_id"],
            "owner_scope_amendment_sha256": dense["owner_scope_amendment_sha256"],
        },
        "source_and_read_surface": {
            "owner_primary": {
                "type": "OWNER_STRUCTURAL_SNAPSHOT_STREAM",
                "binding_id": owner["c2_owner_stream_binding_id"],
                "owner_generation_id": owner["owner_generation_id"],
                "owner_authority_id": owner["owner_authority_id"],
                "read_authority_id": owner["read_authority_id"],
                "owner_resolution_id": owner["owner_resolution_id"],
                "mode": owner["population_mode"],
                "record_policy": owner["record_policy"],
                "chronology": owner["chronology"],
                "break_policy": owner["break_policy"],
                "missingness_policy": owner["missingness_policy"],
            },
            "dense_secondary": {
                "role": dense["source_role"],
                "may_generate": dense["may_generate"],
                "may_repair_owner_state_or_target": dense["may_create_replace_or_repair_owner_state_or_target"],
                "exact_binding": dense["exact_dense_source_binding"],
                "status": dense["exact_dense_source_status"],
                "real_source_execution_eligible": dense["factorised_real_source_execution_eligible"],
            },
            "factorised_source_binding_manifest_id": factor_source["factorised_source_binding_manifest_id"],
            "factorised_source_status": factor_source["status"],
            "c2e": factor_source["c2e"],
            "c2p": factor_source["c2p"],
            "opt_c_opt_d_validation_sff": factor_source["opt_c_opt_d_validation_sff"],
        },
        "tvx_source_and_reproduction": {
            "completeness_status": source["status"],
            "required_round_denominator": len(source["required_rounds"]),
            "required_rounds": source["required_rounds"],
            "not_exactly_bound_rounds": missing_rounds,
            "reproduction_status": reproduction["execution_status"],
            "reproduction_interpretation": reproduction["interpretation"],
            "missing_prerequisites": reproduction["missing_prerequisites"],
            "c0b_classification": lineage["c0b"]["state"],
            "c0b_byte_equivalent": lineage["c0b"]["byte_equivalent"],
            "c0c_classification": concordance["concordance_state"],
            "c0c_byte_equivalent": lineage["c0c"]["byte_equivalent"],
            "c0c_join_eligibility": concordance["join_eligibility"],
            "c0c_join_denial_reason": concordance["denial_reason"],
        },
        "population_and_training": {
            "qualification_population_scope": diagnostics["maturity"],
            "universal_owner_transition_denominator": population["owner_transition_opportunities"],
            "grammar_evaluation_denominator": population["grammar_evaluation_opportunities"],
            "representation_view_denominator": population["representation_views"],
            "explicit_declared_view_row_denominator": diagnostics["representation_set_completeness"]["expected_view_denominator"],
            "computed_declared_view_rows": diagnostics["representation_set_completeness"]["computed_views"],
            "non_survivor_promotion": "FORBIDDEN",
            "training_frontier": fixture["training_frontier_manifest"],
            "fixture_population_manifest_id": fixture_population["manifest_id"],
            "diagnostic_population_manifest_id": population["manifest_id"],
        },
        "factorised_mechanics": {
            "registry_id": registry["registry_id"],
            "micro_factorisation_constitution": fixture["factorisation_constitution"],
            "carrier_decoder_manifest": fixture["decoder_manifest"],
            "declared_representation_set": registry["declared_representation_set"],
            "antecedent_hierarchies": registry["antecedent_hierarchies"],
            "support_policy": registry["support_policy"],
            "comparison_target_pack": fixture["comparison_target_manifest"],
            "target_hierarchies": registry["target_hierarchies"],
            "relation_support_trace": {
                "frontier_record_count": len(fixture["frontier_records"]),
                "trace_set_id": fixture["trace_set"]["trace_set_id"],
                "trace_set_complete": fixture["trace_set"]["complete"],
                "algorithmic_assurance_check": assurance["checks"][9],
            },
        },
        "null_coupling": {
            "null_spec_ids": sorted(nulls["null_specs"]),
            "total_replica_count": nulls["total_replica_count"],
            "all_representations_from_one_world_per_replica": nulls["all_representations_derived_from_one_world_per_replica"],
            "independent_representation_draws": nulls["independent_representation_draws"],
            "pack_id": nulls["pack_id"],
        },
        "opportunity_exposure_and_freshness": {
            "specification_opportunity_ledger": diagnostics["specification_opportunity_ledger"],
            "design_exposure_manifest": diagnostics["design_exposure_manifest"],
            "claim_exposure_matrix": diagnostics["claim_exposure_matrix"],
            "claim_freshness_cap": diagnostics["claim_freshness_cap"],
            "temporal_stability_vector": diagnostics["temporal_segment_context"]["temporal_stability_vector"],
            "empirical_claim_status": diagnostics["scientific_claims"],
        },
        "derivation_capacity_and_retention": {
            "derivation_manifest": fixture["derivation_manifest"],
            "dependency_change_assurance": integrated["derivation_dependency_change"],
            "integrated_equivalence": integrated["equivalence"],
            "failure_assurance": integrated["failure_assurance"],
            "retention": integrated["retention"],
            "measured_capacity": integrated["measured_capacity"],
            "capacity_result": integrated["capacity_result"],
        },
        "reviewer_independence": {
            "historical_g3_reviewer": g3_review["reviewer"],
            "historical_g3_decision": g3_review["decision"],
            "wp7_algorithmic_assurance": {
                "implementation_separate_from_mechanics": True,
                "check_count": assurance["check_count"],
                "result": assurance["result"],
                "receipt_id": assurance["receipt_id"],
            },
            "wp11_independent_scientific_decision_claimed": False,
            "genuine_independent_authority": "OPERATOR_DECISION_REQUIRED_AT_GREAL",
        },
        "laboratory_custody": [
            _custody_summary(packet, CUSTODY_BINDINGS[packet], value)
            for packet, value in sorted(custody_values.items())
        ],
        "qa_and_file_bindings": {
            "bound_record_count": len(file_bindings),
            "file_bindings": file_bindings,
            "wp7_assurance_result": assurance["result"],
            "wp8_null_result": nulls["result"],
            "wp10_capacity_result": integrated["capacity_result"],
        },
        "warnings": [
            "PROTECTED_2021_2023_SOURCE_NOT_ACCESSED_AND_REMAINS_DENIED",
            "OWNER_STREAM_BINDING_IS_SYNTHETIC_QUALIFICATION_MODE_NOT_EMPIRICAL_2021_2023_POPULATION",
            "EXACT_DENSE_INTERSTITIAL_SECONDARY_SOURCE_NOT_YET_PUBLICLY_BOUND",
            "TVX_EVIDENCE_SOURCE_STATUS_PARTIAL_SOURCE_LIMITED_AND_R9X_R16_R21_BYTES_ABSENT",
            "R22_TO_R31_EXACT_LOAD_BEARING_EXECUTABLE_SOURCES_INCOMPLETE_OR_ABSENT",
            "C0C_RECEIPT_CONCORDANT_NOT_BYTE_REPRODUCED_AND_JOIN_DENIED",
            "WP6_TO_WP10_OUTPUTS_ARE_SOURCE_FREE_OR_SYNTHETIC_QUALIFICATION_NOT_EMPIRICAL_FINDINGS",
            "VALIDATION_LOCKED_UNCONSUMED",
            "GREAL_PASS_WOULD_NOT_AUTHORISE_CANDIDATE_GENERATION",
        ],
        "unresolved_issues": [
            "BIND_EXACT_PROTECTED_SOURCE_RELEASE_MANIFEST_AND_BYTES_ONLY_AFTER_GREAL_PASS",
            "BIND_EXACT_OWNER_POPULATION_AND_DENSE_SECONDARY_SOURCE_FOR_PHASE_A",
            "RESOLVE_TVX_PARTIAL_SOURCE_LIMITATIONS_OR_PRESERVE_THEM_AS_NON_LOAD_BEARING",
            "REQUIRE_C2S_SPTOI_GREAL_FEAS_PASS_BEFORE_ANY_CANDIDATE_GENERATING_SEARCH",
        ],
        "proposed_real_source_authority_delta": {
            "decision_token": "PASS_REAL_SOURCE_FEASIBILITY_ONLY",
            "if_operator_passes": {
                "protected_source_access": "ALLOW_EXACT_BOUND_2021_2023_SOURCE_FOR_PHASE_A_FEASIBILITY_ONLY",
                "source_binding": "REQUIRE_EXACT_RELEASE_MANIFEST_BYTE_HASH_AUTHORITY_CHRONOLOGY_BREAK_RESET_MISSINGNESS_AND_POPULATION_BINDINGS_BEFORE_COMPUTE",
                "permitted_execution": "PHASE_A_REAL_SOURCE_FEASIBILITY_ONLY",
                "required_output": "RealSourceFeasibilityExposureRecord",
                "structurally_suppressed_outputs": [
                    "MOTIF_OUTPUTS",
                    "SUPPORT_OUTPUTS",
                    "CANDIDATE_OUTPUTS",
                    "SCALAR_CONFIDENCE",
                    "PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION_OUTPUTS",
                ],
                "candidate_generating_factorised_search": "DENIED_PENDING_C2S_SPTOI_GREAL_FEAS_PASS",
                "validation": "LOCKED_UNCONSUMED",
                "candidate_freeze": "NONE",
                "semantic_admission": "NONE",
                "publication": "NONE",
            },
            "allowed_operator_decisions": [
                "PASS_REAL_SOURCE_FEASIBILITY_ONLY",
                "ADJUST",
                "DEFER",
                "BLOCK",
                "QUARANTINE",
            ],
            "exact_operator_command_for_pass": "OVC APPROVE C2S-SPTOI-GREAL-SCI-PREREG PASS_REAL_SOURCE_FEASIBILITY_ONLY",
        },
        "rollback": "If GREAL is not passed, keep protected source denied and preserve WP0-WP11 plus custody evidence. If a later Phase A feasibility defect occurs, stop, quarantine affected artifacts, preserve exposure records, and forward-supersede; never rewrite history or promote feasibility outputs.",
        "current_authority": {
            "protected_source_access": "DENIED",
            "factorised_evidence_execution": "DENIED",
            "validation": "LOCKED_UNCONSUMED",
            "candidate_generation": "DENIED",
            "candidate_freeze": "NONE",
            "semantic_authority": "NONE",
            "publication": "NONE",
            "probability_risk_exposure_trading_execution": "NONE",
        },
        "decision": "UNDECIDED_OPERATOR_REQUIRED",
        "next_lawful_action": "PRESENT_THIS_EXACT_PACKET_TO_OPERATOR_AND_STOP",
    }
    body = json.loads(json.dumps(body, sort_keys=True))
    body["operator_packet_id"] = content_id("PreGrealOperatorPacket/v1", body)
    return body
