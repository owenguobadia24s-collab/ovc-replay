from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GATES = ROOT / "docs/programmes/grt-v0-2/gates"
STATE = ROOT / "registries/implementation/grt_v0_2"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g2_5_gate_is_prepared_without_consuming_operator_authority() -> None:
    gate = _load(GATES / "GRT2_G2_5_GATE_PACKET.json")
    qa = _load(GATES / "GRT2_G2_5_QA_PACKET.json")
    state = _load(STATE / "OVC_GRT2_STATE_v0_9.json")
    pointer = _load(STATE / "CURRENT_STATE_POINTER.json")

    assert gate["gate_id"] == "GRT2-G2.5"
    assert gate["recommended_decision"] == "PASS"
    assert gate["operator_decision"] is None
    assert gate["authority_consumed_by_preparation"] == "NONE"
    assert gate["proposed_authority_delta"]["type"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert gate["pilot_evidence_threshold"]["minimum_elapsed_hours"] == 24
    assert gate["pilot_evidence_threshold"]["minimum_eligible_candidate_evaluations"] == 8
    assert gate["pilot_evidence_threshold"]["normal_real_ordinary_candidate_target"] == 4
    assert gate["g3_readiness_monitoring"]["pilot_escapes_required"] == 0
    assert gate["g3_readiness_monitoring"]["blocking_false_positives_required"] == 0
    assert gate["g3_readiness_monitoring"]["unresolved_false_negatives_required"] == 0
    assert gate["g3_readiness_monitoring"]["scope_leakage_required"] == 0

    assert qa["qa_recommendation"] == "PASS"
    assert qa["authority_delta_from_this_qa"] == "NONE"
    assert state["status"] == "GATE_READY"
    assert state["g2_5_status"] == "GATE_READY_OPERATOR_REQUIRED"
    assert state["active_enforcement"] == "NONE"
    assert state["debt_floor_generation"] is None
    assert pointer["current_state"].endswith("OVC_GRT2_STATE_v0_9.json")
    assert pointer["status"] == "GATE_READY"
    assert pointer["gate_id"] == "GRT2-G2.5"


def test_g2_5_monitoring_preserves_limited_scope_and_g3_separation() -> None:
    monitor = _load(GATES / "GRT2_G2_5_PILOT_MONITORING_PLAN.json")
    assert monitor["pilot_authority"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT_ONLY_AFTER_OPERATOR_PASS"
    assert "FINDING_CAUSED_SOLELY_BY_MODIFICATION_OF_PRE_EXISTING_ARTIFACT_UNLESS_INDEPENDENT_PRE_EXISTING_ASSURANCE_ALREADY_BLOCKS" in monitor["shadow_only_scope"]
    assert monitor["historical_dry_run"]["required_before_g3"] is True
    assert monitor["historical_dry_run"]["ordinary_historical_candidate_target"] == 10
    assert monitor["threshold"]["ordinary_and_injection_counts_separate"] is True
    assert monitor["status"] == "PREPARED_AWAITING_OPERATOR_G2_5_PASS"
