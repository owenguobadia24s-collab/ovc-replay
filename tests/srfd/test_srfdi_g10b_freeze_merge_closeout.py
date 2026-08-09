from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10b-freeze/SRFDI_G10B_FREEZE_MERGE_RECEIPT.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10b-freeze/SRFDI_G10B_FREEZE_CLOSEOUT_QA.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_32_G10B_FREEZE_COMPLETED.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"

class SRFDIG10BFreezeMergeCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=json.loads(RECEIPT.read_text())
        cls.qa=json.loads(QA.read_text())
        cls.state=json.loads(STATE.read_text())
        cls.pointer=json.loads(POINTER.read_text())

    def test_exact_primary_merge_and_assurance(self):
        self.assertEqual(522,self.receipt["pr_number"])
        self.assertEqual("8ae89f21a7c7bad70cfec0bb8b406562b237553d",self.receipt["tested_final_head"])
        self.assertEqual("eefd860af86aea38e80ec211dd5ea34160171b6f",self.receipt["merge_commit"])
        self.assertEqual("SUCCESS",self.receipt["repository_suite"]["result"])
        self.assertEqual("SUCCESS",self.receipt["tiered_profile_compatibility_merge_readiness"]["result"])
        self.assertEqual(0,self.receipt["unresolved_review_threads"])

    def test_closeout_is_zero_delta_delegated_pass(self):
        self.assertEqual("PASS",self.qa["qa_result"])
        self.assertTrue(self.qa["auto_ratifiable"])
        self.assertEqual("NONE_CLOSEOUT_ONLY",self.qa["authority_delta"])
        self.assertEqual("PASS",self.qa["delegated_decision"])

    def test_binding_is_effective_and_science_is_unchanged(self):
        self.assertEqual("COMPLETED",self.state["status"])
        self.assertEqual("2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1",self.state["exact_bindings"]["execution_binding_logical_sha256"])
        self.assertTrue(self.state["authority"]["segmentation_execution_binding"].endswith("@eefd860af86aea38e80ec211dd5ea34160171b6f"))
        self.assertTrue(self.state["authority"]["fresh_june_scientific_run"].startswith("DENIED"))
        self.assertEqual("LOCKED_UNCONSUMED",self.state["authority"]["validation_2025"])

    def test_pointer_advances_only_to_operator_june_gate(self):
        self.assertEqual("SRFDI-G-JUNE-AUTH",self.pointer["current_gate"])
        self.assertEqual("GATE_READY",self.pointer["status"])
        self.assertTrue(self.pointer["operator_decision_required"])
        self.assertIsNone(self.pointer["fresh_authority_token_id"])
        self.assertEqual("NOT_MINTED_PENDING_OPERATOR",self.pointer["fresh_authority_token_state"])

if __name__ == "__main__":
    unittest.main()
