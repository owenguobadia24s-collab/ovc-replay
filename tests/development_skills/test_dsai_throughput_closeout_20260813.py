from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/releases/development-skills-architecture-throughput-20260813"
STATE_ROOT = ROOT / "registries/implementation/dsai_throughput_20260813"
CAPACITY = ROOT / "registries/development/skills/orch345_operational_capacity_v0_2.json"


class DSAIThroughputCloseoutTests(unittest.TestCase):
    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_merge_receipt_is_exact_and_non_authorising(self) -> None:
        receipt = self._load(RELEASE / "DSAI_TE_G1_SQUASH_MERGE_RECEIPT.json")
        self.assertEqual(receipt["pull_request"], 697)
        self.assertEqual(receipt["approved_head"], "f75694466ce99b50de8b6255579342d8f6a2bd84")
        self.assertEqual(receipt["result_main"], "80c940e764c90b285d0043030e218fc18532776e")
        self.assertEqual(receipt["gate_decision"], "PASS_DELEGATED_AUTO_RATIFIED")
        self.assertEqual(receipt["authority_delta"], "NONE")
        self.assertEqual(receipt["operational_capacity"]["max_parallel_builds"], 4)
        self.assertEqual(receipt["operational_capacity"]["max_train_packets"], 8)
        self.assertEqual(receipt["operational_capacity"]["max_auto_requeue_attempts"], 2)
        self.assertFalse(receipt["boundaries_preserved"]["parallel_merge"])
        self.assertTrue(receipt["boundaries_preserved"]["serialized_final_integration_window"])
        self.assertEqual(receipt["governance_broadening"], "DEFERRED_TO_END_OF_DAY_OPERATOR_ASSESSMENT")

    def test_terminal_state_keeps_eod_governance_assessment_operator_required(self) -> None:
        state = self._load(STATE_ROOT / "OVC_DSAI_THROUGHPUT_STATE_v0_3.json")
        pointer = self._load(STATE_ROOT / "CURRENT_STATE_POINTER.json")
        capacity = self._load(CAPACITY)

        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["authority_delta"], "NONE")
        self.assertEqual(state["merge_commit"], "80c940e764c90b285d0043030e218fc18532776e")
        self.assertIsNone(state["next_packet"])
        self.assertTrue(state["terminal"]["programme_complete"])
        self.assertTrue(state["terminal"]["throughput_profile_active_on_main"])
        self.assertTrue(state["terminal"]["eod_assessment_pending"])
        self.assertTrue(state["terminal"]["future_governance_broadening_requires_operator"])
        self.assertEqual(pointer["current_state"], "OVC_DSAI_THROUGHPUT_STATE_v0_3.json")
        self.assertEqual(pointer["status"], "COMPLETED")
        self.assertIsNone(pointer["next_packet"])

        self.assertTrue(capacity["effective"])
        self.assertEqual(capacity["authority_delta"], "NONE")
        self.assertEqual(capacity["packet_class_allowlist"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertFalse(capacity["integration_policy"]["parallel_merge"])
        self.assertEqual(capacity["operator_required_gate_behavior"], "STOP")
        self.assertEqual(capacity["non_none_authority_delta_behavior"], "STOP")
        self.assertEqual(capacity["validation"], "DENIED")
        self.assertEqual(capacity["reserved_scientific_execution_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
