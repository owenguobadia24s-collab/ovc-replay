from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp10'
PACKET=BASE/'MG_WP10_OPERATOR_DECISION_PACKET.json'
DECISION=BASE/'MG_WP10_OPERATOR_DECISION.json'
PREDECISION=BASE/'MG_WP10_PREDECISION_EXACT_HEAD_ASSURANCE.json'
RECEIPT=BASE/'MG_WP10_POST_MERGE_RECEIPT.json'
STATE=ROOT/'registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc'
INVENTORY=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp0/MG_WP0_EXTERNAL_ARTIFACT_INVENTORY.json'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class MarketGrammarWp10GatePacketTests(unittest.TestCase):
 def test_operator_pass_is_recorded_and_programme_is_completed(self):
  packet=load(PACKET); decision=load(DECISION); receipt=load(RECEIPT); state=load(STATE); packets={x['packet_id']:x for x in state['packets']}
  self.assertEqual('MG-WP10',packet['gate_id']); self.assertEqual('APPROVED',packet['status']); self.assertEqual('PASS',packet['decision']); self.assertEqual('PASS',decision['decision']); self.assertEqual('OPERATOR_EXPLICIT',decision['decision_authority']); self.assertEqual('OVC APPROVE MG-WP10 PASS',decision['operator_command']); self.assertEqual('COMPLETED',receipt['status']); self.assertEqual('COMPLETED',state['status']); self.assertEqual('SATISFIED_OPERATOR_DECISION',state['authority_required']); self.assertEqual('COMPLETED',packets['MG-WP10']['status']); self.assertEqual('SATISFIED_OPERATOR_DECISION',packets['MG-WP10']['authority_required']); self.assertEqual('COMPLETED',packets['MG-WP9']['status'])
 def test_approved_delta_explicitly_excludes_reserved_activation(self):
  packet=load(PACKET); limits=' '.join(packet['approved_delta_limits']).lower()
  for phrase in ('no selector','no canonical','no family','no c3','no publication','no active discovery','no probability'):
   self.assertIn(phrase,limits)
 def test_predecision_exact_head_assurance_matches_operator_approved_head(self):
  decision=load(DECISION); assurance=load(PREDECISION); self.assertEqual(decision['approved_gate_head'],assurance['tested_head']); self.assertEqual('PASS_EXACT_HEAD',assurance['result']); self.assertEqual(0,assurance['checks']['unresolved_review_threads'])
 def test_post_merge_receipt_binds_final_head_and_merge(self):
  receipt=load(RECEIPT); self.assertEqual('027726b54b6576b9bf433c091837a17f5c0b89ef',receipt['final_head']); self.assertEqual('a0ce6371e825e376577b98b7a4343ec18c0b67e7',receipt['merge_commit']); self.assertEqual(363,receipt['pull_request']); self.assertEqual(0,receipt['exact_head_assurance']['unresolved_review_threads']); self.assertEqual('NONE_GRANTED',receipt['reserved_authority'])
 def test_external_hash_lock_matches_accepted_inventory(self):
  packet=load(PACKET); inventory=load(INVENTORY); hashes=packet['external_artifact_hashes']; objects={x['object_id']:x['sha256'] for x in inventory['external_objects']}
  self.assertEqual(inventory['binding']['binding_sha256'],hashes['binding_sha256']); self.assertEqual(objects['SRC.DUKASCOPY.GBPUSD.M1.BID.20260530_20260703.v1'],hashes['m1_bid']); self.assertEqual(objects['SRC.DUKASCOPY.GBPUSD.M1.ASK.20260530_20260703.v1'],hashes['m1_ask']); self.assertEqual(objects['SRC.DUKASCOPY.GBPUSD.H1.BID.20260530_20260703.v1'],hashes['h1_bid']); self.assertEqual(objects['SRC.DUKASCOPY.GBPUSD.H1.ASK.20260530_20260703.v1'],hashes['h1_ask']); self.assertEqual(inventory['integrated_package']['package_sha256'],hashes['integrated_package']); self.assertEqual(inventory['logical_population_sha256'],hashes['logical_population'])
 def test_next_programme_is_bounded_and_separate(self):
  decision=load(DECISION); state=load(STATE); nxt=decision['next_programme']; self.assertEqual('OVC-MARKET-GRAMMAR-EMPIRICAL-INTEGRATION-JUNE-v0.1',nxt['programme_id']); self.assertEqual(nxt['programme_id'],state['next_programme']); self.assertIn('accepted June evidence',nxt['scope']); self.assertIn('canonical selection',nxt['stop_before']); self.assertIn('publication',nxt['stop_before'])
if __name__=='__main__': unittest.main()
