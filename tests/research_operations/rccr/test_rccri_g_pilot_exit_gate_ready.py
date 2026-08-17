from __future__ import annotations

import json
from pathlib import Path

from ovc.development.authority_gates import ExecutionClass, GateAssessmentInput, GateFunction, classify_gate
from ovc.development.identity import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_pilot_exit_is_operator_required_by_exact_scope_expansion_delta():
    stored = load("docs/releases/rccr-v0-1/rccri-g-pilot-exit/RCCRI_G_PILOT_EXIT_GATE_AUTHORITY_ASSESSMENT.json")
    inp = GateAssessmentInput(
        gate_id=stored["gate_id"], gate_instance_id=stored["gate_instance_id"], programme_id=stored["programme_id"],
        plan_id=stored["plan_id"], plan_version=stored["plan_version"], packet_id=stored["packet_id"],
        baseline_commit=stored["baseline_commit"], candidate_commit=stored["candidate_commit"],
        current_authority_envelope_id=stored["current_authority_envelope_id"], current_authority_hash=stored["current_authority_hash"],
        proposed_pass_effect_hash=stored["proposed_pass_effect_hash"], proposed_authority_hash=stored["proposed_authority_hash"],
        authority_delta=("OPR.SCOPE_EXPANSION",), net_new_delta=("OPR.SCOPE_EXPANSION",),
        acceptance_conditions_passed=True, qa_status="PASS", blocking_issue_count=0, rollback_defined=True,
        gate_function_hint=GateFunction.AUTHORITY_DECISION, evidence_refs=tuple(stored["evidence_refs"]),
    )
    actual = classify_gate(inp).to_dict()
    for key in ("execution_class", "gate_function", "assessment_id"):
        assert actual[key] == stored[key]
    for key in ("reserved_predicate_hits", "reason_codes"):
        assert tuple(actual[key]) == tuple(stored[key])
    assert actual["execution_class"] == ExecutionClass.OPERATOR_REQUIRED.value


def test_authority_envelopes_are_exact_and_owner_authority_remains_denied():
    stored = load("docs/releases/rccr-v0-1/rccri-g-pilot-exit/RCCRI_G_PILOT_EXIT_GATE_AUTHORITY_ASSESSMENT.json")
    current = {"authority_envelope_id":"RCCR_AUTHORITY_ENVELOPE_PRE_PILOT_EXIT","owner_capability_activation":"DENIED","real_source_ec1_authority":"NONE","scaleout_authority":"DENIED","scope":"RCCR_WP0_WP7A_PRE_EVIDENTIARY_PILOT","validation":"LOCKED_UNCONSUMED"}
    proposed = {"authorized_follow_on_packets":["RCCRI-WP6B","RCCRI-WP7B","RCCRI-WP8"],"owner_capability_activation":"DENIED","real_source_ec1_authority":"NONE","scope":"BOUNDED_NON_AUTHORITATIVE_PATH2_EXTERNAL_BOOTSTRAP_READ_MODELS","validation":"LOCKED_UNCONSUMED"}
    assert canonical_sha256(current) == stored["current_authority_hash"]
    assert canonical_sha256(proposed) == stored["proposed_authority_hash"]
    assert canonical_sha256({"current": current, "proposed": proposed}) == stored["proposed_pass_effect_hash"]


def test_pre_pilot_exit_fixture_currentness_is_rechecked_against_exact_main():
    recheck = load("docs/releases/rccr-v0-1/rccri-g-pilot-exit/RCCRI_PILOT_EXIT_FIXTURE_CURRENTNESS_RECHECK.json")
    assert recheck["recheck_main"] == "fff6bf2f8ed13060dba5030db3b62da992d5fb94"
    assert recheck["population_total"] == 36
    assert recheck["silent_sampling_forbidden"] is True
    assert recheck["stale_fixture_count"] == 0
    assert recheck["currentness"] == "PASS"
    assert recheck["recheck_result"] == "PASS_NO_SEMANTIC_TRIGGER"
    assert recheck["triggered_semantic_changes"] == []
    assert all(item["status"] == "UNCHANGED" for item in recheck["dependency_recheck"].values())
    assert recheck["authority_effect"] == "NONE"


