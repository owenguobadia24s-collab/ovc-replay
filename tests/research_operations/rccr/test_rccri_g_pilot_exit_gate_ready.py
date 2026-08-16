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


def test_programme_pointer_advances_after_operator_pass_without_owner_authority():
    pointer = load("registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json")
    state = load("registries/implementation/rccr_v0_1/RCCR_V0_1_STATE_v0_11.json")
    assert pointer["status"] == state["status"] == "APPROVED"
    assert pointer["current_gate"] == state["current_gate"] == "RCCRI-G-PILOT-EXIT"
    assert pointer["operator_pending"] == state["operator_pending"] == []
    assert pointer["scaleout_authority"] == state["scaleout_authority"] == "AUTHORIZED_BOUNDED_WP6B_WP7B_WP8"
    assert pointer["authorized_follow_on_packets"] == state["authorized_follow_on_packets"] == ["RCCRI-WP6B", "RCCRI-WP7B", "RCCRI-WP8"]
    assert pointer["real_source_ec1_authority"] == state["real_source_ec1_authority"] == "NONE"
    assert pointer["path2_real_source_authority"] == state["path2_real_source_authority"] == "NOT_GRANTED"
    assert pointer["owner_capability_activation"] == state["owner_capability_activation"] == "DENIED"
    assert pointer["validation"] == state["validation"] == "LOCKED_UNCONSUMED"
    assert pointer["last_completed_packet"] == state["last_completed_packet"] == "RCCRI-WP7A"
    assert pointer["last_merge_commit"] == state["last_merge_commit"] == "bd2a5af60d2f26320e873e7cd72875397b85a9d7"
    assert pointer["next_packet"] == state["next_packet"] == "RCCRI-WP6B"
