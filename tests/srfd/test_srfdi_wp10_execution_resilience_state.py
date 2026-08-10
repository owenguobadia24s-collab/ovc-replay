from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / 'registries/research/srfd/wp10_execution_resilience_profile_v0_1.json'
STATE = ROOT / 'registries/implementation/srfd/OVC_SRFDI_STATE_v0_23_WP10_EXECUTION_RESILIENCE_READY.json'
BLOCKER = ROOT / 'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-6/SRFDI_WP10_V06_EXECUTION_BLOCKER.json'

class SRFDIWP10ExecutionResilienceStateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.profile=json.loads(PROFILE.read_text()); cls.state=json.loads(STATE.read_text()); cls.blocker=json.loads(BLOCKER.read_text())
 def test_v06_consumed_token_remains_immutable_history(self):
  token=self.blocker['authority_token']; self.assertEqual('SRFD.JUNE.AUTH.3c63cd70ea57151a264443b436f94075bd8fb13f8a45f318a245cff96fefd168',token['token_id']); self.assertEqual('CONSUMED_NOT_REUSABLE',token['state'])
 def test_frozen_science_is_exact(self):
  frozen=self.profile['frozen_scientific_bindings']; self.assertEqual(8598,frozen['eligible_record_count']); self.assertEqual(36,frozen['comparability_domain_count']); self.assertEqual(35380668,frozen['exact_pair_opportunity_count']); self.assertEqual(1944,frozen['family_configuration_count']); self.assertEqual('68317db2ddb5608d0dd13bad67be78f70263dee5c2dc59790c1c995098c00866',frozen['capacity_catalog_grid_hash']); self.assertEqual('FORBIDDEN',self.state['frozen_science']['mutation'])
 def test_resilience_is_run_scoped_not_reusable_token_scope(self):
  scope=self.profile['run_scope']; self.assertEqual('ONE_TO_ONE',scope['token_to_run_cardinality']); self.assertEqual('FORBIDDEN',scope['token_reuse']); self.assertEqual('FORBIDDEN',scope['new_run_from_consumed_token']); self.assertEqual('SAME_RUN_ID_FROM_VERIFIED_COMMITTED_CHECKPOINT',scope['resume']); self.assertEqual('FAIL_CLOSED',scope['binding_drift'])
 def test_historical_resilience_state_is_pointer_independent(self):
  self.assertEqual('READY',self.state['status']); self.assertEqual('SRFDI-G-JUNE-AUTH',self.state['current_gate']); self.assertEqual('SRFDI-G-JUNE-AUTH-v0.7-PREP',self.state['next_packet']); self.assertTrue(self.state['authority']['fresh_june_scientific_run'].startswith('DENIED'))
 def test_reserved_authority_firewalls_remain_closed(self):
  self.assertEqual('DENIED',self.profile['firewalls']['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',self.profile['firewalls']['validation_2025']); self.assertEqual('DENIED',self.state['authority'].get('provider_fetch','DENIED')); self.assertEqual('LOCKED_UNCONSUMED',self.state['authority'].get('validation_2025','LOCKED_UNCONSUMED'))
if __name__ == '__main__': unittest.main()
