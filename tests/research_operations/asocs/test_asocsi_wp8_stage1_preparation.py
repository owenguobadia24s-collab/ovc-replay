from __future__ import annotations
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
WP8=ROOT/'docs/programmes/asocs-v0-1/implementation/wp8'
SCHEMAS=ROOT/'schemas/research_operations/asocs'
POINTER=ROOT/'registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json'
def _j(p): return json.loads(p.read_text(encoding='utf-8'))
def _cid(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()
def test_stage1_preparation_is_ordered_and_nonrevealing():
    p=_j(WP8/'ASOCSI_WP8_STAGE1_PREPARATION_v0_1.json')
    assert p['stage']=='SOURCE_C1_FIDELITY'
    assert p['required_order']==['SOURCE_C1_FIDELITY','C2_PRIMITIVE_STRUCTURE','C2_COMPOSITION','C2E_TEMPORAL','OCCURRENCE_CONTEXT_FIREWALL']
    assert p['revealed_now'] is False and p['human_adjudication_started'] is False
    assert 'REVEAL_C2_BEFORE_STAGE1_FREEZE' in p['non_grants']
    assert p['construct_survival_rule'].startswith('NO_CONSTRUCT_SURVIVAL_STATE')
def test_stage1_contract_requires_freeze_and_non_authority():
    s=_j(SCHEMAS/'asocs_reveal_stage_record_v0_1.schema.json')
    props=s['properties']
    assert props['frozen_before_next_reveal']['const'] is True
    assert props['authority_class']['const']=='ASOCS_AUDIT_ONLY_NONAUTHORITATIVE_HUMAN_RESEARCH_EVIDENCE'
    f=_j(SCHEMAS/'asocs_failure_attribution_v0_1.schema.json')
    assert f['properties']['information_gap_evaluated_first']['const'] is True
    assert f['properties']['construct_survival_decision']['const']=='PROHIBITED_DURING_CASE_REVIEW'
def test_stage1_authority_and_frontier_are_bounded_and_content_addressable():
    authority=_j(WP8/'ASOCSI_WP8_STAGE1_AUTHORITY_MANIFEST_v0_1.json')
    frontier=_j(WP8/'ASOCSI_WP8_STAGE1_DEPENDENCY_FRONTIER_v0_1.json')
    assert authority['authority_delta']=='NONE'
    assert authority['human_judgement_authority']=='HUMAN_REVIEWER_ONLY_NO_AGENT_SYNTHESIS'
    assert 'STAGE2_C2_PRIMITIVE_REVEAL_BEFORE_STAGE1_FREEZE' in authority['non_grants']
    assert frontier['physical_main_binding']=='LATE_ONLY'
    assert frontier['blocked_until_human_input']==['STAGE2_C2_PRIMITIVE_REVEAL']
    assert _cid(authority)=='55aee9c2bde046137fdf3d05363339be6e812c1201e6da75f41d97d29216d8da'
    assert _cid(frontier)=='493d1ff259a0b98771757472fc6f8861b4431bed5321119fbea18ed90328ea36'
def test_pointer_stops_for_human_scientific_input():
    pointer=_j(POINTER); state=_j(ROOT/pointer['current_state'])
    assert pointer['status']==state['status']=='GATE_READY'
    assert state['authority_delta']=='NONE'
    assert state['candidate_commit']=='RESOLVE_AT_EXACT_HEAD'
    assert state['human_adjudication_started'] is False
    assert state['stage1_reveal_started'] is False
    assert state['blockers']==['HUMAN_STAGE1_SOURCE_C1_FIDELITY_JUDGEMENTS_NOT_YET_SUPPLIED']
