from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from ovc.opt_b.market_grammar.review_surfaces import build_review_model
ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'fixtures/market_grammar/wp8/topology_smoke_cases.json'; PACKS=ROOT/'registries/opt_b/market_grammar/MG_C2G_SENSITIVITY_PACK_REGISTRY_v0_1.json'; LEDGER=ROOT/'registries/opt_b/market_grammar/MG_CEAR_G10_MIGRATION_LEDGER_v0_1.json'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
class ReviewSurfaceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixture=load(FIXTURE); cls.packs=load(PACKS); cls.ledger=load(LEDGER); cls.records=[load(ROOT/item['path']) for item in cls.ledger['migration_records']]; cls.model=build_review_model(cls.fixture,cls.packs,cls.ledger,cls.records)
 def test_all_required_surfaces_are_present_and_read_only(self):
  model=self.model; self.assertFalse(model['canonical']); self.assertFalse(model['mutation_controls']); self.assertEqual('INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_READ_ONLY_REVIEW',model['authority'])
  for key in ('sensitivity_comparison','family_graph','medoid_variant_stability','assignment_explanations','grammar_review','context_review','candidate_migration','counterexample_ledger','issue_ledger'):
   self.assertIn(key,model)
  for key in ('sensitivity_comparison','family_graph','medoid_variant_stability','assignment_explanations','grammar_review','context_review','candidate_migration'):
   self.assertEqual('READ_ONLY',model[key]['mode'])
  self.assertIsNone(model['sensitivity_comparison']['canonical_pack_id']); self.assertIsNone(model['family_graph']['canonical_family_id']); self.assertIsNone(model['medoid_variant_stability']['canonical_variant_id'])
 def test_grammar_and_context_trace_remain_explicit(self):
  grammar=self.model['grammar_review']; context=self.model['context_review']; self.assertFalse(grammar['canonical']); self.assertFalse(grammar['published']); self.assertEqual('GRAMMAR_MATCH',grammar['parse_status']); self.assertTrue(grammar['upstream_lineage']); self.assertFalse(context['missing_context_neutralised']); self.assertEqual('UNAVAILABLE',context['explicit_missing_context']['status']); self.assertEqual(1,context['status_counts']['UNAVAILABLE'])
 def test_all_fourteen_migrations_and_counterexamples_remain_inspectable(self):
  view=self.model['candidate_migration']; self.assertEqual(14,view['candidate_count']); self.assertEqual({'MAPPED':14},view['migration_status_counts']); self.assertEqual('NONE',view['promotion_authority']); self.assertEqual(14,len(view['candidates'])); self.assertGreaterEqual(len(self.model['counterexample_ledger']),14)
  for candidate in view['candidates']:
   self.assertEqual('NONE',candidate['promotion_authority']); self.assertTrue(candidate['read_only']); self.assertRegex(candidate['counterexample_set_sha256'],r'^[0-9a-f]{64}$')
 def test_provenance_is_diagnostic_only(self):
  policy=self.model['provenance_policy']; self.assertFalse(policy['structural_match_feature']); self.assertTrue(policy['diagnostic_only']); self.assertNotEqual(policy['structural_assignment_sha256'],policy['provenance_inclusive_diagnostic_sha256'])
 def test_negative_evidence_and_known_limitations_are_not_hidden(self):
  ids={item['issue_id'] for item in self.model['issue_ledger']}; self.assertIn('MG.WP9.ISSUE.REVISED_C2_SYNTHETIC_BOUNDARY',ids); self.assertIn('MG.WP9.ISSUE.C2G_PROJECTION_ADAPTER',ids); self.assertIn('MG.WP9.ISSUE.TYPED_EMPIRICAL_PARITY_NOT_EVALUATED',ids); self.assertTrue(all(item['authority_effect']=='NONE' for item in self.model['issue_ledger']))
 def test_candidate_order_and_runtime_environment_do_not_change_model(self):
  fixture=copy.deepcopy(self.fixture); fixture['runtime_metadata']={'machine_name':'review-host-z','local_path':'/ignored/review'}; second=build_review_model(fixture,self.packs,self.ledger,list(reversed(self.records))); self.assertEqual(self.model['input_sha256'],second['input_sha256']); self.assertEqual(self.model['result_sha256'],second['result_sha256']); self.assertEqual(canonical(self.model),canonical(second))
 def test_invalid_candidate_inventory_and_promoted_source_fail_closed(self):
  with self.assertRaisesRegex(ValueError,'fourteen'): build_review_model(self.fixture,self.packs,self.ledger,self.records[:-1])
  promoted=copy.deepcopy(self.ledger); promoted['promotion_authority']='PROMOTED'
  with self.assertRaisesRegex(ValueError,'promotion'): build_review_model(self.fixture,self.packs,promoted,self.records)
if __name__=='__main__': unittest.main()
