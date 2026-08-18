from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RELEASE = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-iad"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_iad_plan_and_run_receipt_are_bound() -> None:
    plan = ROOT / "docs/plans/c2p2-identity-anchor-discrimination-v0-1/OVC_C2P2_IDENTITY_ANCHOR_DISCRIMINATION_PLAN_v0_1.md"
    text = plan.read_text(encoding="utf-8")
    assert "OVC-C2P2-IDENTITY-ANCHOR-DISCRIMINATION-PLAN-v0.1" in text
    assert "C2P2-IAD-GOWNER" in text
    assert "C2P2-IAD-GREAL" in text
    start = load(RELEASE / "C2P2_IAD_EXECUTION_START_RECEIPT_v0_1.json")
    assert start["operator_instruction"] == "OVC RUN C2P2-IAD"
    assert start["plan_ratification_commit"] == "668cfea5a8ea725df022b8c3757b4290d02597fe"
    assert start["fresh_real_source_execution"] is False


def test_wp0_freezes_exact_candidate_generation_and_denials() -> None:
    wp0 = load(RELEASE / "C2P2_IAD_WP0_CURRENTNESS_AND_AUTHORITY_v0_1.json")
    generation = wp0["candidate_generation"]
    assert generation["generation_id"] == "C2P2-PS0-EMPIRICAL-RUNTIME-GENERATION-v3"
    assert generation["generation_logical_sha256"] == "c7f0160f7bb8d75b92d4aa95116895c25c44c987e2e78a8352c0e491244bbf1a"
    assert generation["candidate_hashes"] == {
        "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3": "a8cb003521c62129044a4d62cb9a4d5a967cd3ef9d933fb1090ac4dad0843102",
        "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v3": "a91f50c12438c4d5263d36b48e40acc0a5e146b474307721a4108ac2398a752e",
        "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v3": "29f8ac9a5844b425901fda90299f911a48a85422a390771753ffd5b894b1c52c",
    }
    firewall = wp0["authority_firewall"]
    assert firewall["fresh_real_source_execution"] == "FORBIDDEN_UNTIL_C2P2_IAD_GREAL_PASS"
    assert firewall["material_owner_contract_change"] == "FORBIDDEN_UNTIL_C2P2_IAD_GOWNER_PASS_IF_REQUIRED"
    assert firewall["objectpack_selection"] == "NONE"
    assert wp0["real_source_read"] is False
    assert wp0["real_source_execution"] is False


def test_wp0_completion_receipt_preserves_non_authoritative_no_vit_state() -> None:
    receipt = load(RELEASE / "C2P2_IAD_WP0_COMPLETION_RECEIPT_v0_1.json")
    assert receipt["packet_id"] == "C2P2-IAD-WP0"
    assert receipt["status"] == "COMPLETED"
    assert receipt["candidate_commit"] == "d0fe7a7f1c0fd9ee60f7f2a7b455e886990ede4f"
    assert receipt["qa"]["recommendation"] == "PASS"
    assert receipt["qa"]["tested_head_sha"] == receipt["candidate_commit"]
    state = receipt["state_at_completion"]
    assert state["real_source_authority"] == "NONE_PENDING_C2P2_IAD_GREAL"
    assert state["active_object_pack_id"] is None
    assert state["c2p_activation"] == "NONE"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["main_merge"] == "NONE"
    assert state["no_vit"] is True
