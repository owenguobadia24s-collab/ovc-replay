from __future__ import annotations
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-9/SRFDI_WP10_V09_RUN_START_EVIDENCE.json'
S=ROOT/'registries/implementation/srfd/OVC_SRFDI_STATE_v0_42_WP10_V09_RUNNING.json'
P=ROOT/'registries/implementation/srfd/CURRENT_STATE_POINTER.json'
RUN='SRFD.RUN.25ca319a998d72fb01e0dceff2d455f7abf71a4e6419987246529407467e51e5'
TOKEN='SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3'
BIND='ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a'
class SRFDIWP10V09RunStartTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.e=json.loads(E.read_text()); cls.s=json.loads(S.read_text()); cls.p=json.loads(P.read_text())
 def test_exact_preflight_precedes_consumption(self):
  self.assertEqual('PASS',self.e['interface_preflight']['status']); self.assertFalse(self.e['interface_preflight']['token_consumed']); self.assertEqual('PASS',self.e['full_preflight']['status']); self.assertFalse(self.e['full_preflight']['token_consumed']); self.assertEqual(9420,self.e['full_preflight']['source_record_count']); self.assertEqual(8598,self.e['full_preflight']['eligible_record_count']); self.assertEqual(36,self.e['full_preflight']['comparability_domain_count']); self.assertEqual(35380668,self.e['full_preflight']['exact_pair_opportunity_count']); self.assertEqual(1944,self.e['full_preflight']['family_configuration_count'])
 def test_token_consumed_once_for_exact_run(self):
  self.assertEqual(TOKEN,self.e['token_id']); self.assertEqual(RUN,self.e['run_id']); self.assertEqual(BIND,self.e['run_binding_sha256']); self.assertEqual('CONSUMED_FOR_RUN',self.e['consumption']['state']); self.assertTrue(self.s['authority']['fresh_authority_token_consumed']); self.assertEqual('CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN',self.s['authority']['fresh_authority_token_state']); self.assertEqual('NONE',self.s['authority']['new_run_authority'])
 def test_checkpoint_and_external_evidence_are_exact(self):
  self.assertEqual('COMMITTED',self.e['checkpoint']['state']); self.assertEqual(1,self.e['checkpoint']['sequence']); self.assertEqual(['population'],self.e['checkpoint']['completed_units']); self.assertEqual('WITHIN_T0',self.e['capacity_checkpoint']['capacity_status']); self.assertEqual('1WH_AEgvm5ZQd-t0j82pyekAzEhe8bIJk',self.e['evidence_bundle']['drive_file_id']); self.assertEqual('a12487a0abc6d414070f3ab99e225ddcf2105c05d60307656bd961af2983c4ed',self.e['evidence_bundle']['sha256'])
 def test_pointer_preserves_run_and_firewalls(self):
  self.assertEqual('RUNNING',self.p['status']); self.assertEqual(RUN,self.p['run_id']); self.assertEqual(BIND,self.p['run_binding_sha256']); self.assertTrue(self.p['fresh_authority_token_consumed']); self.assertEqual('CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN',self.p['fresh_authority_token_state']); self.assertEqual('SRFDI-WP10-v0.9-RESUME',self.p['next_packet']); self.assertEqual('DENIED',self.p['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',self.p['validation_2025']); self.assertEqual('NONE',self.p['scientific_promotion']); self.assertEqual('NONE',self.p['selector_family_semantic_publication']); self.assertEqual('NONE',self.p['probability_risk_exposure_execution'])
if __name__=='__main__': unittest.main()
