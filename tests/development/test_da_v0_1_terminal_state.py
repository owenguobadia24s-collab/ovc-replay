from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json"
IMPLEMENTATION = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml"


class DevelopmentAccelerationV01TerminalStateTests(unittest.TestCase):
    def test_programme_state_matches_merged_da_g5_and_da_g6_records(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual(state["programme_status"], "COMPLETED")
        self.assertIsNone(state["current_packet"])
        self.assertIsNone(state["current_gate"])
        self.assertEqual(state["operator_decision_id"], "DA-G6.OPERATOR.PASS.20260802T212200+0100")
        self.assertEqual(state["merge_commit"], "da29bb4b571e8f0c4706fa3032e941a89d0d5550")
        self.assertEqual(state["next_action"], "PROGRAMME_COMPLETED_NO_NEXT_PACKET")
        self.assertEqual(state["completion"]["status"], "COMPLETED")
        self.assertEqual(state["completion"]["blockers"], [])

        packets = {row["packet_id"]: row for row in state["packets"]}
        self.assertEqual(packets["DA-WP5"]["status"], "COMPLETED")
        self.assertEqual(packets["DA-WP5"]["candidate_commit"], "0b2dd8ed479545eb57cca947938c15eb9a9e3054")
        self.assertEqual(packets["DA-WP5"]["merge_commit"], "eaefbf55d1702d689d59765558af65e87c0b37fc")
        self.assertEqual(packets["DA-G6"]["status"], "COMPLETED")
        self.assertEqual(packets["DA-G6"]["candidate_commit"], "0f0bda757e62120f2a570de6b3c000e9786445c5")
        self.assertEqual(packets["DA-G6"]["merge_commit"], "da29bb4b571e8f0c4706fa3032e941a89d0d5550")
        self.assertIsNone(packets["DA-G6"]["next_packet"])

        self.assertEqual(state["authority"]["default_workflow_adoption"], "ACTIVE")
        self.assertEqual(state["authority"]["duplicated_mechanics"], "RETIRED_NON_AUTHORITATIVE_NON_DESTRUCTIVE")
        self.assertEqual(state["authority"]["direct_main_write"], "PROHIBITED")
        self.assertEqual(state["authority"]["validation"], "DENIED")
        self.assertEqual(state["authority"]["execution"], "NONE")

    def test_implementation_registry_is_terminal_and_authority_neutral(self) -> None:
        body = IMPLEMENTATION.read_text(encoding="utf-8")
        required = [
            "programme_status: COMPLETED",
            "operator_decision_id: DA-G6.OPERATOR.PASS.20260802T212200+0100",
            "terminal_merge_commit: da29bb4b571e8f0c4706fa3032e941a89d0d5550",
            "packet_id: DA-WP5",
            "final_head_commit: 0b2dd8ed479545eb57cca947938c15eb9a9e3054",
            "merge_commit: eaefbf55d1702d689d59765558af65e87c0b37fc",
            "packet_id: DA-G6",
            "final_head_commit: 0f0bda757e62120f2a570de6b3c000e9786445c5",
            "activation_pull_request: 222",
            "current_authority: ACTIVE_DEFAULT_WORKFLOW_WITH_NON_DESTRUCTIVE_RETIREMENT",
            "duplicated_mechanics_retirement: RETIRED_NON_AUTHORITATIVE_NON_DESTRUCTIVE",
        ]
        for token in required:
            self.assertIn(token, body)
        self.assertNotIn("status: QA_REVIEW", body)
        self.assertNotIn("blockers: [FINAL_HEAD_CI_PENDING]", body)
        self.assertNotIn("status: PLANNED\n  current_authority: DENIED", body)


if __name__ == "__main__":
    unittest.main()
