from __future__ import annotations
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
PACKET=ROOT/"docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9/SRFDI_G_JUNE_AUTH_OPERATOR_PACKET_v0_9.json"; QA=ROOT/"docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9/SRFDI_G_JUNE_AUTH_QA_PACKET_v0_9.json"; MANIFEST=ROOT/"docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9/SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v0_9.json"; STATE=ROOT/"registries/implementation/srfd/OVC_SRFDI_STATE_v0_33_G_JUNE_AUTH_V0_9_GATE_READY.json"; POINTER=ROOT/"registries/implementation/srfd/CURRENT_STATE_POINTER.json"
FRESH_V09="SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3"; V09_BINDING="ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a"
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
class SRFDIJuneAuthV09GateReadyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.packet=json.loads(PACKET.read_text()); cls.qa=json.loads(QA.read_text()); cls.manifest=json.loads(MANIFEST.read_text()); cls.state=json.loads(STATE.read_text()); cls.pointer=json.loads(POINTER.read_text())
 def test_operator_gate_is_exact_and_reserved(self): self.assertEqual("SRFDI-G-JUNE-AUTH",self.packet["gate_id"]); self.assertEqual("OPERATOR_REQUIRED",self.packet["gate_class"]); self.assertEqual("AUTHORIZE_JUNE",self.packet["recommended_decision"]); self.assertEqual("OVC APPROVE SRFDI-G-JUNE-AUTH AUTHORIZE_JUNE",self.packet["exact_operator_command"]); self.assertTrue(self.packet["operator_decision_required"])
 def test_manifest_is_inert_and_exactly_bound(self): self.assertEqual("INERT_PENDING_OPERATOR_AUTHORIZATION",self.manifest["status"]); self.assertEqual(V09_BINDING,canonical_sha(self.manifest["run_binding"])); self.assertEqual(self.manifest["run_binding_sha256"],canonical_sha(self.manifest["run_binding"])); self.assertEqual("2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1",self.manifest["execution_binding"]["logical_sha256"])
 def test_predecision_packet_has_no_token_or_run_authority(self):
  self.assertEqual("NOT_MINTED",self.packet["current_authority"]["fresh_authority_token"]); self.assertTrue(self.packet["current_authority"]["june_execution"].startswith("DENIED")); self.assertEqual("PRESERVED_IMMUTABLE_NOT_RESUMABLE",self.packet["current_authority"]["blocked_v0_8_run"]); self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN",self.manifest["historical_blocked_run"]["token_state"])
  if self.pointer["current_gate"]=="SRFDI-G-JUNE-AUTH" and self.pointer["status"]=="GATE_READY": self.assertIsNone(self.pointer["fresh_authority_token_id"]); self.assertTrue(self.pointer["june_execution"].startswith("DENIED"))
  else:
   self.assertIn(self.pointer["status"],{"APPROVED","READY","RUNNING","BLOCKED","QA_REVIEW","GATE_READY"}); self.assertEqual(FRESH_V09,self.pointer.get("fresh_authority_token_id")); self.assertEqual(V09_BINDING,self.pointer["run_binding_sha256"])
   if self.pointer["current_gate"]=="SRFDI-G10C": self.assertEqual("GATE_READY",self.pointer["status"]); self.assertTrue(self.pointer["operator_decision_required"]); self.assertIsNone(self.pointer["next_packet"]); self.assertEqual("AUTHORIZED_UNCONSUMED",self.pointer["fresh_authority_token_state"]); self.assertFalse(self.pointer["fresh_authority_token_consumed"]); self.assertTrue(self.pointer["current_blocker_evidence"].endswith("SRFDI_WP10_V09_PREFLIGHT_EXECUTION_INTERFACE_BLOCKER.json")); self.assertEqual("BLOCKED_PRECONSUMPTION_EXECUTION_INTERFACE_MISMATCH_PENDING_SRFDI_G10C",self.pointer["june_execution"])
  self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN",self.pointer["authority_token_state"])
 def test_firewalls_and_frozen_science_remain(self):
  d=self.packet["proposed_authority_delta"]; self.assertEqual("DENIED_UNCHANGED",d["provider_fetch"]); self.assertEqual("LOCKED_UNCONSUMED_UNCHANGED",d["validation_2025"])
  for k in ("scientific_parameter_or_method_change","scientific_promotion","selector_change","family_promotion","semantic_promotion","publication","probability_risk_exposure_execution","scope_expansion"): self.assertEqual("NONE",d[k])
  self.assertEqual("PASS_GATE_READY",self.qa["qa_result"]); self.assertEqual("GATE_READY",self.state["status"]); self.assertTrue(self.state["operator_decision_required"]); self.assertEqual("DENIED",self.pointer["provider_fetch"]); self.assertEqual("LOCKED_UNCONSUMED",self.pointer["validation_2025"])
if __name__=="__main__": unittest.main()
