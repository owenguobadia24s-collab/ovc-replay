import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class TestDSAI2WP4TerminalCloseout(unittest.TestCase):
    def _load(self, relative: str):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_terminal_receipt_and_state_are_exact(self):
        receipt = self._load(
            "docs/releases/development-skills-architecture-v0-2/dsai2-wp4/"
            "DSAI2_WP4_G4_TERMINAL_SQUASH_MERGE_RECEIPT.json"
        )
        state = self._load(
            "registries/implementation/dsai_v0_2/OVC_DSAI_V0_2_STATE_v0_7.json"
        )
        pointer = self._load(
            "registries/implementation/dsai_v0_2/CURRENT_STATE_POINTER.json"
        )
        authority = self._load(
            "registries/development/skills/orch345_bounded_authority_v0_1.json"
        )

        expected_main = "8ce1eb5bb3749074b1d5c40f7ce11f974b6c2d30"
        self.assertEqual(receipt["pull_request"], 693)
        self.assertEqual(receipt["result_main"], expected_main)
        self.assertEqual(receipt["gate_decision"], "PASS_DELEGATED_AUTO_RATIFIED")
        self.assertEqual(receipt["authority_delta"], "NONE")
        self.assertEqual(receipt["pilot_acceptance"]["false_parallel_allows"], 0)
        self.assertEqual(receipt["pilot_acceptance"]["parallel_merges"], 0)
        self.assertFalse(receipt["pilot_acceptance"]["reserved_authority_crossed"])

        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["merge_commit"], expected_main)
        self.assertEqual(state["next_packet"], None)
        self.assertEqual(len(state["completed_packets"]), 5)
        self.assertTrue(state["terminal"]["programme_complete"])
        self.assertFalse(state["terminal"]["final_merge_receipt_pending"])
        self.assertTrue(state["terminal"]["future_authority_expansion_requires_operator"])

        self.assertEqual(pointer["current_state"], "OVC_DSAI_V0_2_STATE_v0_7.json")
        self.assertEqual(pointer["status"], "COMPLETED")
        self.assertIsNone(pointer["next_packet"])

        self.assertTrue(authority["approved"])
        self.assertTrue(authority["effective"])
        self.assertEqual(authority["enabled_packet_classes"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertEqual(authority["enabled_orchestrators"], ["ORCH-3", "ORCH-4", "ORCH-5"])
        self.assertFalse(authority["integration_policy"]["parallel_merge"])
        self.assertTrue(authority["integration_policy"]["serialized_final_integration_window"])
        self.assertFalse(authority["integration_policy"]["force_push"])
        self.assertFalse(authority["integration_policy"]["history_rewrite"])
        self.assertEqual(authority["validation"], "DENIED")
        self.assertEqual(authority["reserved_scientific_execution_authority"], "NONE")

    def test_administrative_noop_pr_did_not_become_authority(self):
        receipt = self._load(
            "docs/releases/development-skills-architecture-v0-2/dsai2-wp4/"
            "DSAI2_WP4_G4_TERMINAL_SQUASH_MERGE_RECEIPT.json"
        )
        events = receipt["administrative_events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["pull_request"], 694)
        self.assertEqual(events[0]["disposition"], "CLOSED_UNMERGED_IMMEDIATELY")


if __name__ == "__main__":
    unittest.main()
