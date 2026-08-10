from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from srfd._current_pointer_compat import assert_lawful_v10_pointer

from ovc.opt_b.srfd import june_authority_v08
from ovc.opt_b.srfd.serialization import logical_sha256
from ovc.opt_b.srfd.wp10_execution_resilience import ExecutionResilienceError, RunAuthorityStore

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-8"
DECISION=BASE/"SRFDI_G_JUNE_AUTH_DELEGATED_DECISION_v0_8.json"; ENVELOPE=BASE/"SRFD_JUNE_AUTHORITY_ENVELOPE_v0_8.json"; TOKEN=BASE/"SRFD_JUNE_AUTHORITY_TOKEN_v0_8.json"; QA=BASE/"SRFDI_G_JUNE_AUTH_QA_v0_8.json"; SUPERSESSION=BASE/"SRFDI_V07_UNUSED_TOKEN_SUPERSESSION_v0_8.json"; SOURCE_REVERIFY=ROOT/"docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-6/SRFD_SOURCE_ARTIFACT_REVERIFICATION_v0_6.json"; OLD_V07_TOKEN=ROOT/"docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-7/SRFD_JUNE_AUTHORITY_TOKEN_v0_7.json"; IMPL_BINDING=ROOT/"registries/research/srfd/wp10_v07_runner_implementation_binding_v0_1.json"; CANDIDATE_BINDING=ROOT/"registries/research/srfd/wp10b_segmentation_execution_binding_candidate_v0_1.json"; POINTER=ROOT/"registries/implementation/srfd/CURRENT_STATE_POINTER.json"; STATE=ROOT/"registries/implementation/srfd/OVC_SRFDI_STATE_v0_26_JUNE_AUTH_V0_8_RUNNER_BOUND_AUTHORIZED.json"; G10B_DECISION=ROOT/"docs/releases/srfd-benchmark-v0-1/srfdi-g10b/SRFDI_G10B_OPERATOR_DECISION.json"
FRESH_V09="SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3"
V09_BINDING="ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a"

