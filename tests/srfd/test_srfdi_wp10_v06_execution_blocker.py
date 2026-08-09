from __future__ import annotations
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
BLOCK=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-6/SRFDI_WP10_V06_EXECUTION_BLOCKER.json'; STATE=ROOT/'registries/implementation/srfd/OVC_SRFDI_STATE_v0_22_WP10_V06_BLOCKED.json'; POINTER=ROOT/'registries/implementation/srfd/CURRENT_STATE_POINTER.json'; V06_TOKEN='SRFD.JUNE.AUTH.3c63cd70ea57151a264443b436f94075bd8fb13f8a45f318a245cff96fefd168'; FRESH_V09='SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3'; V09_BINDING='ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a'
class SRFDIWP10V06ExecutionBlockerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.b=json.loads(BLOCK.read_text()); cls.s=json.loads(STATE.read_text()); cls.p=json.loads(POINTER.read_text())
 def test_token_is_consumed_and_never_reusable(self):
  self.assertEqual(V06_TOKEN,self.b['authority_token']['token_id']); self.assertEqual('CONSUMED_NOT_REUSABLE',self.b['authority_token']['state'])
  if self.p['authority_token_id']==V06_TOKEN: self.assertTrue(self.p['authority_token_consumed']); self.assertEqual('CONSUMED_NOT_REUSABLE',self.p['authority_token_state'])
  else: self.assertEqual(V06_TOKEN,self.p['prior_v0_6_authority_token_id']); self.assertEqual('CONSUMED_NOT_REUSABLE',self.p['prior_v0_6_authority_token_state'])
 def test_interruption_is_not_misreported_as_t0_capacity_result(self): self.assertEqual(600,self.b['execution']['local_invocation_ceiling_seconds']); self.assertEqual(14400,self.b['execution']['frozen_t0_max_wall_seconds']); self.assertTrue(self.b['execution']['capacity_interpretation'].startswith('NOT_A_T0_CAPACITY_RESULT')); self.assertFalse(self.b['execution']['checkpoint_receipt_available']); self.assertEqual('FORBIDDEN_WITH_CONSUMED_TOKEN',self.b['execution']['restart_or_retry'])
 def test_partial_outputs_are_not_scientifically_dispositionable(self): e=self.b['scientific_effect']; self.assertFalse(e['wp10_complete']); self.assertFalse(e['g10_qa_eligible']); self.assertFalse(e['wp11_authorized']); self.assertFalse(e['g11_disposition_eligible']); self.assertEqual('INCOMPLETE_NONDISPOSITIONABLE_EVIDENCE',e['partial_family_outputs'])
 def test_firewalls_and_history_are_preserved(self): f=self.b['firewalls']; self.assertEqual('DENIED_NO_ATTEMPT',f['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED_NO_ACCESS',f['validation_2025']); self.assertEqual('UNCHANGED_8598',f['source_population']); self.assertEqual('PRESERVED_HISTORICAL_EVIDENCE',f['pr_433']); self.assertEqual('CONSUMED_NOT_REUSABLE',f['prior_v0_4_token']); self.assertEqual('NON_AUTHORITATIVE_UNMERGED_DO_NOT_REUSE',f['attempted_v0_5_token'])
 def test_immutable_incident_state_and_moving_pointer_both_fail_closed(self):
  p=self.p; self.assertEqual('BLOCKED',self.s['status']); self.assertEqual('SRFDI-WP10-v0.6',self.s['active_packet']); self.assertEqual('SRFDI-G10',self.s['current_gate']); self.assertIsNone(self.s['next_packet']); self.assertEqual('STOP_FAIL_CLOSED_NEW_LAWFUL_SUPERSESSION_REQUIRED',self.s['next_action']); self.assertIn(p['status'],{'BLOCKED','READY','AUTHORIZED_REMEDIATION_ONLY','GATE_READY','APPROVED','RUNNING','QA_REVIEW'}); self.assertEqual('BLOCKED_CONSUMED_TOKEN_PRESERVED',p['wp10_v0_6_execution_route']); self.assertEqual('DENIED',p['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',p['validation_2025']); self.assertEqual('NONE',p['scientific_promotion']); self.assertEqual('NONE',p['probability_risk_exposure_execution'])
  if p.get('wp10_v0_7_execution_route'):
   self.assertTrue(p['blocker_evidence'].endswith('SRFDI_WP10_V07_EXECUTION_BLOCKER.json')); self.assertEqual('CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN',p['authority_token_state'])
   if p['status']=='BLOCKED': self.assertIsNone(p['next_packet']); self.assertEqual('HARD_BLOCKER_SEGMENTATION_BINDING_MISMATCH',p['stop_at'])
   elif p['status']=='AUTHORIZED_REMEDIATION_ONLY': self.assertEqual('SRFDI-G10B',p['current_gate']); self.assertEqual('SRFDI-WP10B',p['next_packet']); self.assertEqual('SRFDI-G10B-FREEZE',p['stop_at']); self.assertTrue(p['authority_token_consumed'])
   elif p['status']=='GATE_READY':
    self.assertIn(p['current_gate'],{'SRFDI-G10B-FREEZE','SRFDI-G-JUNE-AUTH','SRFDI-G10C'}); self.assertIsNone(p['next_packet']); self.assertTrue(p['operator_decision_required']); self.assertTrue(p['authority_token_consumed'])
    if p['current_gate']=='SRFDI-G10B-FREEZE': self.assertEqual('COMPLETED_ASSURED_CANDIDATE_PENDING_OPERATOR_FREEZE',p['wp10b_execution'])
    elif p['current_gate']=='SRFDI-G-JUNE-AUTH': self.assertTrue(p['wp10b_execution'].startswith('COMPLETED_FROZEN_ON_MAIN@')); self.assertIsNone(p['fresh_authority_token_id']); self.assertEqual('NOT_MINTED_PENDING_OPERATOR',p['fresh_authority_token_state']); self.assertTrue(p['june_execution'].startswith('DENIED'))
    else: self.assertEqual(FRESH_V09,p['fresh_authority_token_id']); self.assertEqual('AUTHORIZED_UNCONSUMED',p['fresh_authority_token_state']); self.assertFalse(p['fresh_authority_token_consumed']); self.assertEqual(V09_BINDING,p['run_binding_sha256']); self.assertTrue(p['current_blocker_evidence'].endswith('SRFDI_WP10_V09_PREFLIGHT_EXECUTION_INTERFACE_BLOCKER.json')); self.assertEqual('BLOCKED_PRECONSUMPTION_EXECUTION_INTERFACE_MISMATCH_PENDING_SRFDI_G10C',p['june_execution'])
   elif p.get('current_gate')=='SRFDI-G-JUNE-AUTH': self.assertFalse(p['operator_decision_required']); self.assertIsNotNone(p['fresh_authority_token_id']); self.assertTrue(p['june_execution'].startswith('AUTHORIZED')); self.assertTrue(p['authority_token_consumed'])
  elif p['status']=='BLOCKED': self.assertTrue(p['blocker_evidence'].endswith('SRFDI_WP10_V06_EXECUTION_BLOCKER.json')); self.assertIsNone(p['next_packet']); self.assertEqual('HARD_BLOCKER',p['stop_at'])
  elif p['next_packet']=='SRFDI-G-JUNE-AUTH-v0.7-PREP': self.assertEqual('DENIED_PENDING_NEW_RUN_SCOPED_SRFDI_G_JUNE_AUTH',p['june_execution'])
  else: self.assertEqual('SRFDI-WP10-v0.7',p['next_packet']); self.assertEqual('AUTHORIZED_ONE_EXACT_RUN_ID_UNCONSUMED',p['june_execution']); self.assertEqual('AUTHORIZED_UNCONSUMED',p['authority_token_state'])
if __name__=='__main__': unittest.main()
