from __future__ import annotations
import copy,json,time,unittest
from pathlib import Path
from ovc.opt_b.market_grammar.topology_smoke import MAX_RETAINED_BYTES,MAX_RUNTIME_SECONDS,make_checkpoint,resume_topology_smoke,run_topology_smoke
ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'fixtures/market_grammar/wp8/topology_smoke_cases.json'
PACKS=ROOT/'registries/opt_b/market_grammar/MG_C2G_SENSITIVITY_PACK_REGISTRY_v0_1.json'
MIGRATIONS=ROOT/'registries/opt_b/market_grammar/MG_CEAR_G10_MIGRATION_LEDGER_v0_1.json'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
class TopologySmokeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixture=load(FIXTURE); cls.packs=load(PACKS); cls.migrations=load(MIGRATIONS); started=time.monotonic(); cls.result=run_topology_smoke(cls.fixture,cls.packs,cls.migrations); cls.elapsed=time.monotonic()-started
 def test_full_component_topology_is_present_and_shadow_only(self):
  result=self.result; counts=result['component_counts']; self.assertEqual(8,counts['c2_records']); self.assertEqual(4,counts['episodes']); self.assertGreaterEqual(counts['state_families'],1); self.assertGreaterEqual(counts['transition_families'],1); self.assertEqual([2,2],counts['episode_families_by_pack']); self.assertEqual(2,counts['variants']); self.assertEqual(14,counts['candidate_migrations']); self.assertEqual('GRAMMAR_MATCH',result['parse_result']['status']); self.assertFalse(result['canonical']); self.assertFalse(result['published']); self.assertFalse(result['grammar_release']['canonical']); self.assertFalse(result['grammar_release']['published']); self.assertFalse(result['read_only_projection']['mutation_controls']); self.assertEqual('NONE',result['candidate_migration']['promotion_authority']); self.assertIsNone(result['sensitivity_comparison']['canonical_pack_id'])
 def test_missing_context_is_explicit_and_never_neutralised(self):
  self.assertEqual('UNAVAILABLE',self.result['missing_context_resolution']['status']); self.assertEqual(1,self.result['context_status_counts']['UNAVAILABLE']); self.assertEqual(4,self.result['context_status_counts']['AVAILABLE']); self.assertEqual('AVAILABLE',self.result['parse_result']['context_status'])
 def test_two_clean_runs_are_byte_identical_and_checkpoint_restart_reproduces(self):
  second=run_topology_smoke(self.fixture,self.packs,self.migrations); self.assertEqual(canonical(self.result),canonical(second)); checkpoint=make_checkpoint(self.result); resumed=resume_topology_smoke(self.fixture,self.packs,self.migrations,checkpoint); self.assertEqual(canonical(self.result),canonical(resumed))
 def test_shuffled_c2_order_and_environment_labels_do_not_change_identity(self):
  shuffled=copy.deepcopy(self.fixture); shuffled['c2_records']=list(reversed(shuffled['c2_records'])); shuffled['runtime_metadata']={'machine_name':'another-host','local_path':'/tmp/another'}; result=run_topology_smoke(shuffled,self.packs,self.migrations); self.assertEqual(self.result['input_sha256'],result['input_sha256']); self.assertEqual(self.result['result_sha256'],result['result_sha256']); self.assertEqual(self.result['component_ids'],result['component_ids'])
 def test_provenance_is_diagnostic_only_and_does_not_enter_assignments(self):
  surface=self.result['provenance_ablation']; self.assertFalse(surface['structural_assignments_include_provenance']); self.assertTrue(surface['diagnostic_only']); self.assertNotEqual(surface['structural_assignment_sha256'],surface['provenance_inclusive_diagnostic_sha256'])
 def test_fourteen_wp7_dispositions_are_retained_without_promotion(self):
  migration=self.result['candidate_migration']; self.assertEqual(14,len(migration['candidate_ids'])); self.assertEqual({'MAPPED':14},migration['migration_status_counts']); self.assertEqual('b7873a8ebac5f53f88cf90beed1e00f0ea92488270293ed2a82f2dafafc16733',migration['ledger_sha256']); self.assertEqual('NONE',migration['promotion_authority'])
 def test_capacity_envelope(self):
  self.assertLess(self.elapsed,MAX_RUNTIME_SECONDS); self.assertLess(len(canonical(self.result)),MAX_RETAINED_BYTES); self.assertLess(self.result['capacity']['retained_payload_bytes_before_result_hash'],MAX_RETAINED_BYTES)
 def test_invalid_checkpoint_and_migration_binding_fail_closed(self):
  checkpoint=make_checkpoint(self.result); checkpoint['result_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'checkpoint result'): resume_topology_smoke(self.fixture,self.packs,self.migrations,checkpoint)
  tampered=copy.deepcopy(self.migrations); tampered['candidate_count']=13
  with self.assertRaisesRegex(ValueError,'fourteen'): run_topology_smoke(self.fixture,self.packs,tampered)
if __name__=='__main__': unittest.main()
