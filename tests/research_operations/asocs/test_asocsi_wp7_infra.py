from __future__ import annotations
import json
from pathlib import Path
import pytest
from ovc.research_operations.asocs.blind_review import ASOCSBlindFirewallError,BLIND_RESOURCE_ROOT,REVEAL_RESOURCE_ROOT,freeze_blind_record,overlay_visible_review_anchor,review_anchor_partition,review_anchor_time,successor_annotation,tradingview_trace_record,validate_blind_index,validate_prompt_registry
from ovc.research_operations.asocs.population_core import render_source_native_svg
ROOT=Path(__file__).resolve().parents[3]
def _json(p:str)->dict: return json.loads((ROOT/p).read_text(encoding='utf-8'))

def test_blind_and_reveal_resources_are_nonoverlapping():
    assert BLIND_RESOURCE_ROOT!=REVEAL_RESOURCE_ROOT
    assert not BLIND_RESOURCE_ROOT.startswith(REVEAL_RESOURCE_ROOT)
    assert not REVEAL_RESOURCE_ROOT.startswith(BLIND_RESOURCE_ROOT)

def test_blind_index_standard_views_and_recursive_leak_firewall():
    allowed=_json('fixtures/research_operations/asocs/wp7/blind_index_allowed_v0_1.json')
    assert validate_blind_index(allowed)==allowed
    with pytest.raises(ASOCSBlindFirewallError,match='BLIND_METADATA_LEAK'):
        validate_blind_index(_json('fixtures/research_operations/asocs/wp7/blind_index_leak_v0_1.json'))

def test_prompt_registry_is_free_description_first_neutral_and_anchor_explicit():
    registry=_json('registries/research_operations/asocs/ASOCSI_WP7_BLIND_PROMPT_REGISTRY_v0_1.json')
    validate_prompt_registry(registry['prompts'])
    assert registry['prompts'][0]['id']=='A0'
    prompts={p['id']:p['text'] for p in registry['prompts']}
    assert 'displayed review anchor' in prompts['A4']
    assert 'displayed review anchor' in prompts['A5']
    assert 'marked time' not in prompts['A4']+prompts['A5']

def test_visible_review_anchor_uses_time_partition_not_geometric_midpoint_when_gaps_exist():
    bars=[
        {'interval_start':'2026-01-01T00:00:00','open':'1.0','high':'1.2','low':'0.9','close':'1.1'},
        {'interval_start':'2026-01-01T00:15:00','open':'1.1','high':'1.3','low':'1.0','close':'1.2'},
        {'interval_start':'2026-01-01T00:30:00','open':'1.2','high':'1.4','low':'1.1','close':'1.3'},
        {'interval_start':'2026-01-01T01:45:00','open':'1.3','high':'1.5','low':'1.2','close':'1.4'},
    ]
    window={'start':'2026-01-01T00:00:00','end':'2026-01-01T02:00:00'}
    anchor,split=review_anchor_partition(bars,window)
    assert anchor.isoformat()=='2026-01-01T01:00:00'
    assert split==3
    svg=render_source_native_svg(bars)
    marked=overlay_visible_review_anchor(svg,bars,window)
    assert 'data-asocs-review-anchor="visible-neutral-reference"' in marked
    assert 'data-anchor-time="2026-01-01T01:00:00"' in marked
    assert 'x1="880.000"' in marked and 'x2="880.000"' in marked
    assert marked.count('REVIEW ANCHOR')==1

def test_review_anchor_rejects_missing_or_invalid_temporal_inputs():
    with pytest.raises(ASOCSBlindFirewallError,match='REVIEW_WINDOW_NONPOSITIVE'):
        review_anchor_time({'start':'2026-01-01T01:00:00','end':'2026-01-01T01:00:00'})
    with pytest.raises(ASOCSBlindFirewallError,match='REVIEW_BAR_INTERVAL_START_MISSING'):
        overlay_visible_review_anchor('<svg></svg>',[{'open':'1'},{'interval_start':'2026-01-01T01:00:00'}],{'start':'2026-01-01T00:00:00','end':'2026-01-01T02:00:00'})

