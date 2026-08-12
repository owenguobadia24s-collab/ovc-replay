from __future__ import annotations

import json
from pathlib import Path

from ovc.development.skills import resolve_orch2_authority

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp9/DSAI_WP9_G9B_SQUASH_MERGE_RECEIPT.json"
AUTHORITY = ROOT / "registries/development/skills/orch2_low_risk_authority_v0_1.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_27.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_merge_receipt_pins_exact_approved_head_base_and_result_main():
    receipt = _load(RECEIPT)
    assert receipt["gate_id"] == "DSAI-G9B"
    assert receipt["operator_decision"] == "PASS_ORCH2"
    assert receipt["pr_number"] == 661
    assert receipt["merge_method"] == "squash"
    assert receipt["target_branch"] == "main"
    assert receipt["base_sha"] == "eed45f432f6661431fc546fc365aa3f043092697"
    assert receipt["approved_head_sha"] == "59cb04d9222f6c143c8e6da2e2b0fb78532f6aa4"
    assert receipt["result_main_sha"] == "8cde4e7744f93cec33e9fb0786f3cf03533957ed"
    assert receipt["result_parent_sha"] == receipt["base_sha"]
    assert receipt["assurance"]["tests"]["run_number"] == 3800
    assert receipt["assurance"]["tests"]["conclusion"] == "success"
    assert receipt["assurance"]["tiered"]["run_number"] == 2159
    assert receipt["assurance"]["tiered"]["conclusion"] == "success"
    assert receipt["assurance"]["unresolved_reviews"] == 0
    assert receipt["assurance"]["unresolved_review_threads"] == 0


def test_authority_is_now_resolvable_only_for_exact_low_risk_class_on_main():
    authority = _load(AUTHORITY)
    active = resolve_orch2_authority(
        authority=authority,
        packet_class="LOW_RISK_IMPLEMENTATION",
        record_present_on_main=True,
    )
    assert active["status"] == "ACTIVE_AUTHORIZED"
    assert active["g9b_orch2_authority"] is True

    undeclared = resolve_orch2_authority(
        authority=authority,
        packet_class="UNDECLARED",
        record_present_on_main=True,
    )
    assert undeclared["status"] == "BLOCK"
    assert undeclared["g9b_orch2_authority"] is False
    assert "PACKET_CLASS_NOT_ENABLED" in undeclared["reason_codes"]


def test_wp9_completed_state_preserves_all_reserved_boundaries():
    state = _load(STATE)
    assert state["programme_status"] == "WP9_COMPLETED_ORCH2_BOUNDED_ACTIVE"
    assert state["packet_updates"]["DSAI-WP9"]["status"] == "COMPLETED"
    assert state["next_packet"] == "DSAI-WP10"
    assert state["orch2_authority"]["authority_record_present_on_main"] is True
    assert state["orch2_authority"]["effective"] is True
    assert state["orch2_authority"]["enabled_packet_classes"] == ["LOW_RISK_IMPLEMENTATION"]
    assert state["orch2_authority"]["concurrency"] == "SERIAL_REQUIRED"
    assert state["authority"]["direct_main_mutation"] is False
    assert state["authority"]["force_push"] is False
    assert state["authority"]["history_rewrite"] is False
    assert state["authority"]["validation"] == "DENIED"
    assert state["authority"]["orch_3"] == "INACTIVE_NOT_AUTHORISED"
    assert state["authority"]["orch_4"] == "INACTIVE_NOT_AUTHORISED"
    assert state["authority"]["orch_5"] == "INACTIVE_NOT_AUTHORISED"
    assert state["mandatory_stop"]["active"] is False


def test_v027_preserves_wp9_completion_while_live_pointer_may_advance_lawfully():
    state = _load(STATE)
    assert state["next_packet"] == "DSAI-WP10"
    pointer = _load(POINTER)
    assert pointer["programme_id"] == "OVC-DSAI-v0.1"
    assert pointer["schema"] == "ovc-programme-current-state-pointer/v1"
    assert str(pointer["current_state"]).startswith("OVC_DSAI_STATE_v0_")
    assert pointer["next_packet"] in {"DSAI-WP10", "DSAI-WP11", None}
    if pointer["next_packet"] is None:
        assert pointer["status"] == "IMPLEMENTED_ORCH2_BOUNDED_PILOTED"
