from __future__ import annotations
import json,unittest
from pathlib import Path
from ovc.opt_b.market_grammar.typed_grammar import ASTNode,OPERATORS,ParseStatus,compile_grammar,parse_grammar
ROOT=Path(__file__).resolve().parents[2]; FIXTURE=ROOT/'fixtures/market_grammar/wp6/typed_grammar_cases.json'
def load(): return json.loads(FIXTURE.read_text(encoding='utf-8'))
class TypedGrammarTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.fixture=load(); cls.grammar=compile_grammar(cls.fixture['grammar_release'])
 def evidence(self):
  return {'fields':{'transition_evidence':True},'context_status':'AVAILABLE','transitions':[{'from':'BELOW','to':'ABOVE','object_binding':'REF1'}],'nearest_family_id':'F1','nearest_variant_id':'V1','family_distance':'0.1','variant_distance':'0.05','current_phases':['P2'],'completed_phases':['P1'],'lawful_next_phases':['P3'],'upstream_lineage':['C2E.1','C2G.1']}
 def test_release_hash_is_frozen_noncanonical_unpublished(self):
  self.assertEqual('cc8c23540612332ecd2daeb5588450524c52bad3419cacef2dd3d71c6c0ae7c6',self.grammar.release_sha256); self.assertFalse(self.grammar.canonical); self.assertFalse(self.grammar.published); self.assertEqual('SHADOW_EXPERIMENT',self.grammar.authority_state)
 def test_all_eight_frozen_operators_compile(self):
  compiled=[ASTNode.from_mapping(x) for x in self.fixture['valid_operator_nodes']]; self.assertEqual(OPERATORS,{x.operator for x in compiled})
 def test_invalid_operator_and_type_fixtures_fail_closed(self):
  for case in self.fixture['invalid_nodes']:
   with self.assertRaisesRegex(ValueError,case['expected_error']): ASTNode.from_mapping(case['node'])
 def test_parser_status_surface(self):
  base=self.evidence(); self.assertEqual(ParseStatus.GRAMMAR_MATCH,parse_grammar(self.grammar,base).status); self.assertEqual(ParseStatus.AMBIGUOUS_MATCH,parse_grammar(self.grammar,{**base,'ambiguous_match':True}).status)
  partial={**base,'fields':{}}; self.assertEqual(ParseStatus.PARTIAL_MATCH,parse_grammar(self.grammar,partial).status)
  no_match={**base,'context_status':'UNAVAILABLE','transitions':[]}; self.assertEqual(ParseStatus.NO_MATCH,parse_grammar(self.grammar,no_match).status)
  contradiction={**base,'exclusive_conflict_proof':True,'conflicting_evidence':['EXCLUSIVITY_PROOF_X']}; self.assertEqual(ParseStatus.GRAMMAR_CONTRADICTION,parse_grammar(self.grammar,contradiction).status)
  invalidated={**base,'invalidation_reasons':['RESET_BOUNDARY']}; self.assertEqual(ParseStatus.GRAMMAR_INVALIDATED,parse_grammar(self.grammar,invalidated).status)
 def test_ordinary_variation_cannot_create_contradiction(self):
  result=parse_grammar(self.grammar,{**self.evidence(),'conflicting_evidence':['ORDINARY_VARIATION']}); self.assertEqual(ParseStatus.GRAMMAR_MATCH,result.status); self.assertEqual(('ORDINARY_VARIATION',),result.conflicting_evidence)
 def test_result_retains_lineage_distances_phases_and_is_order_independent(self):
  a=parse_grammar(self.grammar,self.evidence()); b=parse_grammar(self.grammar,{**self.evidence(),'upstream_lineage':['C2G.1','C2E.1'],'current_phases':['P2']}); self.assertEqual(a.to_dict(),b.to_dict()); self.assertEqual('F1',a.nearest_family_id); self.assertEqual('V1',a.nearest_variant_id); self.assertEqual('0.1',a.family_distance); self.assertEqual(('C2E.1','C2G.1'),a.upstream_lineage); self.assertTrue(a.parse_id.startswith('C2P.PARSE.'))
 def test_hash_tamper_and_promotion_fail_closed(self):
  raw=dict(self.fixture['grammar_release']); raw['release_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'hash mismatch'): compile_grammar(raw)
  raw=dict(self.fixture['grammar_release']); raw['canonical']=True
  with self.assertRaisesRegex(ValueError,'noncanonical and unpublished'): compile_grammar(raw)
if __name__=='__main__': unittest.main()
