#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

PROGRAMME="OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE"
PLAN="OVC-GRT-V0.2-RCCC-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-REVISED-RATIFIED"
OLD_REF="origin/grt2/g3-activation-materialisation-20260823-final"
OLD_HASH="f008cbad6bbb891b18f615aa91f9981fbf71ec874972630d8c6eb38ae1642ba9"
NEW_HASH="c99fd885b27861c920aea3bec1b849ed928be771c4ce5c51dbff4ef2da0e8fa5"
CONST="cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0"
GATE_IDENTITY="7258dd4f626eac8235b4ca285b5a5057d196a5f5d403c6c7daea85a1aee1b4f2"
OLD_DECISION_ID="cde2d3ce74d1ed1a7ce8a8a608caf016e3590e9945e8a85e952c6124bd8767d3"
GATE_MERGE="903029e35cf2503e76a27418247b952307b7af77"
GATE_TREE="866ce0990deac9b15d3dd7be09d660055daaeb70"
GATE_PATH="docs/programmes/grt-v0-2/g3/superseding/GRT2_G3_SUPERSEDING_GATE_READY_DECISION_PACKET.json"
FLOOR_PATH="docs/programmes/grt-v0-2/g3/superseding/GRT2_G3_SUPERSEDING_PROPOSED_DEBT_FLOOR_GENERATION_0.json"
DECISION_PATH="docs/programmes/grt-v0-2/g3/GRT2_G3_OPERATOR_DECISION.json"
APPROVED_AT="2026-08-25T12:53:00+01:00"


def cj(v):
    if v is None:return "null"
    if v is True:return "true"
    if v is False:return "false"
    if isinstance(v,int):return str(v)
    if isinstance(v,float):
        s=format(v,'.15g'); return s
    if isinstance(v,str):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
    if isinstance(v,dict):return '{'+','.join(cj(k)+':'+cj(v[k]) for k in sorted(v))+'}'
    if isinstance(v,(list,tuple)):return '['+','.join(cj(x) for x in v)+']'
    raise TypeError(type(v))

def h(v): return hashlib.sha256(cj(v).encode()).hexdigest()
def hashed(v):
    v=dict(v); v.pop('logical_sha256',None); v['logical_sha256']=h(v); return v

def git(*a): return subprocess.check_output(['git',*a],text=True).strip()
def show(ref,path): return subprocess.check_output(['git','show',f'{ref}:{path}'],text=True)
def write(root,path,text):
    p=root/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding='utf-8')
def write_json(root,path,obj): write(root,path,json.dumps(obj,indent=2,sort_keys=True)+'\n')

