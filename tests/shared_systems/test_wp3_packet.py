from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROGRAMME=ROOT/"docs/programmes/shared-systems-v0-1"

def load(path:Path)->dict: return json.loads(path.read_text(encoding="utf-8"))

def test_g2_exact_completion_unlocks_wp3()->None:
    b=load(PROGRAMME/"wp3/SHSI_G2_COMPLETION_BINDING_v0_1.json")
    assert b["status"]=="COMPLETED" and b["main_tree"]==b["qualified_candidate_tree"]
    assert b["physical_completion"]["exact_tree_equal"] and b["physical_completion"]["four_content_addressed_receipts_present"]

def test_precedents_are_exact_and_nonmutated()->None:
    census=load(PROGRAMME/"wp3/SHSI_WP3_PRECEDENT_CENSUS_v0_1.json")
    assert {x["owner"] for x in census["sources"]}=={"DSAI","C2E","C2P","C2.5"}
    assert census["mutated_source_contracts"]==[] and census["scientific_runs_executed"]==0
    for source in census["sources"]:
        sha=subprocess.run(["git","hash-object","--",source["path"]],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
        assert sha==source["git_blob_sha"]

def test_wp3_state_gate_and_schema_are_non_authorising()->None:
    pointer=load(ROOT/"registries/implementation/shared_systems_v0_1/CURRENT_STATE_POINTER.json")
    assert (pointer["current_packet"],pointer["current_gate"],pointer["next_packet"])==("SHSI-WP3","SHSI-G3","SHSI-WP4")
    state=load(ROOT/pointer["state_record"])
    assert state["schema"]=="ovc-native-programme-state/v1" and state["authority_delta"]=="NONE"
    gate=load(PROGRAMME/"gates/SHSI_G3_EXECUTION_CLOSEOUT_v0_1.json")
    assert gate["execution_class"]=="AUTO_RATIFIABLE" and gate["authority_effect"]=="NONE"
    schema=load(ROOT/"schemas/shared_systems/execution_replay_kernel_v0_1.schema.json")
    expected={"SemanticGenerationRef","RunSpecification","ExecutionEnvironmentManifest","RunExecutionManifest","LogicalResultIdentity","ReplayResultManifest","CheckpointReceipt","CapacityReceipt"}
    assert expected<=set(schema["$defs"])

def test_wp3_vit_payload_is_content_addressed()->None:
    from ovc.development.identity import canonical_sha256
    vit=PROGRAMME/"vit"; authority=load(vit/"SHSI_WP3_AUTHORITY_MANIFEST_v0_1.json"); frontier=load(vit/"SHSI_WP3_DEPENDENCY_FRONTIER_v0_1.json"); pip=load(vit/"SHSI_WP3_PIP_v0_1.json")
    assert authority["logical_id"]==canonical_sha256(authority["payload"]); assert frontier["logical_id"]==canonical_sha256(frontier["payload"]); assert pip["logical_id"]==canonical_sha256(pip["payload"])
    assert pip["payload"]["authority_manifest_id"]==authority["logical_id"] and pip["payload"]["dependency_frontier_id"]==frontier["logical_id"]
    assert pip["payload"]["completion_transition"]=={"status":"COMPLETED","next_packet":"SHSI-WP4"}
    for change in pip["payload"]["logical_changes"]:
        sha=subprocess.run(["git","hash-object","--",change["path"]],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip(); assert sha==change["blob_sha"],change["path"]
