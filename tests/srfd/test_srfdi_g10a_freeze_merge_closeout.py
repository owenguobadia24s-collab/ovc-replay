from __future__ import annotations
import json
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a-freeze/SRFDI_G10A_FREEZE_MERGE_RECEIPT.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a-freeze/SRFDI_G10A_FREEZE_CLOSEOUT_QA.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_19_G10A_FREEZE_COMPLETED.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
class SRFDIG10AFreezeMergeCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=json.loads(RECEIPT.read_text()); cls.qa=json.loads(QA.read_text()); cls.state=json.loads(STATE.read_text()); cls.pointer=json.loads(POINTER.read_text())
    def test_exact_primary_merge_and_assurance(self):
        self.assertEqual(446,self.receipt["pr_number"]); self.assertEqual("050e04156501d470575dcc276da2c0d382cf1c33",self.receipt["tested_final_head"]); self.assertEqual("fcf8f2e84111c5c0920cb28816f95b00a9168d81",self.receipt["merge_commit"]); self.assertEqual("SUCCESS",self.receipt["repository_suite"]["result"]); self.assertEqual("SUCCESS",self.receipt["tiered_profile_compatibility_merge_readiness"]["result"])
    def test_closeout_is_zero_delta_delegated_pass(self):
        self.assertEqual("PASS",self.qa["qa_result"]); self.assertTrue(self.qa["auto_ratifiable"]); self.assertEqual("NONE_CLOSEOUT_ONLY",self.qa["authority_delta"]); self.assertEqual("PASS",self.qa["delegated_decision"])
    def test_science_and_authority_firewalls_preserved(self):
        auth=self.state["authority"]; self.assertEqual("CONSUMED_NOT_REUSABLE",auth["authority_token_v0_4"]); self.assertTrue(auth["fresh_june_scientific_run"].startswith("DENIED")); self.assertEqual("DENIED",auth["provider_fetch"]); self.assertEqual("LOCKED_UNCONSUMED",auth["validation_2025"]); self.assertEqual("NONE",auth["scientific_promotion"]); self.assertEqual("NONE",auth["probability_risk_exposure_execution"])
    def test_pointer_routes_only_to_fresh_june_gate_preparation(self):
        self.assertEqual("COMPLETED",self.pointer["status"]); self.assertEqual("SRFDI-G-JUNE-AUTH",self.pointer["current_gate"]); self.assertEqual("SRFDI-G-JUNE-AUTH-PREP",self.pointer["next_packet"]); self.assertTrue(self.pointer["operator_decision_required"]); self.assertIn("DENIED",self.pointer["june_execution"])
if __name__ == "__main__": unittest.main()
