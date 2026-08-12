from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp9/DSAI_G9B_ORCH2_ACTIVATION_DECISION_PACKET.json"
QA = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp9/DSAI_WP9_ORCH2_QA_PACKET.json"
QUAL = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp9/DSAI_WP9_ORCH2_QUALIFICATION.json"
CANDIDATE = ROOT / "registries/development/skills/orch2_activation_candidate_v0_1.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_25.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_g9b_packet_is_operator_required_pending_and_recommends_pass():
    gate = _load(GATE)
    assert gate["gate_id"] == "DSAI-G9B"
    assert gate["gate_class"] == "OPERATOR_REQUIRED"
    assert gate["decision"] == "PENDING_OPERATOR"
    assert gate["recommended_decision"] == "PASS"
    assert gate["operator_command_if_accept"] == "OVC APPROVE DSAI-G9B PASS ORCH2"
    assert gate["authority_effect"] == "NONE_UNTIL_OPERATOR_DECISION"


def test_g9b_proposed_scope_is_exact_low_risk_serial_and_no_direct_main():
    delta = _load(GATE)["proposed_authority_delta"]
    assert delta["kind"] == "BOUNDED_DELEGATED_AUTO_RATIFICATION_AND_ELIGIBLE_SQUASH_MERGE"
    assert delta["scope"] == "LOW_RISK_IMPLEMENTATION_PACKET_CLASS_ONLY"
    assert delta["concurrency"] == "SERIAL_REQUIRED"
    assert delta["auto_ratification"] == "WHOLLY_AUTO_EXECUTABLE_GATES_ONLY"
    assert delta["required_authority_delta"] == "NONE"
    assert delta["merge_target"] == "main"
    assert delta["merge_method"] == "squash"
    assert delta["direct_main_mutation"] is False
    assert delta["force_push"] is False
    assert delta["history_rewrite"] is False


def test_pre_g9b_candidate_and_programme_state_remain_inactive():
    candidate = _load(CANDIDATE)["entries"][0]
    assert candidate["effective"] is False
    assert candidate["enabled_packet_classes"] == ["LOW_RISK_IMPLEMENTATION"]
    assert candidate["g9b_authority"] == "NOT_GRANTED"
    assert candidate["delegated_auto_ratification"] == "INACTIVE_PENDING_G9B"
    assert candidate["automatic_merge"] == "INACTIVE_PENDING_G9B"
    assert candidate["direct_main_mutation"] is False

    state = _load(STATE)
    assert state["programme_status"] == "WP9_G9B_GATE_READY"
    assert state["current_gate"] == "DSAI-G9B"
    assert state["orch2_candidate"]["effective"] is False
    assert state["authority"]["orch_2"] == "INACTIVE_PENDING_DSAI_G9B"
    assert state["authority"]["delegated_auto_ratification"] == "INACTIVE"
    assert state["authority"]["automatic_merge"] is False
    assert state["authority"]["merge_authority"] == "NONE"
    assert state["authority"]["direct_main_mutation"] is False
    assert state["authority"]["validation"] == "DENIED"
    assert state["mandatory_stop"]["active"] is True


def test_qualification_and_qa_are_pass_with_no_warnings():
    qualification = _load(QUAL)
    qa = _load(QA)
    assert qualification["qualification_decision"] == "PASS_MECHANICAL"
    assert qualification["authority_effect"] == "NONE"
    assert qualification["warnings"] == []
    assert qualification["unresolved_issues"] == []
    assert qualification["unresolved_reviews"] == []
    assert qualification["acceptance_conditions"]["real_disposable_git_sandbox_squash"] == "PASS_SINGLE_PARENT"
    assert qa["qa_decision"] == "PASS"
    assert qa["qa_recommendation"] == "PASS_TO_OPERATOR_DSAI_G9B"
    assert qa["blocking_warnings"] == []
    assert qa["unresolved_issues"] == []
    assert qa["unresolved_reviews"] == []


def test_v025_preserves_gate_ready_history_while_live_pointer_may_advance_after_operator_decision():
    state = _load(STATE)
    assert state["programme_status"] == "WP9_G9B_GATE_READY"
    assert state["gate_readiness"]["decision"] == "PENDING_OPERATOR"

    pointer = _load(POINTER)
    assert pointer["programme_id"] == "OVC-DSAI-v0.1"
    assert pointer["schema"] == "ovc-programme-current-state-pointer/v1"
    assert str(pointer["current_state"]).startswith("OVC_DSAI_STATE_v0_")
    assert str(pointer["status"]).strip()
    assert pointer["next_packet"] == "DSAI-WP9"
