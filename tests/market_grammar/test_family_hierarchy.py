from __future__ import annotations
import json,unittest
from ovc.opt_b.market_grammar.family_hierarchy import AssignmentStatus,SensitivityPack,StructuralRecord,build_hierarchy,build_sensitivity_result,weighted_distance
HASH='a'*64; FEATURES=('interaction','location','motion','organisation','quality')
def pack(value,containment='0.80'):
 return SensitivityPack.from_mapping({'pack_id':f'MG-C2G-S-{value}-v0.1','sensitivity':value,'feature_weights':{k:'1' for k in FEATURES},'assignment_radius':value,'ambiguity_margin':'0.03','minimum_support':2,'variant_radius':'0.10','containment_threshold':containment,'partial_overlap_threshold':'0.25','missingness_policy':'NOT_EVALUABLE','metric_id':'WEIGHTED_MANHATTAN_V0_1','tie_break':'MAX_COVERAGE_MIN_TOTAL_DISTANCE_LEXICOGRAPHIC_ID','canonical':False})
def record(rid,minute,value,**changes):
 result={'record_id':rid,'record_type':'STATE','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'BID','scope_id':'LOCAL','clock_id':'15M','first_valid_time':f'2026-06-01T00:{minute:02d}:00Z','source_sha256':HASH,'structural_features':{k:str(value) for k in FEATURES}}; result.update(changes); return result
class FamilyHierarchyTests(unittest.TestCase):
 def test_pack_distance_and_noncanonical(self):
  active=pack('0.20'); self.assertFalse(active.canonical); self.assertEqual('0.1',str(weighted_distance(StructuralRecord.from_mapping(record('R1',0,.1)),StructuralRecord.from_mapping(record('R2',5,.2)),active).normalize()))
  with self.assertRaisesRegex(ValueError,'cannot be canonical'): SensitivityPack.from_mapping({**active.to_dict(),'canonical':True})
 def test_order_independent_real_medoid_and_ids(self):
  values=[record('R1',0,.1),record('R2',5,.12),record('R3',10,.8),record('R4',15,.82)]; first=build_sensitivity_result(values,pack('0.20'),build_cutoff='2026-06-01T01:00:00Z'); second=build_sensitivity_result(reversed(values),pack('0.20'),build_cutoff='2026-06-01T01:00:00Z'); self.assertEqual(first.to_dict(),second.to_dict()); self.assertEqual(2,len(first.families)); self.assertTrue(all(f.medoid_record_id in f.member_record_ids for f in first.families)); self.assertNotIn('/tmp',json.dumps(first.to_dict()))
 def test_missingness_is_explicit(self):
  values=[record('R1',0,.1),record('R2',5,.12),{**record('R3',10,.8),'structural_features':{'location':'0.8'}}]; result=build_sensitivity_result(values,pack('0.20'),build_cutoff='2026-06-01T01:00:00Z'); item={x.record_id:x for x in result.assignments}['R3']; self.assertEqual(AssignmentStatus.NOT_EVALUABLE,item.status); self.assertIn('MISSING_STRUCTURAL_FEATURES',item.reason); self.assertIsNone(item.primary_family_id)
 def test_contamination_future_environment_fail_closed(self):
  with self.assertRaisesRegex(ValueError,'non-structural feature'): StructuralRecord.from_mapping({**record('R1',0,.1),'structural_features':{'source_release_id':'0.1'}})
  with self.assertRaisesRegex(ValueError,'future/outcome/downstream'): StructuralRecord.from_mapping({**record('R1',0,.1),'outcome':'UP'})
  with self.assertRaisesRegex(ValueError,'unsupported structural record fields'): StructuralRecord.from_mapping({**record('R1',0,.1),'machine_name':'host-a'})
  with self.assertRaisesRegex(ValueError,'future structural record'): build_sensitivity_result([record('R1',5,.1)],pack('0.20'),build_cutoff='2026-06-01T00:00:00Z')
 def test_hierarchy_acyclic_direction_and_split(self):
  values=[record('R1',0,0),record('R2',5,.05),record('R3',10,.4),record('R4',15,.45)]; low=build_sensitivity_result(values,pack('0.20','0.50'),build_cutoff='2026-06-01T01:00:00Z'); high=build_sensitivity_result(values,pack('0.50','0.50'),build_cutoff='2026-06-01T01:00:00Z'); hierarchy=build_hierarchy([high,low]); self.assertEqual(1,len(hierarchy.split_events)); self.assertEqual(2,sum(1 for edge in hierarchy.edges if edge.directional)); self.assertTrue(all(float(edge.parent_sensitivity)>float(edge.child_sensitivity) for edge in hierarchy.edges if edge.directional)); self.assertEqual('0',hierarchy.adjacent_metrics[0]['reassignment_rate'])
 def test_hierarchy_requires_same_population(self):
  values=[record('R1',0,.1),record('R2',5,.12)]; a=build_sensitivity_result(values,pack('0.20'),build_cutoff='2026-06-01T01:00:00Z'); b=build_sensitivity_result(values+[record('R3',10,.13)],pack('0.35'),build_cutoff='2026-06-01T01:00:00Z')
  with self.assertRaisesRegex(ValueError,'identical input'): build_hierarchy([a,b])
if __name__=='__main__': unittest.main()
