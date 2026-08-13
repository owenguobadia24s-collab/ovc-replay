from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
STATE = ROOT / "registries/implementation/c2p_v0_2/OVC_C2P2_STATE_v0_1.json"
POINTER = ROOT / "registries/implementation/c2p_v0_2/CURRENT_STATE_POINTER.json"
RELEASE = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-wp0"


class C2P2WP0MaterialisationTest(unittest.TestCase):
    def test_exact_ratified_plan_and_authority_boundary(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual(state["schema"], "ovc-c2p2-programme-state/v2")
        self.assertEqual(state["programme_id"], "OVC-C2P-PERSISTENT-STRUCTURAL-OBJECTS-CONFORMANCE-v0.2")
        self.assertEqual(state["plan_id"], "OVC-C2P-PERSISTENT-STRUCTURAL-OBJECTS-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-REVISED")
        self.assertEqual(state["plan_version"], "0.2")
        self.assertEqual(state["ratification"]["decision"], "PASS")
        self.assertTrue(state["ratification"]["repository_materialized"])
        self.assertEqual(state["ratification"]["main_integration"], "fdf64e0df76c5f75b21de357bac05ec965b9f0f7")
        self.assertEqual(state["governing_design_sha256"], "ed656705f13162cb5b9ac231d73a32870f7127f4fb464fe3e3a6ebd48a5608cd")
        self.assertEqual(state["authority"]["c2p_runtime"], "NONE")
        self.assertEqual(state["authority"]["empirical_object_pack_selection"], "NONE")
        self.assertEqual(state["authority"]["real_source_replay"], "DENIED_FUTURE_C2P2_RS0")
        self.assertEqual(state["authority"]["validation"], "LOCKED_UNCONSUMED")

    def test_pointer_and_materialisation_evidence_resolve(self) -> None:
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertEqual(pointer["current_state"], "registries/implementation/c2p_v0_2/OVC_C2P2_STATE_v0_1.json")
        for name in (
            "C2P2_GOVERNING_SOURCE_IDENTITIES.json",
            "C2P2_G0_DECISION.json",
            "C2P2_WP0_COURT_RECORD_CENSUS.json",
            "C2P2_WP0_REQUIREMENT_ARTIFACT_CENSUS.json",
            "C2P2_WP0_QA_PACKET.json",
        ):
            self.assertTrue((RELEASE / name).is_file(), name)

    def test_wp1_is_first_implementation_packet(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        by_id = {packet["packet_id"]: packet for packet in state["packet_register"]}
        self.assertEqual(by_id["C2P2-WP0"]["next_packet"], "C2P2-WP1")
        self.assertEqual(by_id["C2P2-WP0"]["status"], "COMPLETED")
        self.assertEqual(by_id["C2P2-WP1"]["status"], "COMPLETED")
        self.assertEqual(by_id["C2P2-WP1"]["authority_required"], "AUTO_EXECUTABLE")
        self.assertEqual(state["next_packet"], by_id[state["packet_id"]]["next_packet"])
        self.assertEqual(state["deferred_follow_ons"], ["C2P2-PS0", "C2P2-RS0", "C2P2-RR0", "C2P2-AG0"])


if __name__ == "__main__":
    unittest.main()
