from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "docs/releases/parallel-development-v0-1/pdc-terminal/PDC_TERMINAL_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/parallel_development/OVC_PDC_STATE_v0_1.json"


class PDCTerminalReceiptTests(unittest.TestCase):
    def setUp(self):
        self.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_terminal_receipt_binds_primary_squash_merge(self):
        self.assertEqual(self.receipt["programme_id"], "OVC-PARALLEL-DEVELOPMENT-HEAD-CHURN-v0.1")
        self.assertEqual(self.receipt["primary_pr"], 534)
        self.assertEqual(self.receipt["final_reconciled_pr_head"], "7666151a1598689e661efbc9b2a31cdc3b9dd100")
        self.assertEqual(self.receipt["squash_merge_commit"], "1acbcf6010950c4f1f436a35c0e0e9fa98b883c1")
        self.assertEqual(self.receipt["terminal_classification"], "PARALLEL_BUILD_SERIALIZED_INTEGRATION_ACTIVE")

    def test_final_assurance_is_complete(self):
        assurance = self.receipt["final_assurance"]
        self.assertEqual(assurance["complete_repository_suite_run"], 31335716434)
        self.assertEqual(assurance["complete_repository_suite"], "PASS")
        self.assertEqual(assurance["ovc_tiered_run"], 31335716459)
        self.assertEqual(assurance["ovc_merge_readiness"], "PASS")
        self.assertEqual(assurance["unresolved_review_threads"], 0)

    def test_programme_state_is_terminal_and_consistent(self):
        self.assertEqual(self.state["status"], "COMPLETED")
        self.assertEqual(self.state["merge_commit"], self.receipt["squash_merge_commit"])
        self.assertEqual(self.state["candidate_commit"], self.receipt["final_reconciled_pr_head"])
        self.assertIsNone(self.state["next_packet"])
        self.assertEqual(
            self.state["terminal_receipt"],
            "docs/releases/parallel-development-v0-1/pdc-terminal/PDC_TERMINAL_MERGE_RECEIPT.json",
        )

    def test_terminal_packet_grants_no_reserved_authority(self):
        self.assertFalse(self.receipt["reserved_authority_consumed"])
        self.assertEqual(self.receipt["authority_delta"], "DEVELOPMENT_ORCHESTRATION_ONLY")
        self.assertIn("selector_or_pack_activation", self.receipt["explicit_non_authority"])
        self.assertIn("probability_risk_exposure_execution", self.receipt["explicit_non_authority"])


if __name__ == "__main__":
    unittest.main()
