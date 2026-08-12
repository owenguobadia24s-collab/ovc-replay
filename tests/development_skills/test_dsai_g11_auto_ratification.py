from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp11/DSAI_WP11_QA_PACKET.json"
DECISION = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp11/DSAI_G11_DECISION.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_30.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_g11_auto_ratifies_none_delta_terminal_review_only():
    qa = _load(QA)
    decision = _load(DECISION)
    assert qa["qa_decision"] == "PASS"
    assert qa["qa_recommendation"] == "PASS_AUTO_RATIFY_DSAI_G11"
    assert qa["gate_class"] == "AUTO_RATIFIABLE"
    assert qa["authority_delta"] == "NONE"
    assert qa["unresolved_s3_s4"] == 0
    assert qa["blocking_warnings"] == []
    assert decision["gate_id"] == "DSAI-G11"
    assert decision["gate_class"] == "AUTO_RATIFIABLE"
    assert decision["decision"] == "PASS"
    assert decision["packet_class"] == "LOW_RISK_IMPLEMENTATION"
    assert decision["authority_delta"] == "NONE"
    assert decision["authority_effect"] == "NONE"
    assert decision["terminal_state"] == "IMPLEMENTED_ORCH2_BOUNDED_PILOTED"


def test_terminal_state_keeps_orch2_serial_and_defers_all_parallel_authority():
    state = _load(STATE)
    assert state["programme_status"] == "IMPLEMENTED_ORCH2_BOUNDED_PILOTED"
    assert state["next_packet"] is None
    assert state["packet_updates"]["DSAI-WP11"]["decision"] == "PASS_DELEGATED"
    assert state["packet_updates"]["DSAI-WP11"]["authority_delta"] == "NONE"
    assert state["post_pilot_findings"]["recorded_unresolved_s3_s4"] == 0
    assert state["post_pilot_findings"]["parallel_orch2_packet_denominator"] == 0
    assert state["readiness"]["orch3"] == "DEFER_NOT_READY"
    assert state["readiness"]["orch4"] == "DEFER_NOT_READY"
    assert state["readiness"]["parallelism"] == "DEFER_NOT_READY_KEEP_SERIAL_REQUIRED"
    authority = state["authority"]
    assert authority["orch_2"] == "ACTIVE_BOUNDED_SINGLE_PACKET"
    assert authority["orch_2_enabled_packet_classes"] == ["LOW_RISK_IMPLEMENTATION"]
    assert authority["orch_2_concurrency"] == "SERIAL_REQUIRED"
    assert authority["orch_3"] == "INACTIVE_NOT_AUTHORISED"
    assert authority["orch_4"] == "INACTIVE_NOT_AUTHORISED"
    assert authority["orch_5"] == "INACTIVE_NOT_AUTHORISED"
    assert authority["direct_main_mutation"] is False
    assert authority["force_push"] is False
    assert authority["history_rewrite"] is False
    assert authority["validation"] == "DENIED"
    assert state["blocking_warnings"] == []
    assert state["blockers"] == []
    assert state["mandatory_stop"]["active"] is False


def test_terminal_pointer_has_no_next_packet_and_preserves_programme_identity():
    pointer = _load(POINTER)
    assert pointer == {
        "current_state": "OVC_DSAI_STATE_v0_30.json",
        "next_packet": None,
        "programme_id": "OVC-DSAI-v0.1",
        "schema": "ovc-programme-current-state-pointer/v1",
        "status": "IMPLEMENTED_ORCH2_BOUNDED_PILOTED",
    }
