from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp11/DSAI_WP11_G11_TERMINAL_SQUASH_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_31.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"


class DSAIWP11TerminalCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))
        cls.pointer = json.loads(POINTER.read_text(encoding="utf-8"))

    def test_terminal_receipt_pins_exact_g11_squash_and_assurance(self):
        receipt = self.receipt
        self.assertEqual(receipt["gate_id"], "DSAI-G11")
        self.assertEqual(receipt["gate_decision"], "PASS_DELEGATED_AUTO_RATIFIED")
        self.assertEqual(receipt["packet_class"], "LOW_RISK_IMPLEMENTATION")
        self.assertEqual(receipt["authority_delta"], "NONE")
        self.assertEqual(receipt["pr_number"], 677)
        self.assertEqual(receipt["merge_method"], "squash")
        self.assertEqual(receipt["target_branch"], "main")
        self.assertEqual(receipt["base_sha"], "10a0acac129df1039feafd9200612e7512a6c551")
        self.assertEqual(receipt["approved_head_sha"], "c909ff71160e39ddc7163855c01f1c95b2ad5343")
        self.assertEqual(receipt["result_main_sha"], "bd5218b47c1ebc028f1455a4f4f3ef86bded34a7")
        self.assertEqual(receipt["result_parent_sha"], receipt["base_sha"])
        self.assertEqual(receipt["assurance"]["final_tests"]["run_number"], 3873)
        self.assertEqual(receipt["assurance"]["final_tests"]["conclusion"], "success")
        self.assertEqual(receipt["assurance"]["final_tiered"]["run_number"], 2225)
        self.assertEqual(receipt["assurance"]["final_tiered"]["conclusion"], "success")
        self.assertEqual(receipt["assurance"]["final_tiered"]["jobs"]["OVC merge readiness"], "success")
        self.assertEqual(receipt["assurance"]["unresolved_reviews"], 0)
        self.assertEqual(receipt["assurance"]["unresolved_review_threads"], 0)

    def test_remediation_was_fail_closed_and_never_weakened_authority(self):
        remediation = self.receipt["terminal_assurance_remediation"]
        self.assertEqual(remediation["initial_failure_reason"], "OVC_BASE_MOVED_BEFORE_READINESS")
        self.assertEqual(remediation["reconciliation_pr"], 680)
        self.assertFalse(remediation["test_weakening"])
        self.assertFalse(remediation["force_push"])
        self.assertFalse(remediation["history_rewrite"])
        authority = self.receipt["authority"]
        self.assertEqual(authority["orch_2"], "ACTIVE_BOUNDED_SINGLE_PACKET")
        self.assertEqual(authority["enabled_packet_classes"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertEqual(authority["concurrency"], "SERIAL_REQUIRED")
        self.assertFalse(authority["direct_main_mutation"])
        self.assertEqual(authority["orch_3"], "INACTIVE_NOT_AUTHORISED")
        self.assertEqual(authority["orch_4"], "INACTIVE_NOT_AUTHORISED")
        self.assertEqual(authority["orch_5"], "INACTIVE_NOT_AUTHORISED")
        self.assertEqual(authority["validation"], "DENIED")

    def test_terminal_state_completes_wp11_and_has_no_next_packet(self):
        state = self.state
        self.assertEqual(state["programme_status"], "IMPLEMENTED_ORCH2_BOUNDED_PILOTED")
        self.assertEqual(state["packet_updates"]["DSAI-WP11"]["status"], "COMPLETED")
        self.assertEqual(state["packet_updates"]["DSAI-WP11"]["authority_delta"], "NONE")
        self.assertEqual(state["packet_updates"]["DSAI-WP11"]["merge_commit"], "bd5218b47c1ebc028f1455a4f4f3ef86bded34a7")
        self.assertIsNone(state["next_packet"])
        self.assertFalse(state["terminal"]["final_merge_receipt_pending"])
        self.assertEqual(state["terminal"]["result_main_sha"], "bd5218b47c1ebc028f1455a4f4f3ef86bded34a7")
        self.assertTrue(state["terminal"]["future_authority_expansion_requires_separate_operator_approval"])
        self.assertEqual(state["blockers"], [])
        self.assertEqual(state["blocking_warnings"], [])

    def test_terminal_pointer_is_exact_forward_only_closeout_state(self):
        self.assertEqual(
            self.pointer,
            {
                "current_state": "OVC_DSAI_STATE_v0_31.json",
                "next_packet": None,
                "programme_id": "OVC-DSAI-v0.1",
                "schema": "ovc-programme-current-state-pointer/v1",
                "status": "IMPLEMENTED_ORCH2_BOUNDED_PILOTED",
            },
        )


if __name__ == "__main__":
    unittest.main()
