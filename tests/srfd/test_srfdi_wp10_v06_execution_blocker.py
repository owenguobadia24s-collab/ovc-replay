from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
BLOCK=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-6/SRFDI_WP10_V06_EXECUTION_BLOCKER.json'
STATE=ROOT/'registries/implementation/srfd/OVC_SRFDI_STATE_v0_22_WP10_V06_BLOCKED.json'
POINTER=ROOT/'registries/implementation/srfd/CURRENT_STATE_POINTER.json'
V06_TOKEN='SRFD.JUNE.AUTH.3c63cd70ea57151a264443b436f94075bd8fb13f8a45f318a245cff96fefd168'

class SRFDIWP10V06ExecutionBlockerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.b=json.loads(BLOCK.read_text()); cls.s=json.loads(STATE.read_text()); cls.p=json.loads(POINTER.read_text())
 def test_token_is_consumed_and_never_reusable(self):
  self.assertEqual(V06_TOKEN,self.b['authority_token']['token_id']); self.assertEqual('CONSUMED_NOT_REUSABLE',self.b['authority_token']['state'])
  if self.p['authority_token_id']==V06_TOKEN:
   self.assertTrue(self.p['authority_token_consumed']); self.assertEqual('CONSUMED_NOT_REUSABLE',self.p['authority_token_state'])
  else:
   self.assertEqual(V06_TOKEN,self.p['prior_v0_6_authority_token_id']); self.assertEqual('CONSUMED_NOT_REUSABLE',self.p['prior_v0_6_authority_token_state'])
 def test_interruption_is_not_misreported_as_t0_capacity_result(self):
  self.assertEqual(600,self.b['execution']['local_invocation_ceiling_seconds']); self.assertEqual(14400,self.b['execution']['frozen_t0_max_wall_seconds']); self.assertTrue(self.b['execution']['capacity_interpretation'].startswith('NOT_A_T0_CAPACITY_RESULT')); self.assertFalse(self.b['execution']['checkpoint_receipt_available']); self.assertEqual('FORBIDDEN_WITH_CONSUMED_TOKEN',self.b['execution']['restart_or_retry'])
 def test_partial_outputs_are_not_scientifically_dispositionable(self):
  e=self.b['scientific_effect']; self.assertFalse(e['wp10_complete']); self.assertFalse(e['g10_qa_eligible']); self.assertFalse(e['wp11_authorized']); self.assertFalse(e['g11_disposition_eligible']); self.assertEqual('INCOMPLETE_NONDISPOSITIONABLE_EVIDENCE',e['partial_family_outputs'])
 def test_firewalls_and_history_are_preserved(self):
  f=self.b['firewalls']; self.assertEqual('DENIED_NO_ATTEMPT',f['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED_NO_ACCESS',f['validation_2025']); self.assertEqual('UNCHANGED_8598',f['source_population']); self.assertEqual('PRESERVED_HISTORICAL_EVIDENCE',f['pr_433']); self.assertEqual('CONSUMED_NOT_REUSABLE',f['prior_v0_4_token']); self.assertEqual('NON_AUTHORITATIVE_UNMERGED_DO_NOT_REUSE',f['attempted_v0_5_token'])
 def test_immutable_incident_state_and_moving_pointer_both_fail_closed(self):
  self.assertEqual('BLOCKED',self.s['status']); self.assertEqual('SRFDI-WP10-v0.6',self.s['active_packet']); self.assertEqual('SRFDI-G10',self.s['current_gate']); self.assertIsNone(self.s['next_packet']); self.assertEqual('STOP_FAIL_CLOSED_NEW_LAWFUL_SUPERSESSION_REQUIRED',self.s['next_action'])
  self.assertIn(self.p['status'], {'BLOCKED','READY','AUTHORIZED_REMEDIATION_ONLY','GATE_READY'})
  self.assertEqual('BLOCKED_CONSUMED_TOKEN_PRESERVED',self.p['wp10_v0_6_execution_route'])
  self.assertEqual('DENIED',self.p['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',self.p['validation_2025']); self.assertEqual('NONE',self.p['scientific_promotion']); self.assertEqual('NONE',self.p['probability_risk_exposure_execution'])
  if self.p.get('wp10_v0_7_execution_route'):
   self.assertTrue(self.p['blocker_evidence'].endswith('SRFDI_WP10_V07_EXECUTION_BLOCKER.json'))
   self.assertEqual('CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN',self.p['authority_token_state'])
   if self.p['status']=='BLOCKED':
    self.assertIsNone(self.p['next_packet']); self.assertEqual('HARD_BLOCKER_SEGMENTATION_BINDING_MISMATCH',self.p['stop_at'])
   elif self.p['status']=='AUTHORIZED_REMEDIATION_ONLY':
    self.assertEqual('SRFDI-G10B',self.p['current_gate']); self.assertEqual('SRFDI-WP10B',self.p['next_packet']); self.assertEqual('SRFDI-G10B-FREEZE',self.p['stop_at']); self.assertTrue(self.p['authority_token_consumed'])
   elif self.p['status']=='GATE_READY':
    self.assertEqual('SRFDI-G10B-FREEZE',self.p['current_gate']); self.assertIsNone(self.p['next_packet']); self.assertTrue(self.p['operator_decision_required']); self.assertEqual('COMPLETED_ASSURED_CANDIDATE_PENDING_OPERATOR_FREEZE',self.p['wp10b_execution']); self.assertTrue(self.p['authority_token_consumed'])
  elif self.p['status']=='BLOCKED':
   self.assertTrue(self.p['blocker_evidence'].endswith('SRFDI_WP10_V06_EXECUTION_BLOCKER.json')); self.assertIsNone(self.p['next_packet']); self.assertEqual('HARD_BLOCKER',self.p['stop_at'])
  elif self.p['next_packet']=='SRFDI-G-JUNE-AUTH-v0.7-PREP':
   self.assertEqual('DENIED_PENDING_NEW_RUN_SCOPED_SRFDI_G_JUNE_AUTH',self.p['june_execution'])
  else:
   self.assertEqual('SRFDI-WP10-v0.7',self.p['next_packet']); self.assertEqual('AUTHORIZED_ONE_EXACT_RUN_ID_UNCONSUMED',self.p['june_execution']); self.assertEqual('AUTHORIZED_UNCONSUMED',self.p['authority_token_state'])

if __name__=='__main__': unittest.main()