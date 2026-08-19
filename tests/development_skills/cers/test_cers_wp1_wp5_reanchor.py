from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASELINE = "7fbba589f432ff02d8d1b6f717f3b4b071d57451"
AUTHORITY_ID = "4de5dc1e4aff2a6291180f5c899b102a92d9c03c297a435388f54d7eb87aae5e"
FRONTIER_ID = "e966a47e55de1a17f1ab9ee1d752dade72910e9a47a69ede517d255e6dd9e98c"

def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def canonical_id(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()

def test_grouped_authority_is_inactive_shadow_only_and_live_dispatch_denied():
    a=load("docs/releases/development-skills-v0-3/cers-conformance/wp1-wp5/CERS_WP1_WP5_AUTHORITY_MANIFEST_v0_1.json")
    assert canonical_id(a)==AUTHORITY_ID
    assert a["authority_delta"]=="INACTIVE_SHADOW_ONLY"
    assert a["live_unattended_dispatch"]=="DENIED_PENDING_CERS-G-LIVE-DISPATCH"
    assert "CERS_WP6_LIVE_PILOT" in a["denied"]
    assert a["parallel_physical_merge"] is False

def test_dependency_frontier_binds_integrated_wp0_and_current_vit_policy():
    f=load("docs/releases/development-skills-v0-3/cers-conformance/wp1-wp5/CERS_WP1_WP5_DEPENDENCY_FRONTIER_v0_1.json")
    assert canonical_id(f)==FRONTIER_ID
    assert f["baseline_commit"]==BASELINE
    assert f["observations"]["wp0_status_effective"]=="COMPLETED_BY_EXACT_ASSURED_SQUASH_MERGE"
    assert f["observations"]["vit_predecessor_resolution"]=="EXACT_VIT_PLACEMENT_TRAIN_PREDECESSOR"
    assert f["observations"]["administrative_closeout_route"]=="PHYSICAL_MATERIALISATION_RECEIPT_PACKET_COMPLETION_RECEIPT"
    assert f["blockers"]==[]

def test_programme_state_snapshot_carries_wp0_completion_and_stops_gate_ready_without_live_activation():
    s=load("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_6.json")
    assert s["status"]=="GATE_READY"
    assert s["packet_id"]=="CERS-G-LIVE-DISPATCH"
    assert s["live_unattended_dispatch"]=="DENIED_PENDING_CERS-G-LIVE-DISPATCH"
    wp0=next(x for x in s["packet_register"] if x["packet_id"]=="CERS-WP0")
    assert wp0["status"]=="COMPLETED" and wp0["merge_commit"]=="d7a7f12d99f9c101c3203cb4189f0c9f1d60d77d"
    for i in range(1,6):
        row=next(x for x in s["packet_register"] if x["packet_id"]==f"CERS-WP{i}")
        assert row["status"]=="COMPLETED" and row["decision"]=="PASS_DELEGATED"
    gate=next(x for x in s["packet_register"] if x["packet_id"]=="CERS-G-LIVE-DISPATCH")
    assert gate["status"]=="GATE_READY"
    assert gate["authority_required"]=="OPERATOR_REQUIRED"
    assert gate["decision"]=="NOT_TAKEN"

def test_live_dispatch_gate_snapshot_binds_existing_trusted_executor_but_does_not_activate_it():
    g=load("docs/releases/development-skills-v0-3/cers-conformance/wp1-wp5/CERS_G_LIVE_DISPATCH_GATE_PACKET_v0_1.json")
    assert g["status"]=="GATE_READY"
    assert g["decision"]=="NOT_TAKEN"
    assert g["executor_classification"]=="EXISTING_QUALIFIED_EXECUTOR_IDENTITY"
    assert g["executor"]["skill_id"]=="OVC-SKILL-030"
    assert g["executor"]["new_writer_identity_required"] is False
    assert g["proposed_live_pilot_scope"]["worker_concurrency"]==1
    assert g["proposed_live_pilot_scope"]["direct_main_mutation"] is False
    assert g["proposed_live_pilot_scope"]["force_push"] is False
