from ovc.development.prvit_shadow import (ShadowPIPRecord, ShadowVITPlacement, ShadowGRTProofBinding, TypedAssuranceResult, classify_main_movement, evaluate_admission, semantic_dispatch_key)

AUTH='a'*64
DEP='d'*64

def fixture():
    pip=ShadowPIPRecord('P','W',(('x','ADD','h'),),AUTH,DEP)
    placement=ShadowVITPlacement(pip.pip_id,'tree0','tree1',AUTH,DEP)
    grt=ShadowGRTProofBinding('tree1','proof','constitution','PASS')
    assurance=[TypedAssuranceResult('AA0','PASS',DEP,'evidence')]
    return pip,placement,grt,assurance

def test_round_trip_and_admission():
    pip,placement,grt,assurance=fixture()
    assert len(pip.pip_id)==64
    assert evaluate_admission(pip,placement,assurance,grt)=='SHADOW_READY'

def test_invalid_frontier_blocks_without_changing_aa0():
    pip,_,grt,assurance=fixture()
    bad=ShadowVITPlacement(pip.pip_id,'tree0','tree1',AUTH,'e'*64)
    assert assurance[0].state=='PASS'
    assert evaluate_admission(pip,bad,assurance,grt)=='BLOCK'

def test_tree_mismatch_blocks():
    pip,placement,_,assurance=fixture()
    bad=ShadowGRTProofBinding('other','proof','constitution','PASS')
    assert evaluate_admission(pip,placement,assurance,bad)=='BLOCK'

def test_typed_blocked_upstream_is_not_fail():
    x=TypedAssuranceResult('A2','BLOCKED_UPSTREAM',DEP,'e')
    assert x.state=='BLOCKED_UPSTREAM'

def test_nonrequired_not_applicable_is_explicit():
    x=TypedAssuranceResult('IRRELEVANT','NOT_APPLICABLE',DEP,'e',required=False)
    assert x.state=='NOT_APPLICABLE'

def test_main_movement_classification():
    assert classify_main_movement(same_pip=True,same_dependency=True,same_authority=True)=='PLACEMENT_RECOMPUTE_ONLY'
    assert classify_main_movement(same_pip=True,same_dependency=False,same_authority=True)=='ASSURANCE_RENEWAL_REQUIRED'
    assert classify_main_movement(same_pip=True,same_dependency=True,same_authority=False)=='AUTHORITY_REVIEW_REQUIRED'

def test_semantic_dispatch_idempotency():
    pip,_,_,_=fixture()
    assert semantic_dispatch_key('P','W',pip.pip_id)==semantic_dispatch_key('P','W',pip.pip_id)
