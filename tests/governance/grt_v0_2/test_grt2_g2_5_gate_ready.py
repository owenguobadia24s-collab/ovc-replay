from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATES = ROOT / "docs/programmes/grt-v0-2/gates"
STATE = ROOT / "registries/implementation/grt_v0_2"
AUTHORITY = ROOT / "registries/authority"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g2_5_gate_preparation_remains_historical_after_operator_pass() -> None:
    gate = _load(GATES / "GRT2_G2_5_GATE_PACKET.json")
    qa = _load(GATES / "GRT2_G2_5_QA_PACKET.json")
    historical_state = _load(STATE / "OVC_GRT2_STATE_v0_9.json")
    pilot_state = _load(STATE / "OVC_GRT2_STATE_v0_10.json")
    threshold_state = _load(STATE / "OVC_GRT2_STATE_v0_11.json")
    blocker_state = _load(STATE / "OVC_GRT2_STATE_v0_12.json")
    correction_running_state = _load(STATE / "OVC_GRT2_STATE_v0_13.json")
    current_state = _load(STATE / "OVC_GRT2_STATE_v0_14.json")
    pointer = _load(STATE / "CURRENT_STATE_POINTER.json")
    decision = _load(GATES / "GRT2_G2_5_OPERATOR_DECISION.json")
    authority = _load(AUTHORITY / "GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_1.json")

    assert gate["gate_id"] == "GRT2-G2.5"
    assert gate["recommended_decision"] == "PASS"
    assert gate["operator_decision"] == "PASS"
    assert gate["operator_decision_record"] == "docs/programmes/grt-v0-2/gates/GRT2_G2_5_OPERATOR_DECISION.json"
    assert gate["authority_consumed"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT_ONLY"
    assert gate["pilot_evidence_threshold"]["minimum_elapsed_hours"] == 24
    assert gate["pilot_evidence_threshold"]["minimum_eligible_candidate_evaluations"] == 8
    assert gate["pilot_evidence_threshold"]["normal_real_ordinary_candidate_target"] == 4
    assert gate["g3_readiness_monitoring"]["pilot_escapes_required"] == 0
    assert gate["g3_readiness_monitoring"]["blocking_false_positives_required"] == 0
    assert gate["g3_readiness_monitoring"]["unresolved_false_negatives_required"] == 0
    assert gate["g3_readiness_monitoring"]["scope_leakage_required"] == 0
    assert qa["qa_recommendation"] == "PASS"
    assert qa["authority_delta_from_this_qa"] == "NONE"
    assert historical_state["status"] == "GATE_READY"
    assert historical_state["g2_5_status"] == "GATE_READY_OPERATOR_REQUIRED"
    assert historical_state["active_enforcement"] == "NONE"
    assert historical_state["debt_floor_generation"] is None
    assert decision["decision"] == "PASS"
    assert decision["approved_authority_delta"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT_ONLY"
    assert authority["enforcement_mode"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert authority["g3_status"] == "NOT_AUTHORISED"
    assert authority["debt_floor_generation"] is None
    assert pilot_state["g2_5_status"] == "APPROVED_OPERATOR_PASS_PILOT_ACTIVE"
    assert pilot_state["active_enforcement"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert pilot_state["constitution_status"] == "PROPOSED_UNADMITTED"
    assert pilot_state["debt_floor_generation"] is None

    assert threshold_state["pilot_observation_threshold_met"] is True
    assert threshold_state["pilot_eligible_candidate_count"] == 8
    assert threshold_state["g3_status"] == "NOT_AUTHORISED_READINESS_EVIDENCE_INCOMPLETE"
    assert threshold_state["active_enforcement"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert threshold_state["constitution_status"] == "PROPOSED_UNADMITTED"
    assert threshold_state["debt_floor_generation"] is None
    assert blocker_state["status"] == "BLOCKED"
    assert blocker_state["blockers"] == ["GRT2_G3_FULL_ENFORCEMENT_REPLAY_SURFACE_NOT_MATERIALIZED"]
    assert blocker_state["debt_floor_generation"] is None

    assert correction_running_state["status"] == "RUNNING"
    assert correction_running_state["g3_status"] == "NOT_AUTHORISED_CORRECTIVE_IMPLEMENTATION_RUNNING"
    assert correction_running_state["active_enforcement"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert correction_running_state["constitution_status"] == "PROPOSED_UNADMITTED"
    assert correction_running_state["debt_floor_generation"] is None

    assert pointer["current_state"].endswith("OVC_GRT2_STATE_v0_14.json")
    assert pointer["status"] == "APPROVED"
    assert pointer["packet_id"] == "GRT2-G3-FULL-ENFORCEMENT-REPLAY-SURFACE-CORRECTION"
    assert pointer["gate_id"] == "GRT2-G2-SUPERSEDING-QUALIFICATION"
    assert pointer["next_packet"] == "GRT2-G3-READINESS-EVIDENCE"
    assert current_state["status"] == "APPROVED"
    assert current_state["g2_status"] == "APPROVED_DELEGATED_PASS_SUPERSEDING_IMPLEMENTATION_QUALIFICATION"
    assert current_state["g3_status"] == "NOT_AUTHORISED_READINESS_EVIDENCE_NEXT"
    assert current_state["active_enforcement"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert current_state["constitution_status"] == "PROPOSED_UNADMITTED"
    assert current_state["debt_floor_generation"] is None
    assert current_state["authority_delta"] == "NONE_CORRECTIVE_IMPLEMENTATION_ONLY"


def test_g2_5_monitoring_preserves_limited_scope_and_g3_separation() -> None:
    monitor = _load(GATES / "GRT2_G2_5_PILOT_MONITORING_PLAN.json")
    ledger = _load(GATES / "GRT2_G2_5_PILOT_LEDGER.json")
    receipt = _load(GATES / "GRT2_G2_5_THRESHOLD_RECEIPT.json")
    assert monitor["pilot_authority"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT_ACTIVE"
    assert "FINDING_CAUSED_SOLELY_BY_MODIFICATION_OF_PRE_EXISTING_ARTIFACT_UNLESS_INDEPENDENT_PRE_EXISTING_ASSURANCE_ALREADY_BLOCKS" in monitor["shadow_only_scope"]
    assert monitor["historical_dry_run"]["required_before_g3"] is True
    assert monitor["historical_dry_run"]["ordinary_historical_candidate_target"] == 10
    assert monitor["threshold"]["ordinary_and_injection_counts_separate"] is True
    assert monitor["status"] == "ACTIVE_COLLECTING_EVIDENCE"
    assert monitor["eligible_candidate_evaluations"] == 0
    assert ledger["eligible_candidate_count"] == 8
    assert ledger["real_candidate_count"] == 8
    assert ledger["threshold_met"] is True
    assert ledger["g3_ready"] is False
    assert ledger["full_g3_shadow_complete"] is False
    assert receipt["disposition"] == "PASS_G2_5_OBSERVATION_THRESHOLD_ONLY"
    assert receipt["g3_status"] == "NOT_AUTHORISED"
    assert receipt["authority_delta"] == "NONE"
