import pytest

from ovc.development.prvit_remediation import ImmutableVITLineagePointer, IntegrationAssuranceGeneration, PRVITRemediationError, ShadowGRTProof, ShadowPlacement, TypedAssuranceResult, ancestry_disposition, build_post_materialisation_receipt, classify_main_movement, compare_legacy_and_shadow, evaluate_shadow_admission, semantic_dispatch_key

A="a"*64; B="b"*64; C="c"*64; D="d"*64; T1="1"*40; T2="2"*40; T3="3"*40

def assurance(state="PASS", required=True, run="run-1"):
    return TypedAssuranceResult("tests", state, B, f"evidence:{state}", required, run)
def placement(frontier=B):
    return ShadowPlacement(A, T1, T2, C, frontier)
def grt(tree=T2, state="PASS"):
    return ShadowGRTProof(tree, "proof", "grt-v0.2", state)

def test_prvit_r01_main_move_is_placement_only():
    d=classify_main_movement(same_pip=True, dependency_frontier_changed=False, authority_changed=False)
    assert d.disposition=="PLACEMENT_RECOMPUTE_ONLY" and d.a0_reuse_allowed and not d.payload_rebuild_required

def test_prvit_r02_invalid_placement_does_not_mutate_a0():
    a=assurance(); disp,reasons=evaluate_shadow_admission(pip_id=A, placement=placement(D), assurances=[a], grt=grt(), authority_manifest_id=C, dependency_frontier_id=B)
    assert a.state=="PASS" and disp=="BLOCK" and "PLACEMENT_FRONTIER_MISMATCH" in reasons

def test_prvit_r03_blocked_upstream_is_not_fail():
    a=assurance("BLOCKED_UPSTREAM"); disp,reasons=evaluate_shadow_admission(pip_id=A, placement=placement(), assurances=[a], grt=grt())
    assert a.state=="BLOCKED_UPSTREAM" and disp=="BLOCK" and any("BLOCKED_UPSTREAM" in r for r in reasons)

def test_prvit_r04_required_fail_blocks():
    assert evaluate_shadow_admission(pip_id=A, placement=placement(), assurances=[assurance("FAIL")], grt=grt())[0]=="BLOCK"

def test_prvit_r05_not_applicable_only_when_optional():
    assert evaluate_shadow_admission(pip_id=A, placement=placement(), assurances=[assurance("NOT_APPLICABLE", False)], grt=grt())[0]=="SHADOW_READY"
    with pytest.raises(PRVITRemediationError, match="REQUIRED_ASSURANCE_NOT_APPLICABLE"): assurance("NOT_APPLICABLE", True)

def test_prvit_r06_rerun_creates_new_generation():
    p=placement(); r1=assurance(run="run-1"); r2=assurance(run="run-2")
    g1=IntegrationAssuranceGeneration(A,T2,p.placement_id,T1,C,B,"policy-v1",(r1.result_id,),("run-1",))
    g2=IntegrationAssuranceGeneration(A,T2,p.placement_id,T1,C,B,"policy-v1",(r2.result_id,),("run-2",),g1.generation_id)
    assert g1.generation_id!=g2.generation_id and g2.supersedes_generation_id==g1.generation_id

def test_prvit_r07_pr_metadata_cannot_change_pointer():
    p1=ImmutableVITLineagePointer(A,"records/development/vit/lineage/a.json",B); p2=ImmutableVITLineagePointer(A,"records/development/vit/lineage/a.json",B)
    assert p1.pointer_id==p2.pointer_id

def test_prvit_r08_duplicate_dispatch_is_idempotent():
    key=semantic_dispatch_key("programme","packet",A)
    assert semantic_dispatch_key("programme","packet",A)==key and semantic_dispatch_key("programme","other",A)!=key

def test_prvit_r09_compare_api_cannot_override_git():
    assert ancestry_disposition(compare_api_status=404, local_git_ancestor=True)=="PASS_GIT_NATIVE"
    assert ancestry_disposition(compare_api_status=200, local_git_ancestor=False)=="FAIL_NOT_ANCESTOR"
    assert ancestry_disposition(compare_api_status=404, local_git_ancestor=None)=="NOT_EVALUABLE_GIT_PROOF_REQUIRED"

def test_prvit_r10_tree_mismatch_blocks():
    disp,reasons=evaluate_shadow_admission(pip_id=A, placement=placement(), assurances=[assurance()], grt=grt(T3))
    assert disp=="BLOCK" and "PROSPECTIVE_GRT_TREE_MISMATCH" in reasons
    with pytest.raises(PRVITRemediationError, match="POST_WRITE_TREE_MISMATCH"): build_post_materialisation_receipt(transaction_id="txn", pip_id=A, qualified_tree=T2, physical_commit=T3, physical_tree=T3, completed_packet="packet")

def test_shadow_only_allow_never_silently_authoritative():
    c=compare_legacy_and_shadow(legacy_allowed=False, shadow_disposition="SHADOW_READY")
    assert not c["equivalent"] and c["classification"]=="SHADOW_ONLY_ALLOW_REQUIRES_INVESTIGATION"
