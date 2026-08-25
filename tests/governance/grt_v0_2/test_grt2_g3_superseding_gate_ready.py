from __future__ import annotations
import json
from pathlib import Path
from ovc.programme_genesis.grt_v0_2.debt import B0_MEMBER_COUNT,B0_MEMBERSHIP_SHA256,validate_debt_floor
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256
ROOT=Path(__file__).resolve().parents[3]; SUP=ROOT/"docs/programmes/grt-v0-2/g3/superseding"; STATE=ROOT/"registries/implementation/grt_v0_2"
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def logical(r):
 p=dict(r); e=p.pop("logical_sha256"); assert e==canonical_sha256(p)
def test_superseding_gate_ready_authority_inert():
 g=load(SUP/"GRT2_G3_SUPERSEDING_GATE_READY_DECISION_PACKET.json"); q=load(SUP/"GRT2_G3_SUPERSEDING_GATE_READY_QA_PACKET.json"); i=load(SUP/"GRT2_G3_SUPERSEDING_OPERATOR_INSTRUCTION_RECEIPT.json")
 for r in (g,q,i): logical(r)
 assert g["authority_consumed"]=="NONE" and g["operator_decision"] is None and g["operator_decision_required"] is True
 assert g["b0_lineage_and_provenance"]["member_count"]==B0_MEMBER_COUNT and g["b0_lineage_and_provenance"]["membership_sha256"]==B0_MEMBERSHIP_SHA256
 assert q["qa_recommendation"]=="PASS" and not q["warnings"] and not q["unresolved_issues"]
 assert i["instruction"]=="OVC APPROVE GRT2-G3 SUPERSEDING PASS" and i["consumed"] is False
def test_superseding_floor_new_valid_inactive():
 f=load(SUP/"GRT2_G3_SUPERSEDING_PROPOSED_DEBT_FLOOR_GENERATION_0.json"); o=load(ROOT/"docs/programmes/grt-v0-2/g3/GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json"); s=load(STATE/"OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json")
 validate_debt_floor(f); assert len(f["open_grandfathered_findings"])==s["candidate_debt_floor_count"] and f["floor_hash"]==s["candidate_debt_floor_hash"] and f["floor_hash"]!=o["floor_hash"]
 assert s["debt_floor_generation"] is None and s["constitution_status"]=="PROPOSED_UNADMITTED" and s["active_enforcement"]=="LIMITED_NEW_ARTIFACT_ENFORCEMENT"; logical(s)
def test_pointer_stops_without_activation():
 p=load(STATE/"CURRENT_STATE_POINTER.json"); assert p["packet_id"]=="GRT2-G3-SUPERSEDING-GATE-READY" and p["operator_decision_required"] is True and p["next_packet"]=="GRT2-G3-SUPERSEDING-OPERATOR-DECISION"
