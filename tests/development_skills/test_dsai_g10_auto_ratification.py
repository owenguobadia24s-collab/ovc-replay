from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp10/DSAI_WP10_QA_PACKET.json"
DECISION = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp10/DSAI_G10_DECISION.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_28.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_g10_is_delegated_pass_with_none_authority_delta():
    qa = _load(QA)
    decision = _load(DECISION)
    assert qa["qa_decision"] == "PASS"
    assert qa["qa_recommendation"] == "PASS_AUTO_RATIFY_DSAI_G10"
    assert qa["gate_class"] == "AUTO_RATIFIABLE"
    assert qa["authority_delta"] == "NONE"
    assert decision["gate_id"] == "DSAI-G10"
    assert decision["gate_class"] == "AUTO_RATIFIABLE"
    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "DELEGATED_BY_RATIFIED_PLAN_AND_ACTIVE_BOUNDED_ORCH2"
    assert decision["packet_class"] == "LOW_RISK_IMPLEMENTATION"
    assert decision["authority_delta"] == "NONE"
    assert decision["authority_effect"] == "NONE"
    assert all(value == "PASS" or value == "NONE" for value in decision["acceptance_conditions"].values())


def test_g10_state_preserves_console_and_dsai_authority_boundaries():
    state = _load(STATE)
    assert state["programme_status"] == "WP10_G10_AUTO_RATIFIED_PENDING_INTEGRATION"
    wp10 = state["packet_updates"]["DSAI-WP10"]
    assert wp10["status"] == "APPROVED_PENDING_INTEGRATION"
    assert wp10["packet_class"] == "LOW_RISK_IMPLEMENTATION"
    assert wp10["authority_delta"] == "NONE"
    assert wp10["decision"] == "PASS_DELEGATED"
    assert state["rcn_projection"]["mode"] == "FIXTURE_ONLY_LOCAL_READ_ONLY"
    assert state["rcn_projection"]["allowed_methods"] == ["GET"]
    assert state["rcn_projection"]["real_source_routes"] == "DENIED_UNTIL_RCN_RN_G4"
    assert state["rcn_projection"]["governance_write_surface"] is False
    authority = state["authority"]
    assert authority["orch_2"] == "ACTIVE_BOUNDED_SINGLE_PACKET"
    assert authority["orch_2_enabled_packet_classes"] == ["LOW_RISK_IMPLEMENTATION"]
    assert authority["direct_main_mutation"] is False
    assert authority["force_push"] is False
    assert authority["history_rewrite"] is False
    assert authority["validation"] == "DENIED"
    assert authority["orch_3"] == "INACTIVE_NOT_AUTHORISED"
    assert authority["orch_4"] == "INACTIVE_NOT_AUTHORISED"
    assert authority["orch_5"] == "INACTIVE_NOT_AUTHORISED"
    assert state["mandatory_stop"]["active"] is False


def test_live_pointer_waits_for_wp10_integration_before_wp11():
    pointer = _load(POINTER)
    assert pointer == {
        "current_state": "OVC_DSAI_STATE_v0_28.json",
        "next_packet": "DSAI-WP10",
        "programme_id": "OVC-DSAI-v0.1",
        "schema": "ovc-programme-current-state-pointer/v1",
        "status": "WP10_G10_AUTO_RATIFIED_PENDING_INTEGRATION",
    }
