from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; BASE=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp4'; STATE=ROOT/'registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc'; REG=ROOT/'registries/opt_b/market_grammar/MG_WP4_IMPLEMENTATION_REGISTRY_v0_1.json'; SCHEMAS=ROOT/'schemas/opt_b/market_grammar'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class MarketGrammarWp4PacketTests(unittest.TestCase):
 def test_registry_manifest_and_qa_are_noncanonical(self):
  reg=load(REG); manifest=load(BASE/'MG_WP4_IMPLEMENTATION_MANIFEST.json'); qa=load(BASE/'MG_WP4_QA_PACKET.json'); self.assertFalse(reg['canonical_outputs']); self.assertEqual('INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY',manifest['authority']); self.assertEqual('PASS_ZERO',qa['checks']['reserved_authority']); self.assertEqual([],qa['blockers']); self.assertEqual([],qa['warnings'])
 def test_variant_schemas_are_closed(self):
  for name in ('c2g_family_variant_v0_1.schema.json','c2g_variant_ledger_v0_1.schema.json'):
   schema=load(SCHEMAS/name); self.assertFalse(schema['additionalProperties']); self.assertEqual('https://json-schema.org/draft/2020-12/schema',schema['$schema'])
 def test_state_preserves_upstream_and_routes_only_wp4(self):
  state=load(STATE); p={x['packet_id']:x for x in state['packets']}; self.assertEqual('COMPLETED',p['MG-WP3']['status']); self.assertIn(p['MG-WP4']['status'],{'RUNNING','IMPLEMENTED','QA_REVIEW','APPROVED','COMPLETED'}); self.assertEqual('OPERATOR_REQUIRED',p['MG-WP10']['authority_required']); self.assertNotIn(state['status'],{'BLOCKED','QUARANTINED'})
if __name__=='__main__': unittest.main()
