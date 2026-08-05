from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp8/CEAR_G8_ASSURANCE_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G8_FINAL_GATE_READY_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CEARG8AssuranceTests(unittest.TestCase):
    def test_receipt_binds_exact_pre_metadata_head_and_successful_assurance(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(312, receipt["pull_request"])
        self.assertEqual("841e91a4dd9f89372aa64fb87721a9eb71f9eb56", receipt["baseline_commit"])
        self.assertEqual("3993e6fb0af7ea72e0033e6ba3605c342c3ad13c", receipt["assured_pre_metadata_head"])
        self.assertEqual(243, receipt["assurance"][0]["test_count"])
        self.assertTrue(all(item["result"] in {"PASS", "ZERO"} for item in receipt["assurance"]))
        self.assertTrue(all(value == "PASS" for value in receipt["gate_policy_results"].values()))
        self.assertEqual("PASS", receipt["qa_recommendation"])
        self.assertEqual([], receipt["blocking_warnings"])
        self.assertEqual([], receipt["unresolved_issues"])
        self.assertEqual("NONE", receipt["active_authority_effect"])

    def test_final_state_requires_operator_and_prohibits_merge(self) -> None:
        state = load(STATE)
        self.assertEqual("GATE_READY", state["status"])
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual("OVC APPROVE CEAR-G8 PASS", state["exact_approval_command"])
        self.assertEqual("BOUND_BY_PR_312_FINAL_HEAD", state["candidate_commit"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["parent_context_resolver"])
        self.assertEqual("DENIED_PENDING_OPERATOR_PASS_AND_DECISION_PR_MERGE", state["current_authority"]["implementation"])
        self.assertEqual("PROHIBITED_PENDING_OPERATOR_DECISION", state["merge_status"])
        self.assertEqual("C2AR-WP8-IMPLEMENTATION", state["next_packet_on_pass"])
        self.assertEqual("CEAR-G9", state["next_reserved_gate"])
        self.assertEqual([], state["blocking_warnings"])
        self.assertEqual([], state["unresolved_issues"])


if __name__ == "__main__":
    unittest.main()
