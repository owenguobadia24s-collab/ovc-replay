from __future__ import annotations
import json,unittest
from pathlib import Path
from srfd._current_pointer_compat import assert_lawful_v10_pointer
ROOT=Path(__file__).resolve().parents[2]; BLOCKER=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-1/SRFDI_WP10_V11_PREFLIGHT_ENVIRONMENT_BLOCKER.json'; STATE=ROOT/'registries/implementation/srfd/OVC_SRFDI_STATE_v0_49_WP10_V11_PREFLIGHT_ENV_BLOCKED.json'; SUPERSESSION=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-1/SRFDI_WP10_V11_ENVIRONMENT_PROFILE_SUPERSESSION.json'; POINTER=ROOT/'registries/implementation/srfd/CURRENT_STATE_POINTER.json'; TOKEN='SRFD.JUNE.AUTH.7b52e77176fa43d246891ec61d3d0130afe8cb7b5e296f3a705dc83e7fe95b9f'; BINDING='3029d32692f20e724d95ed0b63acf79b1709769f4b8603e9371acee50cd642b5'
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c): c.b=json.loads(BLOCKER.read_text()); c.s=json.loads(STATE.read_text()); c.x=json.loads(SUPERSESSION.read_text()); c.p=json.loads(POINTER.read_text())
 def test_historical_blocker(self): self.assertEqual('BLOCKED_PREFLIGHT_ENVIRONMENT_DRIFT',self.b['status']); self.assertFalse(self.b['token_consumed']); self.assertFalse(self.b['science_execution_started']); self.assertEqual(TOKEN,self.b['token_id']); self.assertEqual(BINDING,self.b['attempted_run_binding_sha256'])
 def test_forensics(self): self.assertEqual(506,self.x['cause']['frozen_profile']['line_count']); self.assertEqual(507,self.x['cause']['runtime_verifier']['line_count']); self.assertFalse(self.x['cause']['relevant_dependency_versions_changed']); self.assertEqual('NONE',self.x['cause']['scientific_delta'])
 def test_current_pointer_progression_preserves_historical_supersession(self): self.assertTrue(assert_lawful_v10_pointer(self,self.p)); self.assertEqual(TOKEN,self.p['superseded_v1_1_authority_token_id']); self.assertEqual(BINDING,self.p['superseded_v1_1_run_binding_sha256']); self.assertEqual('SUPERSEDED_UNUSED_UNCONSUMED_DO_NOT_REUSE',self.p['superseded_v1_1_authority_token_state'])
 def test_reserved_boundaries(self): self.assertEqual('DENIED',self.p['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',self.p['validation_2025']); self.assertEqual('NONE',self.p['scientific_promotion'])
