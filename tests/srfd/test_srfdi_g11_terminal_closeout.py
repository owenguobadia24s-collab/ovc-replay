from __future__ import annotations

import json
from pathlib import Path
import unittest

from srfd._current_pointer_compat import assert_lawful_v10_pointer

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp11"
DECISION = BASE / "SRFDI_G11_OPERATOR_DECISION_PASS.json"
RECEIPT = BASE / "SRFDI_G11_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_55_G11_COMPLETED.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
MERGE = "ee313d5324d724ef82584ba9fe6452770201a7a1"
RUN = "SRFD.RUN.55601cfe14d85173c767315be04c8b6c333dc8c07103a8064733086c26606dbf"


class SRFDIG11TerminalCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_receipt_binds_exact_operator_decision_assurance_and_squash_merge(self):
        self.assertEqual("OVC APPROVE SRFDI-G11 PASS", self.receipt["operator_command"])
        self.assertEqual("PASS", self.receipt["decision"])
        self.assertEqual("OPERATOR", self.receipt["decision_authority"])
        self.assertEqual(592, self.receipt["pr_number"])
        self.assertEqual("c5fcf4d586d2ef0a91371d9310dfec285d8a1c2c", self.receipt["tested_final_head"])
        self.assertEqual({"run_id": 31508213955, "result": "SUCCESS"}, self.receipt["repository_suite"])
        self.assertEqual({"run_id": 31508213952, "result": "SUCCESS"}, self.receipt["tiered_profile_compatibility_merge_readiness"])
        self.assertEqual(0, self.receipt["unresolved_review_threads"])
        self.assertEqual("SQUASH", self.receipt["merge_method"])
        self.assertEqual(MERGE, self.receipt["merge_commit"])
        self.assertEqual(RUN, self.receipt["run_id"])

    def test_terminal_state_completes_programme_without_follow_on(self):
        self.assertEqual("COMPLETED", self.state["status"])
        self.assertIsNone(self.state["current_gate"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual("PASS", self.state["operator_decision"])
        self.assertEqual(MERGE, self.state["merge_commit"])
        self.assertIsNone(self.state["next_packet"])
        self.assertEqual("PROGRAMME_COMPLETED_NO_AUTOMATIC_SCIENTIFIC_FOLLOW_ON", self.state["next_action"])
        self.assertEqual("PROGRAMME_TERMINAL", self.state["stop_condition"])
        self.assertEqual([], self.state["blockers"])

    def test_decomposed_dispositions_are_exactly_preserved(self):
        self.assertEqual(
            self.decision["accepted_decomposed_scientific_dispositions"],
            self.receipt["accepted_decomposed_scientific_dispositions"],
        )
        self.assertEqual(
            self.decision["accepted_decomposed_scientific_dispositions"],
            self.state["accepted_decomposed_scientific_dispositions"],
        )
        self.assertEqual(
            self.decision["accepted_decomposed_scientific_dispositions"],
            self.pointer["g11_accepted_decomposed_scientific_dispositions"],
        )

    def test_reserved_authority_remains_closed_at_terminal_state(self):
        authority = self.state["authority"]
        for key in (
            "active_selector_or_replacement",
            "method_or_family_promotion",
            "scientific_promotion",
            "c2e_activation",
            "semantic_promotion",
            "selector_family_semantic_publication",
            "canonical_r2_publication",
            "probability_risk_exposure_execution",
        ):
            self.assertEqual("NONE", authority[key])
        self.assertEqual("DENIED", authority["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", authority["validation_2025"])

    def test_current_pointer_is_exact_terminal_forward_only_state(self):
        self.assertTrue(assert_lawful_v10_pointer(self, self.pointer))
        self.assertEqual(MERGE, self.pointer["g11_merge_commit"])
        self.assertEqual("PASS", self.pointer["g11_operator_decision"])
        self.assertFalse(self.pointer["g11_operator_decision_pending"])
        self.assertEqual("COMPLETED", self.pointer["status"])
        self.assertIsNone(self.pointer["next_packet"])


if __name__ == "__main__":
    unittest.main()
