from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from ovc.opt_b.market_grammar.family_hierarchy import StructuralRecord
from ovc.opt_b.market_grammar.revised_c2_adapter import EmpiricalBinding
from ovc.opt_b.market_grammar.structural_projection import FEATURE_KEYS,PROJECTION_ID,project_revised_c2_state,project_revised_c2_states
ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'fixtures/market_grammar/ei_wp2/structural_projection_cases.json'
STATE=ROOT/'registries/opt_b/market_grammar/OVC_MG_EI_JUNE_PROGRAMME_STATE_v0_1.jsonc'
REG=ROOT/'registries/opt_b/market_grammar/MG_EI_WP2_IMPLEMENTATION_REGISTRY_v0_1.json'
QA=ROOT/'docs/releases/market-grammar-empirical-integration-june-v0-1/ei-wp2/EI_WP2_QA_PACKET.json'
PACKS=ROOT/'registries/opt_b/market_grammar/MG_C2G_SENSITIVITY_PACK_REGISTRY_v0_1.json'
SCHEMA=ROOT/'schemas/opt_b/market_grammar/mg_ei_wp2_structural_projection_v0_1.schema.json'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class StructuralProjectionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.fixture=load(FIXTURE); cls.binding=EmpiricalBinding.from_mapping(cls.fixture['binding']); cls.rows=cls.fixture['rows']
 def test_evaluable_projection(self):
  item=project_revised_c2_state(self.rows[0],binding=self.binding); StructuralRecord.from_mapping(item); self.assertEqual('EVALUABLE',item['computability_status']); self.assertEqual(tuple(item['structural_features']),FEATURE_KEYS); self.assertEqual({'location':'0.200000000000','motion':'0.650000000000','organisation':'0.550000000000','interaction':'0.300000000000','quality':'1.000000000000'},item['structural_features'])
 def test_not_evaluable_projection_is_empty(self):
  item=project_revised_c2_state(self.rows[3],binding=self.binding); StructuralRecord.from_mapping(item); self.assertEqual('NOT_EVALUABLE',item['computability_status']); self.assertEqual({},item['structural_features']); self.assertIn('MOTION:NOT_EVALUABLE:HORIZON_INCOMPLETE',item['not_evaluable_reason'])
 def test_bad_measurements_never_create_partial_vector(self):
  for value in (None,'1.2','abc'):
   row=copy.deepcopy(self.rows[0]); row['axes']['INTERACTION']['measurement']=value; item=project_revised_c2_state(row,binding=self.binding); self.assertEqual('NOT_EVALUABLE',item['computability_status']); self.assertEqual({},item['structural_features'])
 def test_order_and_diagnostics_do_not_change_identity(self):
  first=project_revised_c2_states(self.rows,binding=self.binding); changed=copy.deepcopy(list(reversed(self.rows)))
  for i,row in enumerate(changed): row['diagnostic_metadata']={'machine':f'other-{i}','path':f'/tmp/{i}'}
  second=project_revised_c2_states(changed,binding=self.binding); self.assertEqual(first['logical_sha256'],second['logical_sha256']); self.assertEqual(first['records'],second['records'])
 def test_feature_map_only_contains_evaluable_records(self):
  result=project_revised_c2_states(self.rows,binding=self.binding); self.assertEqual(PROJECTION_ID,result['projection_id']); self.assertEqual(4,result['record_count']); self.assertEqual(3,result['evaluable_count']); self.assertEqual(1,result['not_evaluable_count']); self.assertNotIn('EI.WP2.C2.ASK.002',result['state_structural_features']); self.assertFalse(result['canonical']); self.assertFalse(result['published'])
 def test_parent_adapter_guards_are_inherited(self):
  row=copy.deepcopy(self.rows[0]); row['clock_id']='2H_A_L'
  with self.assertRaisesRegex(ValueError,'CLOCK_SCOPE_MISMATCH'): project_revised_c2_state(row,binding=self.binding)
 def test_frozen_sensitivity_registry_is_comparison_only(self):
  packs=load(PACKS); self.assertTrue(packs['comparison_only']); self.assertIsNone(packs['canonical_pack_id']); self.assertEqual(5,len(packs['packs']))
  for pack in packs['packs']: self.assertFalse(pack['canonical']); self.assertEqual(set(FEATURE_KEYS),set(pack['feature_weights'])); self.assertEqual({'1'},set(pack['feature_weights'].values()))
 def test_schema_registry_qa_and_state(self):
  schema=load(SCHEMA); reg=load(REG); qa=load(QA); state=load(STATE); packets={x['packet_id']:x for x in state['packets']}; self.assertFalse(schema['additionalProperties']); self.assertFalse(reg['canonical_controls']); self.assertFalse(reg['sensitivity_controls']); self.assertFalse(reg['promotion_controls']); self.assertFalse(reg['publication_controls']); self.assertEqual('NONE',reg['promotion_authority']); self.assertEqual([],qa['blockers']); self.assertEqual('COMPLETED',packets['EI-WP1']['status']); self.assertEqual('COMPLETED',packets['EI-WP2']['status']); self.assertIn(packets['EI-WP3']['status'],{'READY','RUNNING','IMPLEMENTED','QA_REVIEW','APPROVED','COMPLETED'})
if __name__=='__main__': unittest.main()
