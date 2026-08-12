from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp10/DSAI_WP10_G10_SQUASH_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_29.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_g10_merge_receipt_pins_exact_auto_ratified_integration():
    receipt = _load(RECEIPT)
    assert receipt["gate_id"] == "DSAI-G10"
    assert receipt["gate_decision"] == "PASS_DELEGATED_AUTO_RATIFIED"
    assert receipt["packet_class"] == "LOW_RISK_IMPLEMENTATION"
    assert receipt["authority_delta"] == "NONE"
    assert receipt["pr_number"] == 673
    assert receipt["merge_method"] == "squash"
    assert receipt["base_sha"] == "28ea2620af36a77704782274830a0e87892a960f"
    assert receipt["approved_head_sha"] == "0c9b3df64f34ce56c7b8ef5899c316f7852c6623"
    assert receipt["result_main_sha"] == "5c8c0c78489c8f820bd8500015bff17397743ab5"
    assert receipt["result_parent_sha"] == receipt["base_sha"]
    assert receipt["assurance"]["final_tests"]["run_number"] == 3819
    assert receipt["assurance"]["final_tiered"]["run_number"] == 2175
    assert receipt["assurance"]["final_tiered"]["merge_readiness"] == "success"


def test_wp10_completed_state_advances_only_to_wp11_without_authority_change():
    state = _load(STATE)
    assert state["programme_status"] == "WP10_COMPLETED_G10_PASS"
    assert state["packet_updates"]["DSAI-WP10"]["status"] == "COMPLETED"
    assert state["packet_updates"]["DSAI-WP10"]["authority_delta"] == "NONE"
    assert state["next_packet"] == "DSAI-WP11"
    assert state["rcn_projection"]["mode"] == "FIXTURE_ONLY_LOCAL_READ_ONLY"
    assert state["rcn_projection"]["allowed_methods"] == ["GET"]
    assert state["rcn_projection"]["real_source_routes"] == "DENIED_UNTIL_RCN_RN_G4"
    assert state["authority"]["orch_2"] == "ACTIVE_BOUNDED_SINGLE_PACKET"
    assert state["authority"]["orch_3"] == "INACTIVE_NOT_AUTHORISED"
    assert state["authority"]["orch_4"] == "INACTIVE_NOT_AUTHORISED"
    assert state["authority"]["orch_5"] == "INACTIVE_NOT_AUTHORISED"
    assert state["authority"]["validation"] == "DENIED"
    assert state["mandatory_stop"]["active"] is False


def test_pointer_advances_to_wp11():
    assert _load(POINTER) == {
        "current_state": "OVC_DSAI_STATE_v0_29.json",
        "next_packet": "DSAI-WP11",
        "programme_id": "OVC-DSAI-v0.1",
        "schema": "ovc-programme-current-state-pointer/v1",
        "status": "WP10_COMPLETED_G10_PASS",
    }
