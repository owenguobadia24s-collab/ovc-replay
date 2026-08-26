from pathlib import Path
import hashlib, json

ROOT=Path(__file__).resolve().parents[3]
WP8=ROOT/'docs/programmes/asocs-v0-1/implementation/wp8'

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def test_c1_case_narrative_supersession_court_record():
    sup=load(WP8/'ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_SUPERSESSION_v0_1.json')
    assert sup['supersession_type']=='FORWARD_SUPERSESSION_OF_REQUIRED_HUMAN_REVIEW_ROUTE_ONLY'
    assert sup['historical_route']['status']=='COMPLETED_IMMUTABLE_HISTORICAL_TECHNICAL_EVIDENCE'
    assert sup['historical_route']['human_completion_required'] is False
    assert sup['historical_route']['mutated'] is False
    assert sup['required_route']['route']=='C1_CASE_NARRATIVE_FIDELITY'
    assert sup['required_route']['review_unit']=='ONE_CASE_LEVEL_JUDGEMENT_PER_CASE'
    assert sup['required_route']['per_candle_human_judgement'] is False
    assert sup['stage2_reveal_started'] is False

def test_historical_stage1_machine_inputs_remain_byte_identical():
    assert sha(WP8/'ASOCSI_WP8_S01_STAGE1_REVEAL_PACKET_v0_1.json')=='5ae775fd5ac9ad5afcecec4f57f3b3fb4fdb5d1d25e2a8d1d9769fde1c52f5c7'
    assert sha(WP8/'ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT_TEMPLATE_v0_1.json')=='607b1d48137b01f3cbb9ea7ae737382fe6ee152497e412fcb725b6ae635b9c9b'
    old=load(WP8/'ASOCSI_WP8_S01_STAGE1_REVIEW_WORKBOOK_ARTIFACT_v0_1.json')
    assert old['sha256']=='4c4a2b6cccb8b2d4551ce6365fe82a6d04519f62cb90b61a004d22f3b739e2b4'

