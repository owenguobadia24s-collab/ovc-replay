from __future__ import annotations
import json
from pathlib import Path
from ovc.programme_genesis.grt_v0_2.debt import validate_debt_floor
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256
ROOT=Path(__file__).resolve().parents[3]; G3=ROOT/"docs/programmes/grt-v0-2/g3"; GOV=ROOT/"registries/governance/grt_v0_2"
def load(p): return json.loads(p.read_text())
def check(r):
 p=dict(r); x=p.pop("logical_sha256"); assert x==canonical_sha256(p)
def test_superseding_operator_pass_exact():
 d=load(G3/"GRT2_G3_OPERATOR_DECISION.json"); check(d); assert d["operator_instruction"]=="OVC APPROVE GRT2-G3 SUPERSEDING PASS"; assert d["approved_gate_decision_identity"]=="7258dd4f626eac8235b4ca285b5a5057d196a5f5d403c6c7daea85a1aee1b4f2"; assert d["approved_authority_delta"]["debt_floor"]["floor_hash"]=="c99fd885b27861c920aea3bec1b849ed928be771c4ce5c51dbff4ef2da0e8fa5"
def test_active_floor_is_exact_approved_superseding_object():
 proposed=load(ROOT/"docs/programmes/grt-v0-2/g3/superseding/GRT2_G3_SUPERSEDING_PROPOSED_DEBT_FLOOR_GENERATION_0.json"); active=load(GOV/"debt_floors/GRT_DEBT_FLOOR_G0.json"); ptr=load(GOV/"GRT_DEBT_FLOOR_CURRENT.json"); assert active==proposed; validate_debt_floor(active); assert len(active["open_grandfathered_findings"])==1641; assert active["floor_hash"]=="c99fd885b27861c920aea3bec1b849ed928be771c4ce5c51dbff4ef2da0e8fa5"; check(ptr); assert ptr["floor_hash"]==active["floor_hash"]
def test_authority_exact_and_non_grt_denials_preserved():
 a=load(ROOT/"registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_2.json"); check(a); assert a["enforcement_mode"]=="FULL_GRT_EXACT"; assert a["constitution_status"]=="ACTIVE"; assert a["no_new_hygiene_debt_required"] is True; assert "Programme Genesis adoption authority" in a["authority_exclusions"]; assert "probability, risk, exposure, trading, execution or agent-write authority" in a["authority_exclusions"]
def test_activation_state_stops_pointer_churn_until_wp4():
 s=load(ROOT/"registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_17_SUPERSEDING_ACTIVATION.json"); check(s); ptr=load(ROOT/"registries/implementation/grt_v0_2/CURRENT_STATE_POINTER.json"); assert s["next_packet"]=="GRT2-WP4" and s["next_gate"]=="GRT2-G4"; assert ptr["current_state"].endswith("OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json")
def test_revalidation_and_serialized_exact_lane():
 r=load(G3/"GRT2_G3_ACTIVATION_REVALIDATION.json"); check(r); assert r["approved_floor_member_count"]==1641 and r["approved_missing_from_current_count"]==0 and r["current_not_in_approved_count"]==0 and r["b0_exact"] is True and r["unresolved_lineage_count"]==0; w=(ROOT/".github/workflows/ovc-tiered-tests.yml").read_text(); assert "group: ovc-main-integration-lane-v1" in w; assert "Run required GRT-EXACT against the exact late-bound integration tree" in w; assert "Run mandatory SIQ/PDC exact-final assurance inside lease" in w; assert "Run lightweight GRT integration readiness" in w
