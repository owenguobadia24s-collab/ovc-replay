from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
RECEIPT = ROOT / "docs/releases/sri-fdi-conformance-v0-1/sfc-wp7/SFC_G7_TERMINAL_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/sfc/OVC_SFC_STATE_v0_11_TERMINAL.json"
POINTER = ROOT / "registries/implementation/sfc/CURRENT_STATE_POINTER.json"


class SFCG7TerminalReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_receipt_binds_exact_g7_head_assurance_and_merge(self) -> None:
        self.assertEqual("SFC-G7", self.receipt["gate_id"])
        self.assertEqual("PASS", self.receipt["decision"])
        self.assertEqual("PRESERVED", self.receipt["route"])
        self.assertEqual(476, self.receipt["pr_number"])
        self.assertEqual("c147d980ff400f23e26358980966988f7466fbb1", self.receipt["tested_final_head"])
        self.assertEqual(31282231555, self.receipt["assurance"]["repository_suite"]["run_id"])
        self.assertEqual("SUCCESS", self.receipt["assurance"]["repository_suite"]["result"])
        self.assertEqual(31282231585, self.receipt["assurance"]["tiered_profile_compatibility_merge_readiness"]["run_id"])
        self.assertEqual("SUCCESS", self.receipt["assurance"]["tiered_profile_compatibility_merge_readiness"]["result"])
        self.assertEqual(0, self.receipt["assurance"]["unresolved_review_threads"])
        self.assertEqual("e7fc0925eb3598f75c4734d8dab417c972cfdf8c", self.receipt["merge_commit"])

    def test_terminal_state_is_completed_preserved(self) -> None:
        self.assertEqual("COMPLETED", self.state["status"])
        self.assertEqual("PRESERVED", self.state["programme_disposition"])
        self.assertIsNone(self.state["current_packet"])
        self.assertEqual("SFC-G7", self.state["current_gate"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual("PROGRAMME_COMPLETED_NO_NEXT_PACKET", self.state["next_action"])
        wp7 = self.state["packets"][-1]
        self.assertEqual("SFC-WP7", wp7["packet_id"])
        self.assertEqual("COMPLETED", wp7["status"])
        self.assertEqual("e7fc0925eb3598f75c4734d8dab417c972cfdf8c", wp7["merge_commit"])

    def test_interlock_release_is_future_srfd_preparation_only(self) -> None:
        expected = "RELEASED_FOR_FUTURE_SEPARATELY_GOVERNED_SRFD_PREPARATION_ONLY"
        self.assertEqual(expected, self.receipt["authority_effect"]["srfd_june_authority_interlock"])
        self.assertEqual(expected, self.state["authority"]["srfd_june_authority_interlock"])
        self.assertEqual(expected, self.pointer["srfd_june_authority_interlock"])
        self.assertEqual("DENIED_SEPARATE_SRFDI_G_JUNE_AUTH_REQUIRED", self.pointer["june_execution"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])

    def test_no_reserved_authority_is_added(self) -> None:
        effect = self.receipt["authority_effect"]
        self.assertEqual("NONE", effect["canonical_representation_normalization_comparison_family_sensitivity"])
        self.assertEqual("NONE", effect["selector_semantic_publication"])
        self.assertEqual("NONE", effect["probability_risk_exposure_execution_agent_write"])
        self.assertEqual("NONE_TERMINAL_RECEIPT_ONLY", self.receipt["authority_delta"])
        self.assertEqual("CLOSED_UNMERGED_ATTEMPTED_AUTHORITY_DO_NOT_REUSE_TOKEN", self.receipt["historical_evidence"]["pr_470"])

    def test_pointer_is_exact_terminal_projection(self) -> None:
        self.assertEqual("registries/implementation/sfc/OVC_SFC_STATE_v0_11_TERMINAL.json", self.pointer["authoritative_state"])
        self.assertEqual("COMPLETED", self.pointer["status"])
        self.assertEqual("PRESERVED", self.pointer["programme_disposition"])
        self.assertIsNone(self.pointer["active_packet"])
        self.assertEqual("PROGRAMME_COMPLETED_NO_NEXT_PACKET", self.pointer["next_action"])


if __name__ == "__main__":
    unittest.main()
