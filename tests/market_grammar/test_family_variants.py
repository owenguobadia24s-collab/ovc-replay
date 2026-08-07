from __future__ import annotations
import json,unittest
from pathlib import Path
from ovc.opt_b.market_grammar.family_hierarchy import FamilyNode,SensitivityPack,SensitivityResult,build_sensitivity_result
from ovc.opt_b.market_grammar.family_variants import VariantAssignmentStatus,build_variant_ledger
ROOT=Path(__file__).resolve().parents[2]; FIXTURE=ROOT/'fixtures/market_grammar/wp4/family_variant_cases.json'; HASH='a'*64; FEATURES=('interaction','location','motion','organisation','quality')
def record(rid,minute,value): return {'record_id':rid,'record_type':'STATE','source_release_id':'REL.SYNTH.v1','instrument_id':'GBPUSD','side':'BID','scope_id':'LOCAL','clock_id':'15M','first_valid_time':f'2026-06-01T00:{minute:02d}:00Z','source_sha256':HASH,'structural_features':{k:str(value) for k in FEATURES}}
def records(values): return [record(f'R{i+1}',i*5,v) for i,v in enumerate(values)]
class FamilyVariantTests(unittest.TestCase):
 def test_valid_fixture_variants_residuals_and_real_medoids(self):
  fixture=json.loads(FIXTURE.read_text()); self.assertEqual('SYNTHETIC_NON_AUTHORITATIVE',fixture['authority'])
  for case in fixture['valid_cases']:
   pack=SensitivityPack.from_mapping(case['pack']); recs=records(case['values']); result=build_sensitivity_result(recs,pack,build_cutoff='2026-06-01T01:00:00Z'); ledger=build_variant_ledger(result,recs); self.assertEqual(case['expected']['variant_count'],len(ledger.variants)); residual=sum(1 for x in ledger.explanations if x.status is VariantAssignmentStatus.FAMILY_RESIDUAL); self.assertEqual(case['expected']['residual_count'],residual); self.assertEqual(len(recs),len(ledger.explanations)); self.assertTrue(all(v.medoid_record_id in v.member_record_ids for v in ledger.variants)); self.assertTrue(all(v.stability_status=='STABLE_UNDER_PACK_CRITERIA' for v in ledger.variants))
 def test_order_independent_and_explanations_are_complete(self):
  case=json.loads(FIXTURE.read_text())['valid_cases'][0]; pack=SensitivityPack.from_mapping(case['pack']); recs=records(case['values']); result=build_sensitivity_result(recs,pack,build_cutoff='2026-06-01T01:00:00Z'); a=build_variant_ledger(result,recs); b=build_variant_ledger(result,reversed(recs)); self.assertEqual(a.to_dict(),b.to_dict()); self.assertEqual(set(result.input_record_ids),{x.record_id for x in a.explanations}); self.assertTrue(all(x.reason for x in a.explanations)); self.assertTrue(all(x.reason for x in a.counterexamples))
 def test_population_mismatch_and_unknown_family_member_fail_closed(self):
  case=json.loads(FIXTURE.read_text())['valid_cases'][0]; pack=SensitivityPack.from_mapping(case['pack']); recs=records(case['values']); result=build_sensitivity_result(recs,pack,build_cutoff='2026-06-01T01:00:00Z')
  with self.assertRaisesRegex(ValueError,'exactly match sensitivity result'): build_variant_ledger(result,recs[:-1])
  family=result.families[0]; bad=FamilyNode(family.family_id,family.pack_id,family.sensitivity,family.source_release_id,family.instrument_id,family.side,family.scope_id,family.clock_id,family.record_type,family.medoid_record_id,family.member_record_ids+('UNKNOWN',),family.dispersion); tampered=SensitivityResult(result.result_id,result.pack,result.build_cutoff,result.input_record_ids,(bad,),result.assignments)
  with self.assertRaisesRegex(ValueError,'unknown member'): build_variant_ledger(tampered,recs)
if __name__=='__main__': unittest.main()
