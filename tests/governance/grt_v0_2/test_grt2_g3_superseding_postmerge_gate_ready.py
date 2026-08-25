from __future__ import annotations
import json
from pathlib import Path
from ovc.programme_genesis.grt_v0_2.debt import B0_MEMBER_COUNT,B0_MEMBERSHIP_SHA256
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256
ROOT=Path(__file__).resolve().parents[3]; SUP=ROOT/"docs/programmes/grt-v0-2/g3/superseding/postmerge"; STATE=ROOT/"registries/implementation/grt_v0_2"
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def logical(r):
 p=dict(r); e=p.pop("logical_sha256"); assert e==canonical_sha256(p)
def test_postmerge_superseding_gate_ready_is_authority_inert_and_exact():
 g=load(SUP/"GRT2_G3_SUPERSEDING_POSTMERGE_GATE_READY_DECISION_PACKET.json"); q=load(SUP/"GRT2_G3_SUPERSEDING_POSTMERGE_GATE_READY_QA_PACKET.json"); i=load(SUP/"GRT2_G3_SUPERSEDING_POSTMERGE_OPERATOR_INSTRUCTION_RECEIPT.json"); s=load(STATE/"OVC_GRT2_STATE_v0_17_SUPERSEDING_POSTMERGE_GATE_READY.json")
 for r in (g,q,i,s): logical(r)
 assert g["authority_consumed"]=="NONE" and g["operator_decision"] is None and g["operator_decision_required"] is True
 assert i["consumed"] is False and i["postmerge_exact_floor_hash"]=="49551ff2247be44b5b0ee21596a17a6e5f691010401e155f889ebbe5175235bb"
 assert g["proposed_debt_floor_generation_0"]["count"]==1641 and g["proposed_debt_floor_generation_0"]["floor_hash"]==i["postmerge_exact_floor_hash"]
 assert g["current_exact_census"]["resolved_count"]==6 and g["current_exact_census"]["added_count"]==19
 assert g["current_exact_census"]["extent_dispositions"]["EXPANDED"]==0 and g["current_exact_census"]["extent_dispositions"]["MATERIAL_CHANGED"]==0
 assert g["b0_lineage_and_provenance"]["member_count"]==B0_MEMBER_COUNT and g["b0_lineage_and_provenance"]["membership_sha256"]==B0_MEMBERSHIP_SHA256
 assert q["qa_recommendation"]=="PASS" and not q["warnings"] and not q["unresolved_issues"]
 assert s["constitution_status"]=="PROPOSED_UNADMITTED" and s["debt_floor_generation"] is None and s["active_enforcement"]=="LIMITED_NEW_ARTIFACT_ENFORCEMENT"
def test_postmerge_pointer_stops_for_fresh_operator_decision():
 p=load(STATE/"CURRENT_STATE_POINTER.json"); assert p["current_state"].endswith("OVC_GRT2_STATE_v0_17_SUPERSEDING_POSTMERGE_GATE_READY.json"); assert p["operator_decision_required"] is True; assert p["next_packet"]=="GRT2-G3-SUPERSEDING-POSTMERGE-OPERATOR-DECISION"
