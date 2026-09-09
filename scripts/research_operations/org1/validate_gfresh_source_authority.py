#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
APP=ROOT/'docs/programmes/org1-v0-1/gfresh/ORG1_GFRESH_GNEW_SOURCE_OPERATOR_APPROVAL_v0_1.json'
SEL=ROOT/'docs/programmes/org1-v0-1/gfresh/ORG1_GFRESH_SOURCE_SELECTION_FREEZE_v0_1.json'
STATE=ROOT/'records/research_operations/org1/ORG1_PROGRAMME_STATE_v0_1.json'

def load(p):return json.loads(p.read_text())
def main():
    a,s,st=map(load,(APP,SEL,STATE))
    assert a['gate_id']=='ORG1-GFRESH-GNEW-SOURCE' and a['decision']=='PASS'
    assert a['operator_command']=='OVC APPROVE ORG1-GFRESH-GNEW-SOURCE'
    assert 'ORG1_D_L_O_TARGET_SCORING' in a['denies']
    assert s['target_firewall']=='CLOSED'
    assert [x['year'] for x in s['candidate_assignments']]==[2012,2013]
    assert s['prohibited_selection_inputs'][0]=='D_L_O_OUTCOMES'
    assert st['status']=='RUNNING'
    assert st['authority_delta']=='BOUNDED_TWO_POPULATION_NEW_REAL_SOURCE_INTAKE_AND_BINDING_ONLY'
    assert st['target_firewall']=='CLOSED_NO_ORG1_D_L_O_ACCESS'
    assert 'TARGET_D_L_O_SCORING' in st['explicit_non_grants']
    print('ORG1_GFRESH_SOURCE_AUTHORITY_VALIDATION_PASS')
if __name__=='__main__':main()