class SRFDIJuneAuthV08RunnerBoundTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.decision=json.loads(DECISION.read_text()); cls.envelope=json.loads(ENVELOPE.read_text()); cls.token=json.loads(TOKEN.read_text()); cls.qa=json.loads(QA.read_text()); cls.supersession=json.loads(SUPERSESSION.read_text()); cls.source_reverify=json.loads(SOURCE_REVERIFY.read_text()); cls.old_v07_token=json.loads(OLD_V07_TOKEN.read_text()); cls.impl_binding=json.loads(IMPL_BINDING.read_text()); cls.candidate_binding=json.loads(CANDIDATE_BINDING.read_text()); cls.pointer=json.loads(POINTER.read_text()); cls.state=json.loads(STATE.read_text()); cls.g10b_decision=json.loads(G10B_DECISION.read_text())
 def test_authority_artifacts_reconstruct_exactly(self):
  self.assertEqual(june_authority_v08.DECISION_SHA256,logical_sha256(self.decision)); self.assertEqual(june_authority_v08.ENVELOPE_SHA256,logical_sha256(self.envelope)); self.assertEqual(june_authority_v08.V07_SUPERSESSION_SHA256,logical_sha256(self.supersession)); self.assertEqual(self.token,june_authority_v08.verify_runner_bound_june_authority(self.decision,self.envelope,self.token,self.source_reverify,self.supersession)); self.assertEqual(june_authority_v08.EXPECTED_TOKEN,self.token["token_id"])
 def test_historical_runner_binding_is_exact_and_only_operator_approved_runner_may_supersede_current_blob(self):
  self.assertEqual(june_authority_v08.RUNNER_IMPLEMENTATION_BINDING_SHA256,logical_sha256(self.impl_binding)); self.assertEqual(self.impl_binding,june_authority_v08.implementation_binding())
  v10_authorized=bool(self.pointer.get("wp10_v1_0_execution_route"))
  g10b_authorized=(self.pointer.get("current_gate") in {"SRFDI-G10B","SRFDI-G10B-FREEZE","SRFDI-G-JUNE-AUTH","SRFDI-G10","SRFDI-G11"} and self.pointer.get("status") in {"AUTHORIZED_REMEDIATION_ONLY","GATE_READY","APPROVED","READY","RUNNING","QA_REVIEW","BLOCKED","RUN_START_AUTHORIZED_PREFLIGHT_PASS","COMPLETED"} and self.g10b_decision["operator_command"]=="OVC APPROVE SRFDI-G10B SUPERSEDE" and self.g10b_decision["decision"]=="SUPERSEDE")
  for name,path in self.impl_binding["runtime_paths"].items():
   data=(ROOT/path).read_bytes(); git_blob=sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest(); historical_blob=self.impl_binding["runtime_blobs"][name]
   if g10b_authorized and name=="production_runner":
    self.assertNotEqual(historical_blob,git_blob)
    if v10_authorized:
     self.assertEqual("ccdde1536660d1ffba95323bcb6228fe1da41cbc",git_blob)
     self.assertEqual("195cce9a44c9071c01f92cbd2b20567c4dae3c79d25bdd7f7778cbed18a3f688",sha256(data).hexdigest())
    else:
     self.assertEqual(self.candidate_binding["runtime_blobs"]["production_runner"],git_blob)
    self.assertEqual(historical_blob,self.candidate_binding["historical_runner_binding"]["production_runner_blob"]); self.assertEqual("SUPERSEDED_FOR_EXECUTION_ONLY",self.g10b_decision["authority_delta"]["wp10_v0_7_output_count_assertion_route"]); self.assertEqual("SRFDI-WP10B",self.g10b_decision["authority_delta"]["authorize_packet"]); self.assertTrue(self.pointer["authority_token_consumed"]); self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN",self.pointer["authority_token_state"])
    if v10_authorized: self.assertTrue(assert_lawful_v10_pointer(self,self.pointer))
    elif self.pointer.get("failure_reason")=="CAPACITY_EXCEEDED_EXTERNAL_BYTES": self.assertEqual("BLOCKED",self.pointer["status"]); self.assertEqual("SRFDI-WP10-v1.0-CAPACITY-REMEDIATION",self.pointer["next_packet"]); self.assertEqual("BLOCKED_CAPACITY_V09_PRESERVED_NOT_COMPLETED",self.pointer["june_execution"]); self.assertEqual(FRESH_V09,self.pointer["fresh_authority_token_id"]); self.assertEqual(V09_BINDING,self.pointer["run_binding_sha256"]); self.assertTrue(self.pointer["fresh_authority_token_consumed"])
    elif self.pointer["current_gate"]=="SRFDI-G-JUNE-AUTH" and self.pointer["status"]=="GATE_READY": self.assertTrue(self.pointer["june_execution"].startswith("DENIED"))
    elif self.pointer["current_gate"]=="SRFDI-G-JUNE-AUTH": self.assertTrue(self.pointer["june_execution"].startswith("AUTHORIZED")); self.assertIsNotNone(self.pointer["fresh_authority_token_id"])
    elif self.pointer["current_gate"]=="SRFDI-G10" and self.pointer["status"]=="READY": self.assertEqual("AUTHORIZED_ONE_EXACT_BOUND_JUNE_RUN_READY",self.pointer["june_execution"]); self.assertEqual(FRESH_V09,self.pointer["fresh_authority_token_id"]); self.assertEqual("AUTHORIZED_UNCONSUMED",self.pointer["fresh_authority_token_state"]); self.assertFalse(self.pointer["fresh_authority_token_consumed"]); self.assertEqual(V09_BINDING,self.pointer["run_binding_sha256"])
    elif self.pointer["current_gate"]=="SRFDI-G10" and self.pointer["status"]=="RUNNING": self.assertEqual("RUNNING_EXACT_BOUND_V09_FROM_COMMITTED_CHECKPOINT",self.pointer["june_execution"]); self.assertEqual(FRESH_V09,self.pointer["fresh_authority_token_id"]); self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN",self.pointer["fresh_authority_token_state"]); self.assertTrue(self.pointer["fresh_authority_token_consumed"]); self.assertEqual(V09_BINDING,self.pointer["run_binding_sha256"])
    else: self.assertEqual("BLOCKED_CONSUMED_RUN_PRESERVED_NO_FRESH_RUN_AUTHORITY",self.pointer["june_execution"])
    self.assertEqual("2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1",self.pointer["effective_runner_implementation_binding_sha256"])
   else: self.assertEqual(historical_blob,git_blob,name)
  self.assertEqual(june_authority_v08.RUN_BINDING_SHA256,june_authority_v08.build_run_binding().logical_hash)
 def test_v07_history_is_preserved_but_cannot_start_new_runner(self):
  self.assertEqual(june_authority_v08.V07_TOKEN,self.old_v07_token["token_id"]); self.assertEqual("AUTHORIZED_UNCONSUMED",self.old_v07_token["state"]); self.assertFalse(self.supersession["superseded_token_consumed"]); self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED",self.supersession["superseded_token_new_state"]); self.assertEqual(june_authority_v08.V07_TOKEN,self.pointer["prior_v0_7_authority_token_id"]); self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED",self.pointer["prior_v0_7_authority_token_state"])
 def test_fresh_v08_token_consumes_once_for_exact_runner_binding(self):
  binding=june_authority_v08.build_run_binding()
  with TemporaryDirectory() as td:
   store=RunAuthorityStore(Path(td)); start=store.consume(self.token,binding); self.assertEqual("CONSUMED_FOR_RUN",start.state); self.assertEqual(self.token["token_id"],start.token_id); self.assertEqual(june_authority_v08.RUN_BINDING_SHA256,start.run_binding_sha256)
   with self.assertRaises(ExecutionResilienceError) as ctx: store.consume(self.token,binding)
   self.assertEqual("TOKEN_ALREADY_CONSUMED",ctx.exception.reason_code)
 def test_historical_v08_authority_is_immutable_while_pointer_may_advance(self):
  self.assertEqual(self.token["token_id"],self.state["authority"]["authority_token_id"]); self.assertFalse(self.state["authority"]["authority_token_consumed"]); self.assertEqual("AUTHORIZED_UNCONSUMED",self.state["authority"]["authority_token_state"]); self.assertEqual("AUTHORIZED_ONE_EXACT_RUN_ID_UNCONSUMED",self.state["authority"]["market_benchmark"]); self.assertEqual(june_authority_v08.RUN_BINDING_SHA256,self.state["exact_bindings"]["run_binding_sha256"]); self.assertEqual(june_authority_v08.RUNNER_IMPLEMENTATION_BINDING_SHA256,self.state["exact_bindings"]["runner_implementation_binding_sha256"]); self.assertEqual("DENIED",self.pointer["provider_fetch"]); self.assertEqual("LOCKED_UNCONSUMED",self.pointer["validation_2025"]); self.assertEqual("NONE",self.pointer["scientific_promotion"]); self.assertEqual("NONE",self.pointer["probability_risk_exposure_execution"])
  if self.pointer["authority_token_id"]==self.token["token_id"]:
   if self.pointer["authority_token_consumed"]: self.assertIn("CONSUMED_FOR_RUN",self.pointer["authority_token_state"])
   else: self.assertEqual("AUTHORIZED_UNCONSUMED",self.pointer["authority_token_state"]); self.assertEqual("READY",self.pointer["status"])
  else: self.assertIn(self.token["token_id"],json.dumps(self.pointer,sort_keys=True))
  if self.pointer.get("wp10_v1_0_execution_route"):
   self.assertTrue(assert_lawful_v10_pointer(self,self.pointer)); return
  if self.pointer.get("failure_reason")=="CAPACITY_EXCEEDED_EXTERNAL_BYTES":
   self.assertEqual("BLOCKED",self.pointer["status"]); self.assertEqual(FRESH_V09,self.pointer["fresh_authority_token_id"]); self.assertTrue(self.pointer["fresh_authority_token_consumed"]); self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN",self.pointer["fresh_authority_token_state"]); self.assertEqual("SRFDI-WP10-v1.0-CAPACITY-REMEDIATION",self.pointer["next_packet"]); self.assertEqual(V09_BINDING,self.pointer["run_binding_sha256"])
  elif self.pointer.get("current_gate")=="SRFDI-G10" and self.pointer["status"]=="READY":
   self.assertEqual(FRESH_V09,self.pointer["fresh_authority_token_id"]); self.assertFalse(self.pointer["fresh_authority_token_consumed"]); self.assertEqual("AUTHORIZED_UNCONSUMED",self.pointer["fresh_authority_token_state"]); self.assertEqual("SRFDI-WP10-v0.9",self.pointer["next_packet"]); self.assertEqual(V09_BINDING,self.pointer["run_binding_sha256"])
  elif self.pointer.get("current_gate")=="SRFDI-G10" and self.pointer["status"]=="RUNNING":
   self.assertEqual(FRESH_V09,self.pointer["fresh_authority_token_id"]); self.assertTrue(self.pointer["fresh_authority_token_consumed"]); self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN",self.pointer["fresh_authority_token_state"]); self.assertEqual("SRFDI-WP10-v0.9-RESUME",self.pointer["next_packet"]); self.assertEqual(V09_BINDING,self.pointer["run_binding_sha256"])
 def test_qa_is_fail_closed_pending_exact_authority_pr_head(self):
  self.assertEqual("PASS_PENDING_EXACT_HEAD_REPOSITORY_ASSURANCE",self.qa["qa_result"]); self.assertEqual([],self.qa["blocking_warnings"]); self.assertEqual([],self.qa["unresolved_issues"]); self.assertIn("FULL_REPOSITORY_SUITE",self.qa["exact_head_requirement"]); self.assertIn("TOKEN_BECOMES_EFFECTIVE",self.qa["on_exact_head_pass"])

if __name__=="__main__": unittest.main()