def test_case_sequence_index_exact_scope_and_upper_layer_firewall():
    idx=load(WP8/'ASOCSI_WP8_S01_STAGE1_C1_CASE_SEQUENCE_INDEX_v0_1.json')
    assert idx['case_count']==25 and len(idx['cases'])==25
    assert [c['presentation_ordinal'] for c in idx['cases']]==list(range(1,26))
    assert len({c['case_id'] for c in idx['cases'])==25
    assert all(set(c['navigation_window'])=={'local','development','wider'} for c in idx['cases'])
    assert idx['source_bindings']['source_sha256']=='210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2'
    assert idx['source_bindings']['g1_audit_15m_sha256']=='df060a22bf8a6c1d990d22af90e189848bd2c5f3090ef65a8c5637e4456bb7d9'
    assert idx['source_bindings']['wp7_frozen_workbook_sha256']=='19101e1e0a32b5d9c605ad3e21242b14e292c4a585c5a37edd1e9279b9b0005f'
    assert idx['aggregate_counts']['wider_union_bucket_count']==23343
    assert idx['aggregate_counts']['wider_union_complete_c1_count']==15335
    assert idx['upper_layer_evidence_included'] is False
    assert idx['stage2_reveal_started'] is False

def test_case_level_judgement_schema_and_blank_template():
    schema=load(ROOT/'schemas/research_operations/asocs/asocs_c1_case_narrative_fidelity_judgement_v0_1.schema.json')
    p=schema['properties']
    assert p['stage']['const']=='C1_CASE_NARRATIVE_FIDELITY'
    assert p['construct_survival_decision']['const']=='PROHIBITED_DURING_CASE_REVIEW'
    template=load(WP8/'ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_HUMAN_INPUT_TEMPLATE_v0_1.json')
    idx=load(WP8/'ASOCSI_WP8_S01_STAGE1_C1_CASE_SEQUENCE_INDEX_v0_1.json')
    assert [x['case_id'] for x in template['cases']]==[x['case_id'] for x in idx['cases']]
    for c in template['cases']:
        j=c['human_judgement']
        assert j['fidelity_disposition'] is None
        assert j['information_gap_disposition'] is None
        assert j['semantic_leakage'] is None
        assert j['traceability'] is None
        assert j['confidence'] is None
        assert j['observational_correspondence']==''
        assert j['notes']==''
        assert j['construct_survival_decision']=='PROHIBITED_DURING_CASE_REVIEW'

def test_external_artifact_bindings_and_review_contract():
    seq=load(WP8/'ASOCSI_WP8_S01_STAGE1_C1_CASE_SEQUENCE_REVEAL_ARTIFACT_v0_1.json')
    wb=load(WP8/'ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_REVIEW_WORKBOOK_ARTIFACT_v0_1.json')
    assert seq['drive_file_id']=='1ilj2J00TPXNlQgeXYuZgKgvBGs04e-5p'
    assert seq['sha256']=='7d0f9e48b7b1ccfd44e3c38820c7dba186d0864f1be03c593ed19526ddbda986'
    assert seq['byte_size']==21506443 and seq['authoritative_machine_record'] is True
    assert wb['drive_file_id']=='182Bqaip9mHWBTqjRo6A07WNv2NQXwHuk'
    assert wb['sha256']=='264e06a3c0c74b0034541c8c2aa9e54edd22bb6bd8ea9402498a313a41340c0d'
    assert wb['byte_size']==27542293
    c=wb['workbook_contract']
    assert c['per_candle_human_judgement'] is False
    assert c['human_response_prepopulation']=='NONE'
    assert c['stage2_reveal']=='NOT_CONSTRUCTED_NOT_REVEALED'
    assert wb['export']['filename']=='ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_HUMAN_INPUT.json'

def test_qa_decision_state_pointer_stop_at_human_input():
    qa=load(WP8/'ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_QA_v0_1.json')
    dec=load(WP8/'ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_DECISION_v0_1.json')
    st=load(ROOT/'records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_27_WP8_S01_STAGE1_C1_CASE_NARRATIVE_FIDELITY_SUPERSESSION_COMPLETED.json')
    effective=load(ROOT/'records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_28_WP8_S01_STAGE1_C1_CASE_NARRATIVE_FIDELITY_SUPERSESSION_REPOSITORY_EFFECTIVE.json')
    ptr=load(ROOT/'registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json')
    assert qa['qa_recommendation']=='PASS' and not qa['blocking_findings']
    assert dec['decision']=='PASS' and dec['authority_delta']=='NONE'
    assert dec['next_boundary']=='HUMAN_SCIENTIFIC_INPUT' and dec['stage2_reveal_started'] is False
    assert st['status']=='COMPLETED' and st['human_scientific_input_boundary'] is True
    assert st['required_human_input_started'] is False and st['human_adjudication_started'] is False
    assert st['stage2_reveal_started'] is False
    assert st['historical_single_anchor_human_completion_required'] is False
    assert effective['status']=='COMPLETED_REPOSITORY_EFFECTIVE'
    assert effective['merge_commit']=='6986acc3caf92c2fd3cdf32ed8460fe1bd858c06'
    assert effective['human_scientific_input_boundary'] is True
    assert effective['required_human_input_started'] is False and effective['human_adjudication_started'] is False
    assert effective['stage2_reveal_started'] is False
    assert ptr['current_state'].endswith('ASOCSI_PROGRAMME_STATE_v0_28_WP8_S01_STAGE1_C1_CASE_NARRATIVE_FIDELITY_SUPERSESSION_REPOSITORY_EFFECTIVE.json')
    assert ptr['status']=='COMPLETED_REPOSITORY_EFFECTIVE'
    assert ptr['next_packet']=='ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-HUMAN-ADJUDICATION'