def test_gate_packet_is_complete_and_non_scientific():
    gate = load("docs/releases/rccr-v0-1/rccri-g-pilot-exit/RCCRI_G_PILOT_EXIT_GATE_PACKET.json")
    assert gate["execution_class"] == "OPERATOR_REQUIRED"
    assert gate["proposed_pass_delta"]["reason_code"] == "OPR.SCOPE_EXPANSION"
    assert gate["proposed_pass_delta"]["owner_capability_activation"] == "DENIED"
    assert gate["proposed_pass_delta"]["real_source_ec1_authority"] == "NONE"
    assert gate["proposed_pass_delta"]["validation"] == "LOCKED_UNCONSUMED"
    assert gate["acceptance_conditions"]["review_trigger_over_30_percent"] is False
    assert gate["acceptance_conditions"]["fixture_semantic_trigger_count"] == 0
    assert gate["acceptance_conditions"]["observed_workaround_count"] == 0
    assert gate["acceptance_conditions"]["unsupported_information_gap_promotions"] == 0
    budget = gate["human_review_budget_recommendation"]
    assert budget["max_human_review_required_share"] == 0.30
    assert budget["scientific_threshold"] is False
    assert budget["numeric_throughput_slo"].startswith("NOT_ESTIMABLE")
    assert gate["recommended_decision"] == "PASS"
    assert set(gate["allowed_decisions"]) == {"PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"}


def test_operator_pass_materialises_only_bounded_scaleout_and_budget():
    decision = load("docs/releases/rccr-v0-1/rccri-g-pilot-exit/RCCRI_G_PILOT_EXIT_OPERATOR_DECISION.json")
    budget = load("registries/research_operations/rccr/v0_1/RCCR_HUMAN_REVIEW_BUDGET_v0_1.json")
    assert decision["decision"] == "PASS"
    assert decision["decision_instruction"] == "OVC APPROVE RCCRI-G-PILOT-EXIT"
    assert decision["reserved_delta"] == ["OPR.SCOPE_EXPANSION"]
    assert decision["approved_effect"]["authorized_follow_on_packets"] == ["RCCRI-WP6B", "RCCRI-WP7B", "RCCRI-WP8"]
    assert decision["approved_effect"]["owner_capability_activation"] == "DENIED"
    assert decision["approved_effect"]["real_source_ec1_authority"] == "NONE"
    assert decision["approved_effect"]["validation"] == "LOCKED_UNCONSUMED"
    assert budget["budget_id"] == "RCCR-HUMAN-REVIEW-BUDGET-v0.1-BOOTSTRAP"
    assert budget["operational_triggers"]["human_review_required_share_gt"] == 0.30
    assert budget["trigger_semantics"]["human_review_share"] == "OPERATIONAL_REVIEW_TRIGGER_ONLY_NOT_SCIENTIFIC_THRESHOLD"
    assert budget["authority_effect"] == "NONE"


