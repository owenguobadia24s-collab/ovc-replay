from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PACKET=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp10/MG_WP10_OPERATOR_DECISION_PACKET.json'
STATE=ROOT/'registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc'
INVENTORY=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp0/MG_WP0_EXTERNAL_ARTIFACT_INVENTORY.json'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class MarketGrammarWp10GatePacketTests(unittest.TestCase):
 def test_terminal_packet_is_operator_required_and_shadow_only(self):
  packet=load(PACKET); state=load(STATE); packets={x['packet_id']:x for x in state['packets']}
  self.assertEqual('MG-WP10',packet['gate_id']); self.assertEqual('GATE_READY',packet['status']); self.assertEqual('PASS',packet['recommended_decision']); self.assertEqual('INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_READ_ONLY',packet['current_authority']); self.assertIn('SHADOW_EXPERIMENT_ONLY',packet['proposed_authority_delta']); self.assertEqual('GATE_READY',state['status']); self.assertEqual('OPERATOR_REQUIRED',state['authority_required']); self.assertEqual('GATE_READY',packets['MG-WP10']['status']); self.assertEqual('OPERATOR_REQUIRED',packets['MG-WP10']['authority_required']); self.assertEqual('COMPLETED',packets['MG-WP9']['status'])
 def test_proposed_delta_explicitly_excludes_reserved_activation(self):
  packet=load(PACKET); limits=' '.join(packet['proposed_delta_limits']).lower()
  for phrase in ('no selector','no canonical','no family','no c3','no publication','no active research authority change'):
   self.assertIn(phrase,limits)
 def test_external_hash_lock_matches_accepted_inventory(self):
  packet=load(PACKET); inventory=load(INVENTORY); hashes=packet['external_artifact_hashes']; objects={x['object_id']:x['sha256'] for x in inventory['external_objects']}
  self.assertEqual(inventory['binding']['binding_sha256'],hashes['binding_sha256']); self.assertEqual(objects['SRC.DUKASCOPY.GBPUSD.M1.BID.20260530_20260703.v1'],hashes['m1_bid']); self.assertEqual(objects['SRC.DUKASCOPY.GBPUSD.M1.ASK.20260530_20260703.v1'],hashes['m1_ask']); self.assertEqual(objects['SRC.DUKASCOPY.GBPUSD.H1.BID.20260530_20260703.v1'],hashes['h1_bid']); self.assertEqual(objects['SRC.DUKASCOPY.GBPUSD.H1.ASK.20260530_20260703.v1'],hashes['h1_ask']); self.assertEqual(inventory['integrated_package']['package_sha256'],hashes['integrated_package']); self.assertEqual(inventory['logical_population_sha256'],hashes['logical_population'])
 def test_operator_command_and_rollback_are_explicit(self):
  packet=load(PACKET); self.assertEqual('OVC APPROVE MG-WP10 PASS',packet['operator_command_for_recommended_decision']); self.assertIn('retain',packet['rollback'].lower()); self.assertGreaterEqual(len(packet['exact_work_after_approval']),6)
if __name__=='__main__': unittest.main()
