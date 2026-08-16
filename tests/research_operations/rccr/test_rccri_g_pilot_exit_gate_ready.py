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
        gate_id=stored["gate_id"],
        gate_instance_id=stored["gate_instance_id"],
        programme_id=stored["programme_id"],
        plan_id=stored["plan_id"],
        plan_version=stored["plan_version"],
        packet_id=stored["packet_id"],
        baseline_commit=stored["baseline_commit"],
        candidate_commit=stored["candidate_commit"],
        current_authority_envelope_id=stored["current_authority_envelope_id"],
        current_authority_hash=stored["current_authority_hash"],
        proposed_pass_effect_hash=stored["proposed_pass_effect_hash"],
        proposed_authority_hash=stored["proposed_authority_hash"],
        authority_delta=("OPR.SCOPE_EXPANSION",),
        net_new_delta=("OPR.SCOPE_EXPANSION",),
        acceptance_conditions_passed=True,
        qa_status="PASS",
        blocking_issue_count=0,
        rollback_defined=True,
        gate_function_hint=GateFunction.AUTHORITY_DECISION,
        evidence_refs=tuple(stored["evidence_refs"]),
    )
    actual = classify_gate(inp).to_dict()
    for key in (
        "execution_class",
        "gate_function",
        "reserved_predicate_hits",
        "reason_codes",
        "assessment_id",
    ):
        assert actual[key] == stored[key]
    assert actual["execution_class"] == ExecutionClass.OPERATOR_REQUIRED.value


def test_authority_envelopes_are_exact_and_owner_authority_remains_denied():
    stored = load("docs/releases/rccr-v0-1/rccri-g-pilot-exit/RCCRI_G_PILOT_EXIT_GATE_AUTHORITY_ASSESSMENT.json")
    current = {
        "authority_envelope_id": "RCCR_AUTHORITY_ENVELOPE_PRE_PILOT_EXIT",
        "owner_capability_activation": "DENIED",
        "real_source_ec1_authority": "NONE",
        "scaleout_authority": "DENIED",
        "scope": "RCCR_WP0_WP7A_PRE_EVIDENTIARY_PILOT",
        "validation": "LOCKED_UNCONSUMED",
    }
    proposed = {
        "authorized_follow_on_packets": ["RCCRI-WP6B", "RCCRI-WP7B", "RCCRI-WP8"],
        "owner_capability_activation": "DENIED",
        "real_source_ec1_authority": "NONE",
        "scope": "BOUNDED_NON_AUTHORITATIVE_PATH2_EXTERNAL_BOOTSTRAP_READ_MODELS",
        "validation": "LOCKED_UNCONSUMED",
    }
    assert canonical_sha256(current) == stored["current_authority_hash"]
    assert canonical_sha256(proposed) == stored["proposed_authority_hash"]
    assert canonical_sha256({"current": current, "proposed": proposed}) == stored["proposed_pass_effect_hash"]


def test_gate_packet_is_complete_and_non_scientific():
    gate = load("docs/releases/rccr-v0-1/rccri-g-pilot-exit/RCCRI_G_PILOT_EXIT_GATE_PACKET.json")
    assert gate["execution_class"] == "OPERATOR_REQUIRED"
    assert gate["proposed_pass_delta"]["reason_code"] == "OPR.SCOPE_EXPANSION"
    assert gate["proposed_pass_delta"]["owner_capability_activation"] == "DENIED"
    assert gate["proposed_pass_delta"]["real_source_ec1_authority"] == "NONE"
    assert gate["proposed_pass_delta"]["validation"] == "LOCKED_UNCONSUMED"
    assert gate["acceptance_conditions"]["review_trigger_over_30_percent"] is False
    assert gate["acceptance_conditions"]["observed_workaround_count"] == 0
    assert gate["acceptance_conditions"]["unsupported_information_gap_promotions"] == 0
    assert gate["recommended_decision"] == "PASS"
    assert set(gate["allowed_decisions"]) == {"PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"}


def test_programme_pointer_stops_at_operator_gate():
    pointer = load("registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json")
    state = load("registries/implementation/rccr_v0_1/RCCR_V0_1_STATE_v0_10.json")
    assert pointer["status"] == state["status"] == "GATE_READY"
    assert pointer["current_gate"] == state["current_gate"] == "RCCRI-G-PILOT-EXIT"
    assert pointer["operator_pending"] == state["operator_pending"] == ["RCCRI-G-PILOT-EXIT"]
    assert pointer["scaleout_authority"] == state["scaleout_authority"] == "DENIED_PENDING_OPERATOR_DECISION"
    assert pointer["real_source_ec1_authority"] == state["real_source_ec1_authority"] == "NONE"
    assert pointer["validation"] == state["validation"] == "LOCKED_UNCONSUMED"
    assert pointer["last_completed_packet"] == state["last_completed_packet"] == "RCCRI-WP7A"
    assert pointer["last_merge_commit"] == state["last_merge_commit"] == "bd2a5af60d2f26320e873e7cd72875397b85a9d7"