def replace_common(text):
    return (text.replace(OLD_HASH,NEW_HASH)
        .replace('1628','1641')
        .replace('2026-08-23T16:55:00+01:00',APPROVED_AT)
        .replace('OVC APPROVE GRT2-G3"','OVC APPROVE GRT2-G3 SUPERSEDING PASS"')
        .replace('0287c81400c3a2536096b2a1691d5486096e87b0',GATE_MERGE)
        .replace('6818abb770c8878af286b011448304c6cc737ff6',GATE_TREE)
        .replace('docs/programmes/grt-v0-2/g3/GRT2_G3_GATE_READY_DECISION_PACKET.json',GATE_PATH)
        .replace('docs/programmes/grt-v0-2/g3/GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json',FLOOR_PATH))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--revalidation-run-id',type=int,required=True); ap.add_argument('--revalidation-artifact-id',type=int,required=True); ap.add_argument('--revalidation-artifact-digest',required=True); ap.add_argument('--revalidation-evidence-sha256',required=True); args=ap.parse_args()
    root=Path(args.root).resolve(); base=git('rev-parse','origin/main'); tree=git('rev-parse',f'{base}^{{tree}}')
    floor_text=show('origin/main',FLOOR_PATH); floor=json.loads(floor_text)
    assert floor['floor_hash']==NEW_HASH and floor['generation']==0 and len(floor['open_grandfathered_findings'])==1641

    # Reuse the qualified runtime implementation; bind it to the superseding floor.
    runtime=replace_common(show(OLD_REF,'scripts/governance/grt_v0_2/grt_exact.py'))
    write(root,'scripts/governance/grt_v0_2/grt_exact.py',runtime)
    write(root,'scripts/governance/grt_v0_2/grt_integration_readiness.py',show(OLD_REF,'scripts/governance/grt_v0_2/grt_integration_readiness.py'))
    write(root,'scripts/governance/grt_v0_2/prepare_next_debt_floor.py',show(OLD_REF,'scripts/governance/grt_v0_2/prepare_next_debt_floor.py'))
    write(root,'registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G0.json',floor_text)

    # Canonical operator decision against the exact repository-effective superseding packet.
    decision=hashed({
      'schema':'ovc-grt2-g3-operator-decision/v1','programme_id':PROGRAMME,'plan_id':PLAN,'plan_version':'0.2_REVISED_RATIFIED','gate_id':'GRT2-G3','decision':'PASS','decision_class':'OPERATOR_REQUIRED_AUTHORITY_CHANGE','decided_at':APPROVED_AT,'operator_instruction':'OVC APPROVE GRT2-G3 SUPERSEDING PASS','gate_ready_merge_commit':GATE_MERGE,'gate_ready_merge_tree':GATE_TREE,'gate_ready_packet':GATE_PATH,'approved_gate_decision_identity':GATE_IDENTITY,'supersedes_unconsumed_decision_identity':OLD_DECISION_ID,'approved_activation_predecessor_policy':'REVALIDATE_CURRENT_MAIN_AND_EXACT_PROPOSED_FLOOR_BEFORE_MATERIALISATION','approved_authority_delta':{'repository_constitution':{'version':'0.2','canonical_hash':CONST,'transition':'PROPOSED_UNADMITTED_TO_ACTIVE'},'debt_floor':{'generation':0,'floor_hash':NEW_HASH,'transition':'ABSENT_TO_ACTIVE_GENERATION_0'},'enforcement':{'transition':'LIMITED_NEW_ARTIFACT_ENFORCEMENT_TO_FULL_GRT_EXACT','required_assurance':'GRT-EXACT'}},'explicitly_unchanged':['immutable B0 membership and 569 count','Programme Genesis adoption authority','owner assignments','constitutional semantics GRT2-D1..D433','market, scientific, Validation, publication, probability, risk, exposure, execution and agent-write authority'],'next_action':'REVALIDATE_EXACT_CURRENT_MAIN_AND_PROPOSED_FLOOR_THEN_MATERIALISE_ATOMIC_G3_ACTIVATION','rollback':'OPERATOR_GOVERNED_CORRECT_FORWARD_ONLY_NO_FORCE_PUSH_NO_HISTORY_REWRITE'})
    write_json(root,DECISION_PATH,decision)

    authority=hashed({'schema':'ovc-grt2-active-enforcement-authority/v0_2','programme_id':PROGRAMME,'plan_id':PLAN,'gate_id':'GRT2-G3','approved_at':APPROVED_AT,'authority_status':'ACTIVE_ON_MAIN_MATERIALISATION','g3_status':'APPROVED_OPERATOR_PASS_ACTIVE_ON_MAIN_MATERIALISATION','constitution_id':'OVC-GRT-REPOSITORY-CONSTITUTION-v0.2','constitution_hash':CONST,'constitution_status':'ACTIVE','rule_bundle_id':'GRT_RULE_BUNDLE_v0_2','rule_bundle_hash':'7d6c38a3a018f257d0a05f6cfaf0a3082b42f825c2c36335d64544432a960979','debt_floor_generation':0,'debt_floor_hash':NEW_HASH,'debt_floor_definition':'registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G0.json','enforcement_mode':'FULL_GRT_EXACT','required_integration_assurance':'GRT-EXACT','no_new_hygiene_debt_required':True,'decision_record':DECISION_PATH,'prior_authority_record':'registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_1.json','effective_condition':'THIS_RECORD_AND_EXACT_GENERATION_0_FLOOR_PRESENT_ON_PROTECTED_MAIN_AFTER_GRT_EXACT_PASS','rollback_requires_operator_decision':True,'authority_exclusions':['Programme Genesis adoption authority','owner reassignment','constitutional semantic amendment','market or scientific authority','Validation or publication authority','probability, risk, exposure, trading, execution or agent-write authority']})
    write_json(root,'registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_2.json',authority)

    pointer=hashed({'schema':'ovc-grt2-debt-floor-current-pointer/v1','programme_id':PROGRAMME,'status':'ACTIVE_ON_MAIN_MATERIALISATION','generation':0,'floor_hash':NEW_HASH,'definition':'registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G0.json','constitution_hash':CONST,'activation_decision':DECISION_PATH,'effective_condition':'THIS_POINTER_AND_GENERATION_FILE_PRESENT_ON_PROTECTED_MAIN_AFTER_GRT_EXACT_PASS'})
    write_json(root,'registries/governance/grt_v0_2/GRT_DEBT_FLOOR_CURRENT.json',pointer)

    reval=hashed({'schema':'ovc-grt2-g3-activation-revalidation/v1','programme_id':PROGRAMME,'gate_id':'GRT2-G3','status':'PASS_EXACT_SUPERSEDING_FLOOR_SET_REPRODUCED','operator_decision':'PASS','decision_record':DECISION_PATH,'approved_floor_generation':0,'approved_floor_hash':NEW_HASH,'approved_floor_member_count':1641,'activation_floor_path':'registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G0.json','activation_predecessor_binding':'LATE_PHYSICAL_PLACEMENT_CURRENT_PROTECTED_MAIN_AT_FINAL_INTEGRATION','main_movement_policy':'ANY_POST_GATE_READY_MAIN_MOVEMENT_REQUIRES_EXACT_LATE_BOUND_GRT_REVALIDATION','revalidation_mechanism':'GRT-EXACT_BASE_AND_CANDIDATE_SNAPSHOTS_MUST_EQUAL_APPROVED_GENERATION_0_FLOOR','gate_ready_commit':GATE_MERGE,'gate_ready_tree':GATE_TREE,'superseding_gate_decision_identity':GATE_IDENTITY,'revalidated_protected_main':base,'revalidated_protected_tree':tree,'approved_missing_from_current_count':0,'current_not_in_approved_count':0,'b0_exact':True,'unresolved_lineage_count':0,'workflow_run_id':args.revalidation_run_id,'artifact_id':args.revalidation_artifact_id,'artifact_digest':args.revalidation_artifact_digest,'evidence_file_sha256':args.revalidation_evidence_sha256,'pre_g3_current_state_pointer_policy':'PRESERVE_FOR_WP4_WAVE_A_REMEDIATION','authority_effect':'NONE_REVALIDATION_ONLY'})
    write_json(root,'docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_REVALIDATION.json',reval)

    transaction=hashed({'schema':'ovc-grt2-g3-activation-transaction/v1','programme_id':PROGRAMME,'gate_id':'GRT2-G3','packet_id':'GRT2-G3-SUPERSEDING-ACTIVATION-MATERIALISATION','status':'APPROVED_PENDING_EXACT_PROOF_AND_MAIN_MATERIALISATION','operator_decision':'PASS','decision_record':DECISION_PATH,'activation_predecessor_binding':'LATE_PHYSICAL_PLACEMENT_CURRENT_PROTECTED_MAIN_AT_FINAL_INTEGRATION','activation_effect_on_protected_main':{'repository_constitution':'ACTIVE_BY_G3_AUTHORITY_BINDING','debt_floor_generation':0,'debt_floor_hash':NEW_HASH,'debt_floor_definition':'registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G0.json','enforcement':'FULL_GRT_EXACT','no_new_hygiene_debt_required':True,'post_g3_stabilization':'START'},'required_pre_merge_proof':{'profile':'GRT-EXACT','base_floor_hash':NEW_HASH,'base_floor_member_count':1641,'base_snapshot_must_equal_approved_floor':True,'candidate_snapshot_must_equal_generation_0_floor':True,'candidate_new_or_expanded_debt_must_equal':0},'current_state_projection':{'pre_g3_pointer_preserved':True,'reason':'AVOID_CONVERTING_INHERITED_CURRENT_STATE_DEBT_INTO_A_NEW_PATH_IDENTITY_DURING_G3_ACTIVATION','authority_source':'GRT2-WP4 Wave A current governance truth','required_remediation_packet':'GRT2-WP4'},'next_packet':'GRT2-WP4','wp5_interlock':'FORBIDDEN_UNTIL_GRT2_G4_PASS','rollback':'FAIL_CLOSED; CORRECT_FORWARD; OPERATOR_REQUIRED_TO_SUSPEND_OR_CHANGE_ACTIVE_CONSTITUTION'})
    write_json(root,'docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_TRANSACTION.json',transaction)

    qa=hashed({'schema':'ovc-grt2-g3-activation-qa/v1','programme_id':PROGRAMME,'status':'PASS_PENDING_REMOTE_EXACT_ASSURANCE','operator_decision':'PASS','operator_decision_record':DECISION_PATH,'constitution_hash':CONST,'candidate_floor_generation':0,'candidate_floor_hash':NEW_HASH,'unresolved_issues':[],'warnings':['Any protected-main movement after exact set revalidation requires fresh GRT-EXACT late binding.','The pre-G3 CURRENT_STATE_POINTER remains inherited until GRT2-WP4 Wave A; activation authority is recorded separately to avoid manufacturing a current-state finding at G3.']})
    write_json(root,'docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_QA_PACKET.json',qa)

    rollback=hashed({'schema':'ovc-grt2-g3-rollback-bundle/v1','programme_id':PROGRAMME,'gate_id':'GRT2-G3','status':'PRESTAGED','operator_decision_record':DECISION_PATH,'predecessor_authority_record':'registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_1.json','predecessor_enforcement':'LIMITED_NEW_ARTIFACT_ENFORCEMENT','active_constitution_hash':CONST,'active_floor_generation':0,'active_floor_hash':NEW_HASH,'fail_closed_mode':'BLOCK_NORMAL_INTEGRATIONS','constitution_change_policy':'OPERATOR_RESERVED_FORWARD_AMENDMENT_OR_EXPLICIT_ENFORCEMENT_SUSPENDED_INCIDENT','runtime_defect_policy':'ONLY_SAME_CONSTITUTION_QUALIFIED_ENFORCEMENT_RUNTIME_MAY_REPLACE_ACTIVE_RUNTIME','same_constitution_qualified_rollback_runtime':None,'forbidden':['force-push','history rewrite','B0 rewrite','silent downgrade to advisory','silent DebtFloor rewrite']})
    write_json(root,'docs/programmes/grt-v0-2/g3/GRT2_G3_ROLLBACK_BUNDLE.json',rollback)
    stabilization=hashed({'schema':'ovc-grt2-post-g3-stabilization-ledger/v1','programme_id':PROGRAMME,'gate_id':'GRT2-G3','activation_decision':DECISION_PATH,'activation_merge_commit':None,'activation_merge_tree':None,'started_at':None,'ends_not_before':None,'duration_calendar_days':30,'status':'STARTS_ON_G3_ACTIVATION_MERGE','entries':[],'review_cadence':{'days_1_to_7':'ONE_EVIDENCE_REVIEW_PER_CALENDAR_DAY','days_8_to_30':'AT_LEAST_ONE_REVIEW_PER_7_DAY_INTERVAL','incident':'IMMEDIATE_REVIEW'},'authority_effect':'NONE_MONITORING_LEDGER_ONLY'})
    write_json(root,'docs/programmes/grt-v0-2/g3/GRT2_POST_G3_STABILIZATION_LEDGER.json',stabilization)

    # VIT authority/frontier bindings.
    manifest={'plan_id':PLAN,'packet_id':'GRT2-G3-SUPERSEDING-ACTIVATION-MATERIALISATION','gate_id':'GRT2-G3','authority_class':'AUTO_EXECUTABLE','authority_delta':'NONE','authority_sources':[GATE_PATH,DECISION_PATH],'reserved_boundaries':['CONSTITUTION_SEMANTIC_AMENDMENT','ENFORCEMENT_SUSPENDED_INCIDENT','DESTRUCTIVE_OR_HISTORY_REWRITE'],'security_envelope_id':None}
    mid=h(manifest); write_json(root,'docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_AUTHORITY_MANIFEST.json',{'schema':'ovc-integration-authority-manifest-binding/v0_1','authority_manifest':manifest,'authority_manifest_id':mid})
    frontier={'dependencies':sorted(['DSAI-VIT-SIQ-PHYSICAL-INTEGRATION',f'GRT2-DEBTFLOOR-SUPERSEDING-GENERATION-0:{NEW_HASH}',f'GRT2-G3-SUPERSEDING-GATE-READY:{GATE_IDENTITY}','GRT2-G3-SUPERSEDING-OPERATOR-DECISION-PASS']),'predecessor_requirement':'PHYSICAL_MATERIALISATION_REQUIRED','owner_bindings':sorted(['OVC-DSAI-VIT-v0.3',PROGRAMME])}
    fid=h(frontier); write_json(root,'docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_DEPENDENCY_FRONTIER.json',{'schema':'ovc-dependency-frontier-binding/v0_1','dependency_frontier':frontier,'dependency_frontier_id':fid})

    state=hashed({'schema':'ovc-grt2-programme-state/v1','programme_id':PROGRAMME,'plan_id':PLAN,'plan_version':'0.2_REVISED_RATIFIED','packet_id':'GRT2-G3-SUPERSEDING-ACTIVATION-MATERIALISATION','gate_id':'GRT2-G3','status':'APPROVED_PENDING_MAIN_MATERIALISATION','operator_decision':'PASS','operator_decision_required':False,'operator_decision_record':DECISION_PATH,'approved_at':APPROVED_AT,'authority_effect':'OPERATOR_APPROVED_G3_ACTIVATION','baseline_commit':base,'baseline_tree':tree,'gate_ready_commit':GATE_MERGE,'gate_ready_tree':GATE_TREE,'constitution_hash':CONST,'constitution_status':'ACTIVE_ON_MAIN_MATERIALISATION','debt_floor_generation':0,'debt_floor_hash':NEW_HASH,'debt_floor_definition':'registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G0.json','active_enforcement':'FULL_GRT_EXACT_ON_MAIN_MATERIALISATION','g3_status':'APPROVED_OPERATOR_PASS_PENDING_EXACT_ACTIVATION_MATERIALISATION','activation_revalidation':'docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_REVALIDATION.json','post_g3_stabilization':'docs/programmes/grt-v0-2/g3/GRT2_POST_G3_STABILIZATION_LEDGER.json','current_projection_status':'PRE_G3_POINTER_INTENTIONALLY_PRESERVED_AS_INHERITED_STALE_STATE_FOR_WP4_WAVE_A','next_packet':'GRT2-WP4','next_gate':'GRT2-G4','next_action':'AFTER_G3_ACTIVATION_MERGE_START_GRT2_WP4_WAVE_A_CURRENT_GOVERNANCE_TRUTH','blockers':[],'unresolved_issues':[]})
    write_json(root,'registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_17_SUPERSEDING_ACTIVATION.json',state)

    readme='''# GRT2-G3 superseding activation materialisation\n\nThis packet records the exact operator-approved `GRT2-G3 SUPERSEDING PASS` and materialises only the ratified transition from limited G2.5 enforcement to full GRT v0.2 exact constitutional enforcement. The exact approved generation-0 floor contains 1,641 finding IDs and has hash `c99fd885b27861c920aea3bec1b849ed928be771c4ce5c51dbff4ef2da0e8fa5`.\n\nIt does not amend constitutional semantics, infer Programme Genesis adoption, reassign ownership, publish scientific or market artifacts, grant probability/risk/exposure/execution authority, rewrite B0, or rewrite history. `GRT-EXACT` must prove the exact current protected-main predecessor and prospective activation tree reproduce the approved finding set before materialisation.\n'''
    write(root,'docs/programmes/grt-v0-2/g3/README_GRT2_G3_ACTIVATION.md',readme)

    # Preserve current workflow semantics and insert GRT-EXACT only into the existing serialized integration lane.
    wp=root/'.github/workflows/ovc-tiered-tests.yml'; text=wp.read_text(encoding='utf-8')
    text=text.replace('    timeout-minutes: 10\n    concurrency:\n      group: ovc-main-integration-lane-v1','    timeout-minutes: 45\n    concurrency:\n      group: ovc-main-integration-lane-v1',1)
    text=text.replace('      admission_receipt_id: ${{ steps.finalize.outputs.admission_receipt_id }}\n    steps:','      admission_receipt_id: ${{ steps.finalize.outputs.admission_receipt_id }}\n      grt_exact_proof_id: ${{ steps.grt-exact.outputs.proof_id }}\n    steps:',1)
    marker='      - name: Run mandatory SIQ/PDC exact-final assurance inside lease\n'
    grt='''      - name: Run required GRT-EXACT against the exact late-bound integration tree\n        id: grt-exact\n        shell: bash\n        env:\n          OVC_GRT_BASE_SHA: ${{ steps.acquire.outputs.base_sha }}\n          OVC_GRT_CANDIDATE_HEAD_SHA: ${{ steps.acquire.outputs.candidate_head_sha }}\n          PYTHONPATH: src:.\n        run: |\n          set -euo pipefail\n          python3 scripts/governance/grt_v0_2/grt_exact.py --base "${OVC_GRT_BASE_SHA}" --head "${OVC_GRT_CANDIDATE_HEAD_SHA}" --output artifacts/grt2-g3/grt-exact.json\n          proof_id=$(python3 -c "import json; p=json.load(open('artifacts/grt2-g3/grt-exact.json')); assert p['result']=='PASS'; print(p['logical_sha256'])")\n          test "${#proof_id}" -eq 64\n          echo "proof_id=${proof_id}" >> "$GITHUB_OUTPUT"\n      - name: Upload immutable GRT-EXACT evidence\n        if: always()\n        uses: actions/upload-artifact@v4\n        with:\n          name: grt-exact-proof\n          path: artifacts/grt2-g3/grt-exact.json\n          if-no-files-found: error\n          retention-days: 30\n'''
    if 'Run required GRT-EXACT against the exact late-bound integration tree' not in text: text=text.replace(marker,grt+marker,1)
    marker2='      - name: Bind exact late-placement IntegrationAdmissionReceipt\n'
    ready='''      - name: Run lightweight GRT integration readiness\n        shell: bash\n        env:\n          OVC_GRT_PROOF_PATH: artifacts/grt2-g3/grt-exact.json\n          OVC_GRT_PROOF_ID: ${{ steps.grt-exact.outputs.proof_id }}\n          OVC_GRT_BASE_SHA: ${{ steps.acquire.outputs.base_sha }}\n          OVC_GRT_HEAD_SHA: ${{ steps.acquire.outputs.candidate_head_sha }}\n          OVC_GRT_PLACEMENT_TREE_SHA: ${{ steps.acquire.outputs.placement_tree_sha }}\n          PYTHONPATH: src:.\n        run: python3 scripts/governance/grt_v0_2/grt_integration_readiness.py\n'''
    if 'Run lightweight GRT integration readiness' not in text: text=text.replace(marker2,ready+marker2,1)
    wp.write_text(text,encoding='utf-8')

    # Focused constitutional activation regression.
    test=f'''from __future__ import annotations\nimport json\nfrom pathlib import Path\nfrom ovc.programme_genesis.grt_v0_2.debt import validate_debt_floor\nfrom ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256\nROOT=Path(__file__).resolve().parents[3]; G3=ROOT/"docs/programmes/grt-v0-2/g3"; GOV=ROOT/"registries/governance/grt_v0_2"\ndef load(p): return json.loads(p.read_text())\ndef check(r):\n p=dict(r); x=p.pop("logical_sha256"); assert x==canonical_sha256(p)\ndef test_superseding_operator_pass_exact():\n d=load(G3/"GRT2_G3_OPERATOR_DECISION.json"); check(d); assert d["operator_instruction"]=="OVC APPROVE GRT2-G3 SUPERSEDING PASS"; assert d["approved_gate_decision_identity"]=="{GATE_IDENTITY}"; assert d["approved_authority_delta"]["debt_floor"]["floor_hash"]=="{NEW_HASH}"\ndef test_active_floor_is_exact_approved_superseding_object():\n proposed=load(ROOT/"{FLOOR_PATH}"); active=load(GOV/"debt_floors/GRT_DEBT_FLOOR_G0.json"); ptr=load(GOV/"GRT_DEBT_FLOOR_CURRENT.json"); assert active==proposed; validate_debt_floor(active); assert len(active["open_grandfathered_findings"])==1641; assert active["floor_hash"]=="{NEW_HASH}"; check(ptr); assert ptr["floor_hash"]==active["floor_hash"]\ndef test_authority_exact_and_non_grt_denials_preserved():\n a=load(ROOT/"registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_2.json"); check(a); assert a["enforcement_mode"]=="FULL_GRT_EXACT"; assert a["constitution_status"]=="ACTIVE"; assert a["no_new_hygiene_debt_required"] is True; assert "Programme Genesis adoption authority" in a["authority_exclusions"]; assert "probability, risk, exposure, trading, execution or agent-write authority" in a["authority_exclusions"]\ndef test_activation_state_stops_pointer_churn_until_wp4():\n s=load(ROOT/"registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_17_SUPERSEDING_ACTIVATION.json"); check(s); ptr=load(ROOT/"registries/implementation/grt_v0_2/CURRENT_STATE_POINTER.json"); assert s["next_packet"]=="GRT2-WP4" and s["next_gate"]=="GRT2-G4"; assert ptr["current_state"].endswith("OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json")\ndef test_revalidation_and_serialized_exact_lane():\n r=load(G3/"GRT2_G3_ACTIVATION_REVALIDATION.json"); check(r); assert r["approved_floor_member_count"]==1641 and r["approved_missing_from_current_count"]==0 and r["current_not_in_approved_count"]==0 and r["b0_exact"] is True and r["unresolved_lineage_count"]==0; w=(ROOT/".github/workflows/ovc-tiered-tests.yml").read_text(); assert "group: ovc-main-integration-lane-v1" in w; assert "Run required GRT-EXACT against the exact late-bound integration tree" in w; assert "Run mandatory SIQ/PDC exact-final assurance inside lease" in w; assert "Run lightweight GRT integration readiness" in w\n'''
    write(root,'tests/governance/grt_v0_2/test_grt2_g3_operator_pass.py',test)
    meta={'base_commit':base,'base_tree':tree,'authority_manifest_id':mid,'dependency_frontier_id':fid,'changed_files':['.github/workflows/ovc-tiered-tests.yml','docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_AUTHORITY_MANIFEST.json','docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_DEPENDENCY_FRONTIER.json','docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_QA_PACKET.json','docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_REVALIDATION.json','docs/programmes/grt-v0-2/g3/GRT2_G3_ACTIVATION_TRANSACTION.json','docs/programmes/grt-v0-2/g3/GRT2_G3_OPERATOR_DECISION.json','docs/programmes/grt-v0-2/g3/GRT2_G3_ROLLBACK_BUNDLE.json','docs/programmes/grt-v0-2/g3/GRT2_POST_G3_STABILIZATION_LEDGER.json','docs/programmes/grt-v0-2/g3/README_GRT2_G3_ACTIVATION.md','registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_2.json','registries/governance/grt_v0_2/GRT_DEBT_FLOOR_CURRENT.json','registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G0.json','registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_17_SUPERSEDING_ACTIVATION.json','scripts/governance/grt_v0_2/grt_exact.py','scripts/governance/grt_v0_2/grt_integration_readiness.py','scripts/governance/grt_v0_2/prepare_next_debt_floor.py','tests/governance/grt_v0_2/test_grt2_g3_operator_pass.py']}
    Path('/tmp/grt2-g3-superseding-activation-meta.json').write_text(json.dumps(meta,sort_keys=True))
    print(json.dumps(meta,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
