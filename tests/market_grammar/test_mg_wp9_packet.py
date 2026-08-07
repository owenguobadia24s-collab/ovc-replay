from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp9'
STATE=ROOT/'registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc'
REG=ROOT/'registries/opt_b/market_grammar/MG_WP9_IMPLEMENTATION_REGISTRY_v0_1.json'
SCHEMA=ROOT/'schemas/opt_b/market_grammar/mg_wp9_review_model_v0_1.schema.json'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class MarketGrammarWp9PacketTests(unittest.TestCase):
 def test_packet_is_read_only_and_has_zero_reserved_delta(self):
  reg=load(REG); qa=load(BASE/'MG_WP9_QA_PACKET.json'); manifest=load(BASE/'MG_WP9_IMPLEMENTATION_MANIFEST.json'); self.assertFalse(reg['mutation_controls']); self.assertFalse(reg['canonical_selection_controls']); self.assertFalse(reg['promotion_controls']); self.assertFalse(reg['publication_controls']); self.assertFalse(reg['selector_controls']); self.assertFalse(reg['provenance_structural_match_feature']); self.assertEqual('NONE',reg['promotion_authority']); self.assertEqual('PASS_ZERO',qa['checks']['reserved_authority']); self.assertEqual([],qa['blockers']); self.assertFalse(manifest['mutation_controls']); self.assertFalse(manifest['canonical_controls']); self.assertFalse(manifest['publication'])
 def test_review_model_schema_is_closed(self):
  schema=load(SCHEMA); self.assertFalse(schema['additionalProperties']); self.assertEqual('https://json-schema.org/draft/2020-12/schema',schema['$schema'])
 def test_state_preserves_wp8_and_routes_only_wp9(self):
  state=load(STATE); packets={x['packet_id']:x for x in state['packets']}; self.assertEqual('COMPLETED',packets['MG-WP8']['status']); self.assertIn(packets['MG-WP9']['status'],{'RUNNING','IMPLEMENTED','QA_REVIEW','APPROVED','COMPLETED'}); self.assertEqual('PLANNED',packets['MG-WP10']['status']); self.assertEqual('OPERATOR_REQUIRED',packets['MG-WP10']['authority_required']); self.assertNotIn(state['status'],{'BLOCKED','QUARANTINED'})
if __name__=='__main__': unittest.main()
