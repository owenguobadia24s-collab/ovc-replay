from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; BASE=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp6'; STATE=ROOT/'registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc'; REG=ROOT/'registries/opt_b/market_grammar/MG_WP6_IMPLEMENTATION_REGISTRY_v0_1.json'; OPS=ROOT/'registries/opt_b/market_grammar/MG_C2P_OPERATOR_REGISTRY_v0_1.json'; SCHEMAS=ROOT/'schemas/opt_b/market_grammar'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class MarketGrammarWp6PacketTests(unittest.TestCase):
 def test_registry_manifest_qa_preserve_unpublished_noncanonical_boundary(self):
  reg=load(REG); ops=load(OPS); manifest=load(BASE/'MG_WP6_IMPLEMENTATION_MANIFEST.json'); qa=load(BASE/'MG_WP6_QA_PACKET.json'); self.assertFalse(reg['canonical_outputs']); self.assertFalse(reg['grammar_fixture_published']); self.assertIsNone(ops['canonical_grammar_release_id']); self.assertFalse(ops['publication']); self.assertEqual(8,reg['operator_count']); self.assertEqual(6,reg['parse_status_count']); self.assertEqual('PASS_ZERO',qa['checks']['reserved_authority']); self.assertEqual([],qa['blockers']); self.assertEqual([],qa['warnings']); self.assertFalse(manifest['grammar_fixture_published'])
 def test_c2p_schemas_are_closed(self):
  for name in ('c2p_ast_node_v0_1.schema.json','c2p_grammar_release_v0_1.schema.json','c2p_parse_result_v0_1.schema.json'):
   schema=load(SCHEMAS/name); self.assertFalse(schema['additionalProperties']); self.assertEqual('https://json-schema.org/draft/2020-12/schema',schema['$schema'])
 def test_state_preserves_upstream_and_allows_only_lawful_progression_after_wp6(self):
  state=load(STATE); p={x['packet_id']:x for x in state['packets']}; self.assertEqual('COMPLETED',p['MG-WP5']['status']); self.assertEqual('COMPLETED',p['MG-WP6']['status']); self.assertIn(p['MG-WP7']['status'],{'READY','RUNNING','IMPLEMENTED','QA_REVIEW','APPROVED','COMPLETED'}); self.assertEqual('OPERATOR_REQUIRED',p['MG-WP10']['authority_required']); self.assertNotIn(state['status'],{'BLOCKED','QUARANTINED'})
if __name__=='__main__': unittest.main()
