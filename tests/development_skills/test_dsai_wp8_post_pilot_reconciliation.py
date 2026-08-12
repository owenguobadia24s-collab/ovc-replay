import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_post_pilot_reconciliation_advances_to_wp9_without_merge_authority():
    pointer = _load("registries/implementation/dsai/CURRENT_STATE_POINTER.json")
    state = _load("registries/implementation/dsai/OVC_DSAI_STATE_v0_21.json")
    receipt = _load(
        "docs/releases/development-skills-architecture-v0-1/dsai-wp8/"
        "DSAI_WP8_ORCH1_POST_PILOT_RECONCILIATION.json"
    )

    assert pointer["current_state"] == "OVC_DSAI_STATE_v0_21.json"
    assert pointer["next_packet"] == "DSAI-WP9"
    assert state["supersedes_state"] == "OVC_DSAI_STATE_v0_20.json"
    assert state["current_packet"] == "DSAI-WP9"
    assert state["packet_updates"]["DSAI-WP8"]["status"] == "COMPLETED_POST_PILOT"
    assert state["packet_updates"]["DSAI-WP8"]["pilot_status"] == "PASS_CLEAN_FINAL_HEAD"
    assert state["wp9_readiness"]["status"] == "READY_FOR_PRE_GATE_MERGE_CAPABILITY_QUALIFICATION"
    assert "ORCH1_PILOT_EVIDENCE_REQUIRED" not in state["wp9_readiness"]["blockers"]
    assert "GIT_MERGE_CAPABILITY_G9A_NOT_YET_TRUSTED" in state["wp9_readiness"]["blockers"]

    assert receipt["pilot"]["pull_request"] == 637
    assert receipt["pilot"]["head_sha"] == "b87eaeb54a85f6663b5c567985cfdf023b998189"
    assert receipt["pilot"]["integration_main_sha"] == "2eff94425606df77eb037a717de662e5c7b7c47b"
    assert receipt["final_head_assurance"]["disposition"] == "PASS_CLEAN_FINAL_HEAD"
    assert all(check["conclusion"] == "success" for check in receipt["final_head_assurance"]["checks"])

    authority = state["authority"]
    assert authority["direct_main_mutation"] is False
    assert authority["automatic_merge"] is False
    assert authority["merge_authority"] == "NONE"
    assert authority["orch_2"] == "INACTIVE_PENDING_DSAI_G9B"
    assert state["git_packet_manager"]["merge_capability"] == "DISABLED_UNTRUSTED"
    assert state["mandatory_stop"]["next_reserved_gate"] == "DSAI-G9A"
