from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; FIXTURE=ROOT/'fixtures/market_grammar/wp3/c2g_sensitivity_cases.json'; RUNNER=ROOT/'scripts/market_grammar/run_mg_wp3_fixture.py'; PACKS=ROOT/'registries/opt_b/market_grammar/MG_C2G_SENSITIVITY_PACK_REGISTRY_v0_1.json'; HIERARCHY=ROOT/'registries/opt_b/market_grammar/MG_C2G_HIERARCHY_POLICY_v0_1.json'; SCHEMAS=ROOT/'schemas/opt_b/market_grammar'
def load(path):
 value=json.loads(path.read_text(encoding='utf-8')); assert isinstance(value,dict); return value
def load_runner():
 spec=importlib.util.spec_from_file_location('run_mg_wp3_fixture',RUNNER); assert spec and spec.loader; module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
class FamilyHierarchyFixtureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.fixture=load(FIXTURE); cls.result=load_runner().run(FIXTURE)
 def test_fixture_pack_is_synthetic_and_complete(self):
  self.assertEqual('SYNTHETIC_NON_AUTHORITATIVE',self.fixture['authority']); self.assertEqual(3,len(self.fixture['valid_cases'])); self.assertEqual(5,len(self.fixture['invalid_cases'])); ids=[x['case_id'] for g in ('valid_cases','invalid_cases') for x in self.fixture[g]]; self.assertEqual(len(ids),len(set(ids)))
 def test_valid_results_match_expectations(self):
  by_id={x['case_id']:x for x in self.result['valid_results']}
  for case in self.fixture['valid_cases']:
   actual=by_id[case['case_id']]
   for key,expected in case['expected'].items(): self.assertEqual(expected,actual[key],f"{case['case_id']}:{key}")
   self.assertRegex(actual['hierarchy_id'],r'^C2G\.HIER\.[0-9a-f]{64}$')
 def test_invalid_results_fail_for_expected_reason(self):
  by_id={x['case_id']:x for x in self.result['invalid_results']}
  for case in self.fixture['invalid_cases']: self.assertIn(case['expected_error'],by_id[case['case_id']]['error'])
 def test_runner_is_deterministic(self): self.assertEqual(load_runner().run(FIXTURE),load_runner().run(FIXTURE))
 def test_pack_registry_noncanonical(self):
  registry=load(PACKS); self.assertTrue(registry['comparison_only']); self.assertIsNone(registry['canonical_pack_id']); self.assertEqual(['0.20','0.25','0.35','0.40','0.50'],[x['sensitivity'] for x in registry['packs']]); self.assertTrue(all(x['canonical'] is False for x in registry['packs']))
 def test_hierarchy_policy_and_schemas(self):
  policy=load(HIERARCHY); self.assertTrue(policy['adjacent_packs_only']); self.assertFalse(policy['canonical']); self.assertEqual(['PARENT_OF'],policy['directional_relations']); required={'c2g_assignment_v0_1.schema.json','c2g_family_node_v0_1.schema.json','c2g_hierarchy_ledger_v0_1.schema.json','c2g_sensitivity_pack_v0_1.schema.json','c2g_sensitivity_result_v0_1.schema.json'}; self.assertEqual(required,{p.name for p in SCHEMAS.glob('c2g*_v0_1.schema.json')})
  for path in SCHEMAS.glob('c2g*_v0_1.schema.json'): schema=load(path); self.assertFalse(schema['additionalProperties']); self.assertEqual('https://json-schema.org/draft/2020-12/schema',schema['$schema'])
if __name__=='__main__': unittest.main()
