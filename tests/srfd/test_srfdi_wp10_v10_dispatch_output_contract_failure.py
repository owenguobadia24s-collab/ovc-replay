from __future__ import annotations

import json
from pathlib import Path
import unittest

from srfd._current_pointer_compat import assert_lawful_v10_pointer

ROOT=Path(__file__).resolve().parents[2]
FAILURE=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-0/SRFDI_WP10_V10_EXECUTION_OUTPUT_CONTRACT_FAILURE.json'
QA=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-0/SRFDI_WP10_V10_EXECUTION_OUTPUT_CONTRACT_FAILURE_QA.json'
STATE=ROOT/'registries/implementation/srfd/OVC_SRFDI_STATE_v0_47_WP10_V10_DISPATCH_BLOCKED.json'
POINTER=ROOT/'registries/implementation/srfd/CURRENT_STATE_POINTER.json'
RUN='SRFD.RUN.21c4557cf2de0a27656e3e762a702b9dda4ce01e6119f619bedf232cafd5f6d5'
TOKEN='SRFD.JUNE.AUTH.ba38ee329eba42c169420bb328956777b3604de4db35308fa306a9bda8711927'

class SRFDIWP10V10DispatchOutputContractFailureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.f=json.loads(FAILURE.read_text()); cls.q=json.loads(QA.read_text()); cls.s=json.loads(STATE.read_text()); cls.p=json.loads(POINTER.read_text())
 def test_consumed_v10_run_is_blocked_and_preserved(self):
  self.assertEqual('BLOCKED_PRESERVED_NOT_COMPLETED',self.f['status']); self.assertEqual(RUN,self.f['run_id']); self.assertEqual(TOKEN,self.f['token_id']); self.assertEqual('CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN',self.f['token_state']); self.assertEqual('WORK_UNIT_DISPATCH_OUTPUT_CONTRACT_CORRUPTION',self.f['failure_class'])
 def test_checkpoint_corruption_range_is_explicit_and_immutable(self):
  e=self.f['checkpoint_evidence']; self.assertEqual(282,e['last_unambiguously_bound_runner_sequence']); self.assertEqual(284,e['correct_next_domain_preparation_sequence']); self.assertEqual(285,e['first_invalid_sequence']); self.assertEqual(338,e['last_invalid_sequence']); self.assertEqual(54,e['invalid_configuration_unit_count']); self.assertEqual('FORBIDDEN',e['checkpoint_rewrite']); self.assertEqual('FORBIDDEN',e['checkpoint_truncation']); self.assertEqual('FORBIDDEN',e['same_run_resume'])
 def test_hardening_pass_is_bound_but_real_memory_safe_route_is_still_required(self):
  self.assertEqual('PASS_2020_OF_2020',self.f['hardening_resolution']['rehearsal_status']); self.assertEqual('PASS',self.f['hardening_resolution']['strict_output_contracts']); self.assertIn('MEMORY_SAFE',self.q['blockers'][0]); self.assertEqual('V11_EXECUTION_ROUTE_IMPLEMENTATION_ONLY_NO_SCIENTIFIC_RUN_AUTHORITY',self.q['authority_effect'])
 def test_current_pointer_preserves_v10_failure_while_allowing_exact_v11_progression(self):
  self.assertEqual('DENIED',self.p['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',self.p['validation_2025']); self.assertEqual('NONE',self.p['scientific_promotion']); self.assertEqual('NONE',self.p['probability_risk_exposure_execution'])
  if self.p.get('active_packet') == 'SRFDI-WP10-v1.1':
   self.assertTrue(assert_lawful_v10_pointer(self,self.p)); self.assertEqual('BLOCKED_DISPATCH_OUTPUT_CONTRACT_FAILURE_PRESERVED',self.p['wp10_v1_0_execution_route'])
   if self.p['status']=='BLOCKED':
    self.assertTrue(self.p['failure_receipt'].endswith('SRFDI_WP10_V11_PREFLIGHT_ENVIRONMENT_BLOCKER.json')); self.assertEqual('BLOCKED_PREFLIGHT_ENVIRONMENT_DRIFT_TOKEN_UNCONSUMED',self.p['wp10_v1_1_execution_route'])
   else:
    self.assertEqual('AUTHORIZED_UNCONSUMED_PENDING_EXACT_PREFLIGHT',self.p['wp10_v1_1_execution_route'])
   return
  self.assertEqual('BLOCKED',self.p['status']); self.assertEqual('SRFDI-WP10-v1.1-REAL-EXECUTION-ROUTE',self.p['next_packet']); self.assertEqual('IMPLEMENTATION_ONLY_NO_RUN_AUTHORITY',self.p['wp10_v1_1_execution_route'])

if __name__=='__main__': unittest.main()
