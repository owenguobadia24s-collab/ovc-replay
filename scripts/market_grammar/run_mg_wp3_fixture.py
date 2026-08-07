#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from ovc.opt_b.market_grammar.family_hierarchy import SensitivityPack,build_hierarchy,build_sensitivity_result
ROOT=Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE=ROOT/'fixtures/market_grammar/wp3/c2g_sensitivity_cases.json'
PACK_REGISTRY=ROOT/'registries/opt_b/market_grammar/MG_C2G_SENSITIVITY_PACK_REGISTRY_v0_1.json'
def load(path):
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict): raise ValueError('JSON root must be an object')
    return value
def packs(): return {item['pack_id']:SensitivityPack.from_mapping(item) for item in load(PACK_REGISTRY)['packs']}
def run(path=DEFAULT_FIXTURE):
    fixture=load(path); registry=packs(); valid=[]; invalid=[]
    for case in fixture['valid_cases']:
        results=[build_sensitivity_result(case['records'],registry[pack_id],build_cutoff=case['build_cutoff']) for pack_id in case['pack_ids']]; hierarchy=build_hierarchy(results)
        valid.append({'case_id':case['case_id'],'result_ids':[item.result_id for item in results],'family_counts':[len(item.families) for item in results],'not_evaluable_counts':[sum(1 for assignment in item.assignments if assignment.status.value=='NOT_EVALUABLE') for item in results],'hierarchy_id':hierarchy.hierarchy_id,'hierarchy_directional_edges':sum(1 for edge in hierarchy.edges if edge.directional),'hierarchy_partial_overlap_edges':sum(1 for edge in hierarchy.edges if not edge.directional),'hierarchy_split_count':len(hierarchy.split_events),'hierarchy_merge_count':len(hierarchy.merge_events)})
    for case in fixture['invalid_cases']:
        try: build_sensitivity_result(case['records'],registry[case['pack_id']],build_cutoff=case['build_cutoff'])
        except ValueError as exc: invalid.append({'case_id':case['case_id'],'error':str(exc)})
        else: raise AssertionError(f"invalid case did not fail: {case['case_id']}")
    return {'schema':'ovc-mg-wp3-fixture-result/v1','authority':fixture['authority'],'pack_registry_id':fixture['pack_registry_id'],'valid_results':valid,'invalid_results':invalid}
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--fixture',type=Path,default=DEFAULT_FIXTURE); args=parser.parse_args(); print(json.dumps(run(args.fixture),sort_keys=True,separators=(',',':'))); return 0
if __name__=='__main__': raise SystemExit(main())
