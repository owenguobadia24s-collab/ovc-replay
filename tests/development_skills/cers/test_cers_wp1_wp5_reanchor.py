from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASELINE = "d7a7f12d99f9c101c3203cb4189f0c9f1d60d77d"
AUTHORITY_ID = "4680cd4fb225179e199265fae656152dad41c504707f51a858c99c60a8e6ac02"
FRONTIER_ID = "06c0a1117551ee5adaaf3d950444aeede129aa9f4071722670b21d45a735979e"

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

def test_programme_state_carries_wp0_completion_forward_without_live_activation():
    s=load("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_5.json")
    p=load("registries/implementation/dsai3v_cers_v0_1/CURRENT_STATE_POINTER.json")
    assert s["status"]=="QA_REVIEW"
    assert s["packet_id"]=="CERS-WP1-WP5"
    assert s["live_unattended_dispatch"]=="DENIED_PENDING_CERS-G-LIVE-DISPATCH"
    wp0=next(x for x in s["packet_register"] if x["packet_id"]=="CERS-WP0")
    assert wp0["status"]=="COMPLETED" and wp0["merge_commit"]==BASELINE
    gate=next(x for x in s["packet_register"] if x["packet_id"]=="CERS-G-LIVE-DISPATCH")
    assert gate["authority_required"]=="OPERATOR_REQUIRED"
    assert p["current_state"].endswith("OVC_DSAI3V_CERS_STATE_v0_5.json")
