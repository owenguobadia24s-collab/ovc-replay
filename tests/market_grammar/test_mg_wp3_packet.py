from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; BASE=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp3'; STATE=ROOT/'registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc'; IMPLEMENTATION=ROOT/'registries/opt_b/market_grammar/MG_WP3_IMPLEMENTATION_REGISTRY_v0_1.json'; PACKS=ROOT/'registries/opt_b/market_grammar/MG_C2G_SENSITIVITY_PACK_REGISTRY_v0_1.json'
def load(path):
 value=json.loads(path.read_text(encoding='utf-8')); assert isinstance(value,dict); return value
class MarketGrammarWp3PacketTests(unittest.TestCase):
 def test_manifest_and_registry_are_inactive(self):
  manifest=load(BASE/'MG_WP3_IMPLEMENTATION_MANIFEST.json'); registry=load(IMPLEMENTATION); self.assertIn(manifest['status'],{'IMPLEMENTED_PENDING_QA','COMPLETED'}); self.assertIn(registry['status'],{'IMPLEMENTED_PENDING_QA','COMPLETED'}); self.assertEqual('INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY',manifest['authority']); self.assertFalse(registry['canonical_outputs']); self.assertEqual('DEFERRED_TO_MG_WP4',registry['variant_discovery']); self.assertIn('OUTCOMES',registry['forbidden_reads'])
 def test_all_packs_noncanonical(self):
  registry=load(PACKS); self.assertIsNone(registry['canonical_pack_id']); self.assertTrue(registry['comparison_only']); self.assertTrue(all(not item['canonical'] for item in registry['packs']))
 def test_qa_requires_exact_head_and_zero_reserved_delta(self):
  qa=load(BASE/'MG_WP3_QA_PACKET.json'); self.assertIn(qa['status'],{'QA_REVIEW','COMPLETED'}); self.assertIn(qa['qa_recommendation'],{'PASS_IF_EXACT_HEAD_ASSURANCE_PASSES','PASS'}); self.assertEqual('PASS_ZERO',qa['checks']['reserved_authority']); self.assertEqual([],qa['blockers']); self.assertEqual([],qa['warnings'])
 def test_programme_state_routes_no_further_than_wp4(self):
  state=load(STATE); packets={x['packet_id']:x for x in state['packets']}; self.assertEqual('COMPLETED',packets['MG-WP2']['status']); self.assertIn(packets['MG-WP3']['status'],{'RUNNING','IMPLEMENTED','QA_REVIEW','APPROVED','COMPLETED'}); self.assertIn(packets['MG-WP4']['status'],{'PLANNED','READY','RUNNING','IMPLEMENTED','QA_REVIEW','APPROVED','COMPLETED'}); self.assertEqual('OPERATOR_REQUIRED',packets['MG-WP10']['authority_required']); self.assertNotIn(state['status'],{'BLOCKED','QUARANTINED'})
if __name__=='__main__': unittest.main()
