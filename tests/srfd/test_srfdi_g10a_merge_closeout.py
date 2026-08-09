from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/releases/srfd-benchmark-v0-1/srfdi-g10a"
RECEIPT=BASE/"SRFDI_G10A_MERGE_RECEIPT.json"; QA=BASE/"SRFDI_G10A_CLOSEOUT_QA.json"; STATE=ROOT/"registries/implementation/srfd/OVC_SRFDI_STATE_v0_16.json"; POINTER=ROOT/"registries/implementation/srfd/CURRENT_STATE_POINTER.json"
FRESH_V09="SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3"; V09_BINDING="ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a"

class SRFDIG10AMergeCloseoutTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.receipt=json.loads(RECEIPT.read_text()); cls.qa=json.loads(QA.read_text()); cls.state=json.loads(STATE.read_text()); cls.pointer=json.loads(POINTER.read_text())
 def test_operator_supersede_merge_is_exact(self):
  self.assertEqual("SRFDI-G10A",self.receipt["gate_id"]); self.assertEqual("SUPERSEDE",self.receipt["decision"]); self.assertEqual("OPERATOR",self.receipt["decision_authority"]); self.assertEqual(442,self.receipt["pr_number"]); self.assertEqual("20fcc4632847e6013f0ae58ba2bff4470a0493e2",self.receipt["tested_final_head"]); self.assertEqual("b73805d1a846b82cca358815da743041cf2d2d54",self.receipt["merge_commit"]); self.assertEqual("SUCCESS",self.receipt["assurance"]["repository_suite_result"]); self.assertEqual("SUCCESS",self.receipt["assurance"]["tiered_profile_compatibility_merge_readiness_result"])
 def test_consumed_token_and_blocker_remain_preserved(self):
  effect=self.receipt["court_record_effect"]; old="SRFD.JUNE.AUTH.52bcae6e0b748a0c49d578b3b2b529f16754438793cbd261670d91ed0d2a5686"; historical="PR433@f9bbeba065cf85f5a5f5c0a88e9c9d0ea6fa96d7"; self.assertEqual("ADMITTED_PRESERVED_EXACT_HEAD_UNMERGED",effect["pr_433_blocker"]); self.assertEqual("CONSUMED_NOT_REUSABLE",effect["authority_token_v0_4"]); self.assertTrue(self.state["exact_bindings"]["authority_token_consumed"]); self.assertEqual(historical,self.pointer.get("historical_blocker_evidence",self.pointer.get("blocker_evidence")))
  if self.pointer["authority_token_id"]==old: self.assertTrue(self.pointer["authority_token_consumed"])
  else: self.assertEqual(old,self.pointer["prior_authority_token_id"]); self.assertEqual("CONSUMED_NOT_REUSABLE",self.pointer["prior_authority_token_state"])
 def test_state_is_ready_for_wp10a_capacity_only(self):
  self.assertEqual("AUTHORITATIVE_CURRENT",self.state["state_role"]); self.assertEqual("READY",self.state["status"]); self.assertEqual("SRFDI-WP10A",self.state["active_packet"]); self.assertEqual("SRFDI-G10A-FREEZE",self.state["current_gate"]); self.assertEqual("AUTHORIZED_BOUNDED_REAL_DATA_FAMILY_GRID_CAPACITY_REMEDIATION_ONLY",self.state["authority"]["wp10a_execution"]); self.assertTrue(self.state["authority"]["fresh_june_scientific_run"].startswith("DENIED")); self.assertEqual("NONE",self.state["authority"]["scientific_promotion"]); self.assertEqual("NONE",self.state["authority"]["probability_risk_exposure_execution"])
 def test_v16_remains_historical_while_current_pointer_advances_lawfully(self):
  self.assertEqual("OVC-SRFD-BENCHMARK-v0.1",self.pointer["programme_id"]); self.assertTrue(self.pointer["authoritative_state"].startswith("registries/implementation/srfd/OVC_SRFDI_STATE_v0_")); self.assertIn(self.pointer.get("current_gate"),{"SRFDI-G10A-FREEZE","SRFDI-G-JUNE-AUTH","SRFDI-G10","SRFDI-G10C","SRFDI-G11","SRFDI-G10B","SRFDI-G10B-FREEZE",None}); self.assertIn(self.pointer["status"],{"READY","RUNNING","QA_REVIEW","APPROVED","APPROVED_PENDING_MERGE","COMPLETED","BLOCKED","AUTHORIZED_REMEDIATION_ONLY","GATE_READY"}); self.assertIn("fcf8f2e84111c5c0920cb28816f95b00a9168d81",self.pointer.get("capacity_backend_freeze","fcf8f2e84111c5c0920cb28816f95b00a9168d81")); self.assertEqual("DENIED",self.pointer.get("provider_fetch","DENIED")); self.assertEqual("LOCKED_UNCONSUMED",self.pointer.get("validation_2025","LOCKED_UNCONSUMED"))
  if self.pointer["status"]=="AUTHORIZED_REMEDIATION_ONLY": self.assertEqual("SRFDI-G10B",self.pointer["current_gate"]); self.assertEqual("SRFDI-WP10B",self.pointer["next_packet"]); self.assertEqual("SRFDI-G10B-FREEZE",self.pointer["stop_at"]); self.assertTrue(self.pointer["authority_token_consumed"])
  if self.pointer["status"]=="GATE_READY":
   self.assertIn(self.pointer["current_gate"],{"SRFDI-G10B-FREEZE","SRFDI-G-JUNE-AUTH","SRFDI-G10C"}); self.assertIsNone(self.pointer["next_packet"]); self.assertTrue(self.pointer["operator_decision_required"])
   if self.pointer["current_gate"]=="SRFDI-G10B-FREEZE": self.assertEqual("COMPLETED_ASSURED_CANDIDATE_PENDING_OPERATOR_FREEZE",self.pointer["wp10b_execution"])
   elif self.pointer["current_gate"]=="SRFDI-G-JUNE-AUTH": self.assertTrue(self.pointer["wp10b_execution"].startswith("COMPLETED_FROZEN_ON_MAIN@")); self.assertIsNone(self.pointer["fresh_authority_token_id"]); self.assertEqual("NOT_MINTED_PENDING_OPERATOR",self.pointer["fresh_authority_token_state"]); self.assertTrue(self.pointer["june_execution"].startswith("DENIED"))
   else: self.assertEqual(FRESH_V09,self.pointer["fresh_authority_token_id"]); self.assertEqual("AUTHORIZED_UNCONSUMED",self.pointer["fresh_authority_token_state"]); self.assertFalse(self.pointer["fresh_authority_token_consumed"]); self.assertEqual(V09_BINDING,self.pointer["run_binding_sha256"]); self.assertTrue(self.pointer["current_blocker_evidence"].endswith("SRFDI_WP10_V09_PREFLIGHT_EXECUTION_INTERFACE_BLOCKER.json")); self.assertEqual("BLOCKED_PRECONSUMPTION_EXECUTION_INTERFACE_MISMATCH_PENDING_SRFDI_G10C",self.pointer["june_execution"])
 def test_closeout_is_delegated_zero_delta_pass(self):
  self.assertEqual("PASS",self.qa["qa_result"]); self.assertEqual("NONE_CLOSEOUT_ONLY",self.qa["authority_delta"]); self.assertTrue(self.qa["auto_ratifiable"]); self.assertEqual("PASS",self.qa["delegated_decision"]); self.assertEqual("SRFDI-WP10A",self.qa["next_packet"]); self.assertEqual("SRFDI-G10A-FREEZE",self.qa["next_operator_gate"])

if __name__=="__main__": unittest.main()
