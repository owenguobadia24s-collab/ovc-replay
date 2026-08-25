from __future__ import annotations
import json
from pathlib import Path
from ovc.programme_genesis.grt_v0_2.debt import validate_debt_floor
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256
ROOT=Path(__file__).resolve().parents[3]; G3=ROOT/"docs/programmes/grt-v0-2/g3"; GOV=ROOT/"registries/governance/grt_v0_2"
def load(p): return json.loads(p.read_text())
def check(r):
 p=dict(r); x=p.pop("logical_sha256"); assert x==canonical_sha256(p)
def test_terminal_supersession_operator_pass_exact():
 d=load(G3/"GRT2_G3_OPERATOR_DECISION.json"); check(d); assert d["operator_instruction"]=="OVC APPROVE GRT2-G3 TERMINAL SUPERSESSION PASS"; assert d["approved_terminal_decision_identity"]=="401b6ab70f3f6ee977766176f12336c7ba1c3f263375e64012d4cec9124b8f49"; assert d["approved_authority_delta"]["debt_floor"]["floor_hash"]=="2c2152397e1ac5ace98b3363ca39c84f5d5a5dadbc6243e73cbd1fba15413c8b"
def test_active_floor_is_exact_approved_superseding_object():
 decision=load(G3/"GRT2_G3_TERMINAL_SUPERSESSION_DECISION.json"); proposed=dict(decision["proposed_replacement_generation_0_floor"]); proposed.pop("member_count"); proposed.pop("status"); active=load(GOV/"debt_floors/GRT_DEBT_FLOOR_G0.json"); ptr=load(GOV/"GRT_DEBT_FLOOR_CURRENT.json"); assert active==proposed; validate_debt_floor(active); assert len(active["open_grandfathered_findings"])==1648; assert active["floor_hash"]=="2c2152397e1ac5ace98b3363ca39c84f5d5a5dadbc6243e73cbd1fba15413c8b"; check(ptr); assert ptr["floor_hash"]==active["floor_hash"]
def test_authority_exact_and_non_grt_denials_preserved():
 a=load(ROOT/"registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_2.json"); check(a); assert a["enforcement_mode"]=="FULL_GRT_EXACT"; assert a["constitution_status"]=="ACTIVE"; assert a["no_new_hygiene_debt_required"] is True; assert "Programme Genesis adoption authority" in a["authority_exclusions"]; assert "probability, risk, exposure, trading, execution or agent-write authority" in a["authority_exclusions"]
def test_activation_state_preserves_exact_wp4_handoff():
 s=load(ROOT/"registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_17_SUPERSEDING_ACTIVATION.json"); check(s); assert s["next_packet"]=="GRT2-WP4" and s["next_gate"]=="GRT2-G4"; assert s["current_projection_status"]=="PRE_G3_POINTER_INTENTIONALLY_PRESERVED_AS_INHERITED_STALE_STATE_FOR_WP4_WAVE_A"
def test_revalidation_and_serialized_exact_lane():
 r=load(G3/"GRT2_G3_ACTIVATION_REVALIDATION.json"); check(r); assert r["approved_floor_member_count"]==1648 and r["approved_missing_from_current_count"]==0 and r["current_not_in_approved_count"]==0 and r["b0_exact"] is True and r["unresolved_lineage_count"]==0; w=(ROOT/".github/workflows/ovc-tiered-tests.yml").read_text(); assert "group: ovc-main-integration-lane-v1" in w; assert "Run required GRT-EXACT against the exact late-bound integration tree" in w; assert "Run mandatory SIQ/PDC exact-final assurance inside lease" in w; assert "Run lightweight GRT integration readiness" in w
