from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10b-freeze/SRFDI_G10B_FREEZE_MERGE_RECEIPT.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10b-freeze/SRFDI_G10B_FREEZE_CLOSEOUT_QA.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_32_G10B_FREEZE_COMPLETED.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
FRESH_V09 = "SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3"
V09_BINDING = "ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a"

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

    def test_pointer_reaches_june_gate_and_may_advance_only_through_exact_v09_authority(self):
        self.assertIn(self.pointer["current_gate"], {"SRFDI-G-JUNE-AUTH", "SRFDI-G10"})
        self.assertIn(self.pointer["status"], {"GATE_READY", "APPROVED", "READY", "RUNNING", "QA_REVIEW", "BLOCKED"})
        if self.pointer["current_gate"] == "SRFDI-G-JUNE-AUTH" and self.pointer["status"] == "GATE_READY":
            self.assertTrue(self.pointer["operator_decision_required"])
            self.assertIsNone(self.pointer["fresh_authority_token_id"])
            self.assertEqual("NOT_MINTED_PENDING_OPERATOR",self.pointer["fresh_authority_token_state"])
        elif self.pointer["current_gate"] == "SRFDI-G-JUNE-AUTH":
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertEqual(FRESH_V09, self.pointer["fresh_authority_token_id"])
        else:
            self.assertEqual("READY", self.pointer["status"])
            self.assertEqual("SRFDI-WP10-v0.9", self.pointer["next_packet"])
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertEqual(FRESH_V09, self.pointer["fresh_authority_token_id"])
            self.assertEqual("AUTHORIZED_UNCONSUMED", self.pointer["fresh_authority_token_state"])
            self.assertFalse(self.pointer["fresh_authority_token_consumed"])
            self.assertEqual(V09_BINDING, self.pointer["run_binding_sha256"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])

if __name__ == "__main__":
    unittest.main()
