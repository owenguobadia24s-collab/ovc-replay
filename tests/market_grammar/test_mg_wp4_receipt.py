from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; BASE=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp4'; STATE=ROOT/'registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class MarketGrammarWp4ReceiptTests(unittest.TestCase):
 def test_receipt_and_decision(self):
  r=load(BASE/'MG_WP4_POST_MERGE_RECEIPT.json'); d=load(BASE/'MG_WP4_DELEGATED_DECISION.json'); self.assertEqual('cc9ee000cd1bfbae312d711df25ddebd80489617',r['final_head']); self.assertEqual('624b4bfb9b51b1e460fb2cec30f593651569d9ff',r['merge_commit']); self.assertEqual(351,r['pull_request']); self.assertEqual(0,r['exact_final_head_assurance']['unresolved_review_threads']); self.assertEqual('PASS',d['decision']); self.assertTrue(d['delegated_authority']); self.assertFalse(d['operator_required'])
 def test_state_unlocks_wp5_without_reserved_delta(self):
  s=load(STATE); p={x['packet_id']:x for x in s['packets']}; self.assertEqual('COMPLETED',p['MG-WP4']['status']); self.assertIn(p['MG-WP5']['status'],{'READY','RUNNING','IMPLEMENTED','QA_REVIEW','APPROVED','COMPLETED'}); self.assertEqual('OPERATOR_REQUIRED',p['MG-WP10']['authority_required']); self.assertNotEqual('MG-WP4',s['next_packet'])
if __name__=='__main__': unittest.main()
