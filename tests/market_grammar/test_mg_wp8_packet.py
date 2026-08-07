from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp8'
STATE=ROOT/'registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc'
REG=ROOT/'registries/opt_b/market_grammar/MG_WP8_IMPLEMENTATION_REGISTRY_v0_1.json'
SCHEMA=ROOT/'schemas/opt_b/market_grammar/mg_wp8_topology_smoke_result_v0_1.schema.json'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class MarketGrammarWp8PacketTests(unittest.TestCase):
 def test_completed_packet_preserves_inactive_noncanonical_boundary(self):
  reg=load(REG); qa=load(BASE/'MG_WP8_QA_PACKET.json'); manifest=load(BASE/'MG_WP8_IMPLEMENTATION_MANIFEST.json'); decision=load(BASE/'MG_WP8_DELEGATED_DECISION.json'); assurance=load(BASE/'MG_WP8_FINAL_HEAD_ASSURANCE_RECEIPT.json'); receipt=load(BASE/'MG_WP8_POST_MERGE_RECEIPT.json')
  self.assertFalse(reg['canonical_outputs']); self.assertFalse(reg['canonical_sensitivity']); self.assertFalse(reg['mutation_controls']); self.assertEqual('NONE',reg['promotion_authority']); self.assertFalse(reg['publication']); self.assertTrue(reg['checkpoint_restart']); self.assertEqual(14,reg['candidate_migration_count']); self.assertEqual('COMPLETED',reg['status']); self.assertEqual('PASS',qa['status']); self.assertEqual('PASS_ZERO',qa['checks']['reserved_authority']); self.assertEqual([],qa['blockers']); self.assertEqual('COMPLETED',manifest['status']); self.assertEqual('PASS',decision['decision']); self.assertEqual('NONE',decision['reserved_authority_delta']); self.assertEqual('PASS_EXACT_DECISION_HEAD',assurance['result']); self.assertEqual('6d5d08d379f4cbdd280560766b59badb985152df',receipt['merge_commit'])
 def test_result_schema_is_closed(self):
  schema=load(SCHEMA); self.assertFalse(schema['additionalProperties']); self.assertEqual('https://json-schema.org/draft/2020-12/schema',schema['$schema'])
 def test_state_preserves_completed_wp8_while_wp9_progresses(self):
  state=load(STATE); packets={x['packet_id']:x for x in state['packets']}; self.assertEqual('COMPLETED',packets['MG-WP8']['status']); self.assertEqual('SATISFIED_DELEGATED_DECISION',packets['MG-WP8']['authority_required']); self.assertIn(packets['MG-WP9']['status'],{'READY','RUNNING','IMPLEMENTED','QA_REVIEW','APPROVED','COMPLETED'}); self.assertEqual('OPERATOR_REQUIRED',packets['MG-WP10']['authority_required']); self.assertNotIn(state['status'],{'BLOCKED','QUARANTINED'})
if __name__=='__main__': unittest.main()
