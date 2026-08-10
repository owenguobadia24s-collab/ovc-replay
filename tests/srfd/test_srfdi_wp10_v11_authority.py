from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.wp10_v10_interface import SCIENCE_IDENTITY_SHA256
from ovc.opt_b.srfd.wp10_v11_interface import binding_from_manifest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v1-1'
MANIFEST=BASE/'SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v1_1.json'
TOKEN=BASE/'SRFD_JUNE_AUTHORITY_TOKEN_v1_1.json'
DECISION=BASE/'SRFD_JUNE_AUTHORITY_OPERATOR_DECISION_v1_1.json'
STATE=ROOT/'registries/implementation/srfd/OVC_SRFDI_STATE_v0_48_WP10_V11_READY.json'
POINTER=ROOT/'registries/implementation/srfd/CURRENT_STATE_POINTER.json'

class SRFDIWP10V11AuthorityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.m=json.loads(MANIFEST.read_text()); cls.t=json.loads(TOKEN.read_text()); cls.d=json.loads(DECISION.read_text()); cls.s=json.loads(STATE.read_text()); cls.p=json.loads(POINTER.read_text()); cls.b=binding_from_manifest(cls.m)
 def test_science_is_exactly_unchanged_and_binding_is_hardened(self):
  self.assertEqual(SCIENCE_IDENTITY_SHA256,self.b.science_identity_sha256); self.assertEqual('1526610575dcd22b066d494c022ba2f443bb099b4f521872c2984765481c58a6',self.b.logical_hash); self.assertEqual('a3162e9260de6168cf57c9f12eef388edbd58c15',self.b.implementation_commit)
 def test_source_artifacts_are_exact_and_provider_fetch_is_denied(self):
  self.assertEqual(6,len(self.m['accepted_source_artifacts'])); self.assertEqual('GOOGLE_DRIVE_ACCEPTED_ARTIFACTS_NO_PROVIDER_FETCH',self.m['retrieval']); self.assertEqual('DENIED',self.m['provider_fetch']); self.assertEqual(9420,self.m['frozen_counts']['source_record_count']); self.assertEqual(8598,self.m['frozen_counts']['eligible_record_count']); self.assertEqual(2020,self.m['frozen_counts']['work_unit_count'])
 def test_token_is_fresh_single_use_and_unconsumed(self):
  self.assertEqual('SRFD.JUNE.AUTH.f80920b2b4d03e00add6621cdda4abdc761f5abf98dae6f072e643f4aaed7f04',self.t['token_id']); self.assertEqual('AUTHORIZED_UNCONSUMED',self.t['state']); self.assertTrue(self.t['single_use']); self.assertEqual('ONE_EXACT_BOUND_RUN',self.t['run_cardinality']); self.assertEqual(self.b.logical_hash,self.t['run_binding_sha256'])
 def test_authority_requires_exact_preflight_before_consumption(self):
  self.assertEqual('PASS_AUTHORIZE_ONE_EXACT_V11_RUN_AFTER_EXACT_PREFLIGHT',self.d['decision']); self.assertIn('EXACT_PREFLIGHT_MUST_PASS_BEFORE_TOKEN_CONSUMPTION',self.d['conditions']); self.assertEqual('READY',self.s['status']); self.assertFalse(self.s['authority']['fresh_authority_token_consumed']); self.assertEqual('RUN_EXACT_V11_PREFLIGHT_THEN_CONSUME_TOKEN_ON_PASS_AND_EXECUTE',self.s['next_action'])
 def test_current_pointer_has_no_scientific_promotion(self):
  self.assertEqual('READY',self.p['status']); self.assertEqual('SRFDI-WP10-v1.1',self.p['active_packet']); self.assertEqual('AUTHORIZED_UNCONSUMED',self.p['fresh_authority_token_state']); self.assertEqual('DENIED',self.p['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',self.p['validation_2025']); self.assertEqual('NONE',self.p['scientific_promotion']); self.assertEqual('NONE',self.p['probability_risk_exposure_execution'])

if __name__=='__main__': unittest.main()
