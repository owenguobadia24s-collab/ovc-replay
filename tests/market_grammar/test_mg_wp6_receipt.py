from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; BASE=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp6'; STATE=ROOT/'registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class MarketGrammarWp6ReceiptTests(unittest.TestCase):
 def test_receipt_and_decision(self):
  r=load(BASE/'MG_WP6_POST_MERGE_RECEIPT.json'); d=load(BASE/'MG_WP6_DELEGATED_DECISION.json'); self.assertEqual('f3f339407f2417fdf62dea7728ef1a918d238217',r['final_head']); self.assertEqual('18a3a1e246e7cb7bccfdf40fe08e195f9332f9ee',r['merge_commit']); self.assertEqual(355,r['pull_request']); self.assertEqual(0,r['exact_final_head_assurance']['unresolved_review_threads']); self.assertEqual('PASS',d['decision']); self.assertTrue(d['delegated_authority']); self.assertFalse(d['operator_required'])
 def test_state_unlocks_wp7_without_promotion(self):
  s=load(STATE); p={x['packet_id']:x for x in s['packets']}; self.assertEqual('COMPLETED',p['MG-WP6']['status']); self.assertIn(p['MG-WP7']['status'],{'READY','RUNNING','IMPLEMENTED','QA_REVIEW','APPROVED','COMPLETED'}); self.assertEqual('PLANNED',p['MG-WP8']['status']); self.assertEqual('OPERATOR_REQUIRED',p['MG-WP10']['authority_required'])
if __name__=='__main__': unittest.main()