def test_blind_record_freezes_before_reveal_and_clarification_is_successor_only():
    base=freeze_blind_record({'case_id':'A','review_status':'REVIEWED','neutral_description':'Price rose, paused, then moved sideways.','confidence':'MODERATE','ambiguity':None,'structured_answers':{}})
    successor=successor_annotation(base,{'clarification':'Approximate turning area corrected.'})
    assert base['protocol_label']=='WITHIN_SINGLE_REVIEWER_PROTOCOL'
    assert base['frozen_before_reveal'] is True
    assert successor['predecessor_blind_record_sha256']==base['blind_record_sha256']
    assert successor['mutates_predecessor'] is False

def test_omission_states_are_explicit_and_not_silently_replaced():
    for state in ['UNREVIEWABLE_TECHNICAL','SOURCE_LIMITED','REVIEWER_DEFERRED']:
        record=freeze_blind_record({'case_id':'A','review_status':state})
        assert record['review_status']==state and record['frozen_before_reveal'] is True

def test_tradingview_is_secondary_and_cannot_override_primary():
    trace=tradingview_trace_record(case_id='A',trace_timestamp='2026-01-02T12:00:00',displayed_timezone='UNRESOLVED_DISPLAY_VALUE_TO_BE_RECORDED',feed_label='TO_BE_RECORDED',mismatch_class='TECHNICAL_UNAVAILABLE')
    assert trace['role']=='SECONDARY_TRACE_NAVIGATION_ONLY'
    assert trace['can_override_primary_adjudication'] is False

def test_wp7_infra_stops_before_human_review_and_g5():
    state=_json('records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_12_WP7_INFRA_QA_REVIEW.json')
    boundary=_json('docs/programmes/asocs-v0-1/implementation/wp7/ASOCSI_WP7_HUMAN_INPUT_BOUNDARY_v0_1.json')
    start=_json('docs/programmes/asocs-v0-1/implementation/wp7/ASOCSI_WP7_REVIEW_START_MANIFEST_v0_1.json')
    assert state['human_review_started'] is False and state['g5_status']=='NOT_STARTED'
    assert boundary['human_review_may_be_inferred_or_automated'] is False
    assert start['prerequisite_g4']['presentation_count']==370 and start['prerequisite_g4']['hidden_repeat_count']==18
    assert start['primary_surface']['renderer_id']=='ASOCS.SOURCE_NATIVE.SVG.CANDLE.v0.1'

def test_wp7_infra_closeout_passes_without_starting_human_review():
    qa=_json('docs/programmes/asocs-v0-1/implementation/wp7/ASOCSI_WP7_INFRA_QA_PACKET_v0_2.json')
    state=_json('records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_13_WP7_INFRA_COMPLETED.json')
    pointer=_json('registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json')
    assert qa['qa_recommendation']=='PASS' and qa['blocking_findings']==[]
    assert qa['repository_assurance']['repository_tests']=='PASS'
    assert qa['repository_assurance']['vit_routing']=='PASS'
    assert qa['repository_assurance']['siq_ready']=='PASS'
    assert qa['repository_assurance']['merge_readiness']=='PASS'
    assert qa['human_review_started'] is False and qa['g5_status']=='NOT_STARTED'
    assert state['status']=='COMPLETED' and state['infra_completed'] is True
    assert state['human_review_started'] is False and state['g5_status']=='NOT_STARTED'
    assert state['next_packet']=='ASOCSI-WP7-HUMAN-REVIEW_REQUIRES_HUMAN_INPUT'
    assert pointer['current_state'].endswith('ASOCSI_PROGRAMME_STATE_v0_13_WP7_INFRA_COMPLETED.json')
    assert pointer['status']=='COMPLETED'
    assert pointer['next_packet']=='ASOCSI-WP7-HUMAN-REVIEW_REQUIRES_HUMAN_INPUT'
