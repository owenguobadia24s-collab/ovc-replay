from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; BASE=ROOT/'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp3'; STATE=ROOT/'registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class MarketGrammarWp3ReceiptTests(unittest.TestCase):
 def test_receipt_binds_exact_head_merge_and_assurance(self):
  r=load(BASE/'MG_WP3_POST_MERGE_RECEIPT.json'); self.assertEqual('359fb384866d98f3995feff1df661b81d96ab7ac',r['final_head']); self.assertEqual('72fbe24f73e080109ad5287d5d48f9bc09b026f2',r['merge_commit']); self.assertEqual(349,r['pull_request']); self.assertEqual(0,r['exact_final_head_assurance']['unresolved_review_threads']); self.assertTrue(all(r['exact_final_head_assurance'][k]['conclusion']=='SUCCESS' for k in ('repository_tests','ovc_final_head','compatibility','merge_readiness')))
 def test_decision_is_delegated_nonreserved_pass(self):
  d=load(BASE/'MG_WP3_DELEGATED_DECISION.json'); self.assertEqual('PASS',d['decision']); self.assertTrue(d['delegated_authority']); self.assertFalse(d['operator_required']); self.assertEqual('INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY',d['authority_delta'])
 def test_state_preserves_completion_and_unlocks_wp4(self):
  s=load(STATE); p={x['packet_id']:x for x in s['packets']}; self.assertEqual('COMPLETED',p['MG-WP3']['status']); self.assertIn(p['MG-WP4']['status'],{'READY','RUNNING','IMPLEMENTED','QA_REVIEW','APPROVED','COMPLETED'}); self.assertNotEqual('MG-WP3',s['next_packet']); self.assertEqual('OPERATOR_REQUIRED',p['MG-WP10']['authority_required'])
if __name__=='__main__': unittest.main()
