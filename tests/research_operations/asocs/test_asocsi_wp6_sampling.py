from __future__ import annotations
import hashlib, json
from pathlib import Path
from ovc.research_operations.asocs.sampling import blind_case_id, canonical_sha256, full_census_frame, select_frame, selection_score
ROOT=Path(__file__).resolve().parents[3]
def _json(p:str)->dict: return json.loads((ROOT/p).read_text(encoding='utf-8'))
POP='f'*64
NONCE='31aa07a7de93f1f70fa5b500eeae5159040965079e9bc11ab4ed1c43d93ea158'

def test_exact_hash_ranking_and_exhaustion():
    expected=hashlib.sha256((POP+NONCE+'S'+'A').encode()).hexdigest()
    assert selection_score(POP,NONCE,'S','A')==expected
    f=select_frame([{'object_id':'A'},{'object_id':'B'}],population_hash=POP,nonce_hex=NONCE,stratum_id='S',target_size=5)
    assert f['exhaustion']=='STRATUM_EXHAUSTED_FULL_CENSUS' and f['selection_count']==2

def test_full_census_nonnumeric_frame_has_no_hand_cut():
    f=full_census_frame([{'object_id':'A'},{'object_id':'B'}],population_hash=POP,nonce_hex=NONCE,stratum_id='NULL',reason='TEST')
    assert f['target_size']=='FULL_CENSUS' and f['selection_count']==f['eligible_count']==2

def test_primary_and_repeat_blind_ids_are_opaque_and_distinct():
    a=blind_case_id(POP,NONCE,'unit-1',repeat=False); b=blind_case_id(POP,NONCE,'unit-1',repeat=True)
    assert a.startswith('ASOCS.BLIND.') and b.startswith('ASOCS.BLIND.') and a!=b
    assert 'LEVEL' not in a and 'GAP' not in a and 'NULL' not in a

def test_pre_census_sampling_configuration_is_bound_to_repository_evidence():
    cfg=_json('registries/research_operations/asocs/ASOCSI_WP6_PREBUILD_SAMPLING_CONFIG_v0_1.json')
    prov=_json('docs/programmes/asocs-v0-1/implementation/wp6/ASOCSI_G4_PRE_CENSUS_CONFIG_PROVENANCE_v0_1.json')
    assert cfg['frozen_before_real_census_execution'] is True
    assert cfg['base_rate_anchor_target']==120 and cfg['gap_centered_minimum']==40
    assert cfg['hidden_repeat_fraction']==0.05 and cfg['default_session_cap_primary_anchor_equivalents']==25
    assert prov['pre_census_commit']=='4ea477362611d39f4c42a0152514d3794ca00658'
    assert prov['pre_census_config_blob_sha']=='67318bb80e3081937f869c2311f4b902a597fa26'

def test_real_g4_candidate_counts_hashes_and_fail_closed_scope():
    m=_json('docs/programmes/asocs-v0-1/implementation/wp6/ASOCSI_G4_SAMPLING_MANIFEST_v0_1.json')
    c=_json('docs/programmes/asocs-v0-1/implementation/wp6/ASOCSI_G4_SAMPLING_CANDIDATE_v0_1.json')
    assert m['sampling_manifest_id']=='33fa9aa81059d0bde9b9cc84da73336d3a20c7236610ccf5b3d8a8a5979e3a31'
    assert m['review_population_sha256']=='ff6eb37724aea5b2706666903f7b5a1bc063af8ef9026f4496429b5e33fa15fe'
    assert c['unique_review_unit_count']==352 and c['presentation_count']==370 and c['hidden_repeat_count']==18
    assert c['base_rate_selection_count']==120 and c['null_full_census_count']==193 and c['gap_centered_selection_count']==40
    assert c['upper_stack_review_scope']=='NOT_EVALUABLE_EXACT_ACTIVE_INTERFACE'
    assert c['human_review_started'] is c['tradingview_navigation_started'] is False
    frames={f['stratum_id']:f for f in m['frames']}
    assert all(frames[f'BASE_RATE_RANDOM_ANCHORS:2026-{month:02d}']['selection_count']==20 for month in range(1,7))
    assert frames['GAP_CENTERED_SOURCE_DISCONTINUITY']['selection_count']==40
    assert frames['C1_CONTINUITY_NULL']['selection_count']==193
    assert frames['C2E_EPISODE']['selection_count']==0 and frames['C2E_PHASE_MUTATION']['selection_count']==0

def test_external_artifact_contract_is_content_addressed_and_reproducibility_passed():
    m=_json('docs/programmes/asocs-v0-1/implementation/wp6/ASOCSI_G4_SAMPLING_MANIFEST_v0_1.json')
    arts=m['external_artifacts']
    assert arts['sampling_execution']['sha256']=='41614501c4b1b440275f0a8d79a951967838d50088b6f77d10bd3bcb4a3a5788'
    assert arts['review_population_reveal_index']['sha256']=='c62db28fe1fc40197f1a904295aaa8391bb78a49640136138431648df9e1dcac'
    assert arts['sampling_reproducibility']['sha256']=='fe3bdd9af2c48adf002d7cddf2087359a88da328186c39c2f68f86766ca98b11'

def test_wp6_remains_qa_review_before_g4_delegated_pass():
    state=_json('records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_10_WP6_QA_REVIEW.json')
    ptr=_json('registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json')
    qa=_json('docs/programmes/asocs-v0-1/implementation/wp6/ASOCSI_WP6_QA_PACKET_v0_1.json')
    assert state['status']==ptr['status']=='QA_REVIEW'
    assert state['gate_status']=='QA_REVIEW' and state['review_population_frozen'] is False
    assert qa['qa_recommendation']=='QA_REVIEW' and qa['repository_ci']=='PENDING'
    assert state['human_review_started'] is False