def test_programme_pointer_preserves_pilot_and_g7b_history_while_wp8_advances():
    pointer = load("registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json")
    pilot_exit = load("registries/implementation/rccr_v0_1/RCCR_V0_1_STATE_v0_11.json")
    g7b = load("registries/implementation/rccr_v0_1/RCCR_V0_1_STATE_v0_14.json")
    wp8_qa = load("registries/implementation/rccr_v0_1/RCCR_V0_1_STATE_v0_15.json")
    g8 = load("registries/implementation/rccr_v0_1/RCCR_V0_1_STATE_v0_16.json")
    decision = load("docs/releases/rccr-v0-1/rccri-wp8/RCCRI_G8_DELEGATED_DECISION.json")

    # Immutable pilot-exit generation remains exactly approved and non-authoritative.
    assert pilot_exit["status"] == "APPROVED"
    assert pilot_exit["current_gate"] == "RCCRI-G-PILOT-EXIT"
    assert pilot_exit["operator_pending"] == []
    assert pilot_exit["scaleout_authority"] == "AUTHORIZED_BOUNDED_WP6B_WP7B_WP8"
    assert pilot_exit["authorized_follow_on_packets"] == ["RCCRI-WP6B", "RCCRI-WP7B", "RCCRI-WP8"]
    assert pilot_exit["real_source_ec1_authority"] == "NONE"
    assert pilot_exit["path2_real_source_authority"] == "NOT_GRANTED"
    assert pilot_exit["owner_capability_activation"] == "DENIED"
    assert pilot_exit["validation"] == "LOCKED_UNCONSUMED"
    assert pilot_exit["last_completed_packet"] == "RCCRI-WP7A"
    assert pilot_exit["last_merge_commit"] == "bd2a5af60d2f26320e873e7cd72875397b85a9d7"
    assert pilot_exit["next_packet"] == "RCCRI-WP6B"

    # G7B delegated PASS remains an immutable predecessor record after physical materialisation.
    assert g7b["status"] == "APPROVED"
    assert g7b["packet_id"] == "RCCRI-WP7B"
    assert g7b["authority_delta"] == "NONE"
    assert g7b["next_packet"] == "RCCRI-WP8_AFTER_G7B_INTEGRATION"
    assert g7b["authority_effect"] == "NONE"

    # WP8 QA remains an immutable predecessor generation even after delegated G8 approval.
    assert wp8_qa["status"] == "QA_REVIEW"
    assert wp8_qa["packet_id"] == "RCCRI-WP8"
    assert wp8_qa["current_gate"] == "RCCRI-G8"
    assert wp8_qa["next_packet"] is None
    assert wp8_qa["authority_effect"] == "NONE"

    # Delegated G8 may advance current state to APPROVED, but not falsely to terminal completion before merge.
    assert g8["status"] == "APPROVED"
    assert g8["packet_id"] == "RCCRI-WP8"
    assert g8["authority_delta"] == "NONE"
    assert g8["merge_commit"] is None
    assert g8["next_packet"] is None
    assert g8["authority_effect"] == "NONE"
    assert decision["decision"] == "PASS"
    assert decision["decision_source"] == "DELEGATED_PLAN_AUTHORITY"
    assert decision["authority_delta"] == "NONE"
    assert decision["merge_commit"] == "PENDING_PHYSICAL_MATERIALISATION"
    assert decision["next_packet"] is None

    # Current pointer advances through G8 approval while preserving all owner firewalls and pre-merge truth.
    assert pointer["current_state"] == "RCCR_V0_1_STATE_v0_16.json"
    assert pointer["status"] == "APPROVED"
    assert pointer["current_packet"] == "RCCRI-WP8"
    assert pointer["current_gate"] == "RCCRI-G8"
    assert pointer["gate_status"] == "PASS_DELEGATED_PENDING_FINAL_HEAD_AND_INTEGRATION"
    assert pointer["last_completed_packet"] == "RCCRI-WP7B"
    assert pointer["last_merge_commit"] == "f8711a2fa0d643c87abb45a0985bf526c0f9915a"
    assert pointer["operator_pending"] == []
    assert pointer["scaleout_authority"] == "AUTHORIZED_BOUNDED_WP6B_WP7B_WP8"
    assert pointer["authorized_follow_on_packets"] == []
    assert pointer["next_packet"] is None
    assert pointer["owner_authority_frontier"]["ec1"]["state"] == "AUTHORISED_BOUNDED"
    assert pointer["owner_authority_frontier"]["path2_external"]["state"] == "AUTHORISED_BOUNDED"
    assert pointer["owner_authority_frontier"]["validation"]["state"] == "LOCKED_UNCONSUMED"
    assert pointer["rccr_consumption_boundary"]["real_source_ec1_consumption"] == "DENIED_BY_RCCRI_WP6B_SCOPE"
    assert pointer["rccr_consumption_boundary"]["path2_real_source_consumption"] == "DENIED_BY_RCCRI_WP6B_SCOPE"
    assert pointer["rccr_consumption_boundary"]["owner_capability_activation"] == "DENIED"
    assert pointer["rccr_consumption_boundary"]["validation_consumption"] == "DENIED"
    assert pointer["authority_effect"] == "NONE"
