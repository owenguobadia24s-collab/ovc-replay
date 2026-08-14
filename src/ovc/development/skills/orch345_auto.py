from __future__ import annotations
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

from ovc.development.identity import canonical_sha256
from .orch345 import PARALLEL_BUILD_CLASS, classify_packet_pair, resolve_orch345_authority
from .orch345_active import DEFAULT_MAX_PARALLEL_BUILDS, DEFAULT_MAX_TRAIN_PACKETS, authorize_parallel_build_pair, build_authorized_packet_train, build_authorized_portfolio_schedule
from .orch345_auto_receipt_core import persist_receipt
from .orch345_auto_receipts import orch3_receipt, orch4_receipt, orch5_receipt

DEFAULT_EVIDENCE_OUTPUT=Path("records/development/skills")

def _state_id(value:Mapping[str,Any],role:str)->str:
    return str(value.get("record_id","")).strip() or canonical_sha256(dict(value),role=role)

def _clean(value:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in value.items() if k!="diagnostic_receipt"}

def run_automatic_orchestration(*,authority:Mapping[str,Any],programme_state:Mapping[str,Any],packet_states:Sequence[Mapping[str,Any]],trigger_source:str,completed_packet_ids:Sequence[str]=(),newly_completed_packet_ids:Sequence[str]=(),max_train_packets:int=DEFAULT_MAX_TRAIN_PACKETS,max_parallel_builds:int=DEFAULT_MAX_PARALLEL_BUILDS,evidence_output:Path|str=DEFAULT_EVIDENCE_OUTPUT,authority_record_present_on_main:bool=True,invocation_id:str|None=None,observed_at_utc:str|None=None)->dict[str,Any]:
    programme_id=str(programme_state.get("programme_id","")).strip()
    if not programme_id or not str(trigger_source).strip() or not packet_states:
        raise ValueError("programme state, trigger source and packet states are required")
    by_id={}; packet_state_ids={}
    for packet in packet_states:
        pid=str(packet.get("packet_id","")).strip()
        if not pid or pid in by_id: raise ValueError("packet states require unique packet ids")
        by_id[pid]=packet; packet_state_ids[pid]=_state_id(packet,"DSAI2_SOURCE_PACKET_STATE")
    programme_packets=[p for p in packet_states if str(p.get("programme_id",""))==programme_id]
    if not programme_packets: raise ValueError("source programme has no packet state")

    resolution=resolve_orch345_authority(authority=authority,record_present_on_main=authority_record_present_on_main)
    if resolution.get("status")!="ACTIVE_AUTHORIZED": raise PermissionError("bounded ORCH-3/4/5 authority is not active")

    programme_state_id=_state_id(programme_state,"DSAI2_SOURCE_PROGRAMME_STATE")
    run_logical={"source_programme_id":programme_id,"source_programme_state_id":programme_state_id,"source_packet_state_ids":dict(sorted(packet_state_ids.items())),"trigger_source":str(trigger_source),"completed_packet_ids":sorted(map(str,completed_packet_ids)),"newly_completed_packet_ids":sorted(map(str,newly_completed_packet_ids)),"max_train_packets":int(max_train_packets),"max_parallel_builds":int(max_parallel_builds)}
    run_id=canonical_sha256(run_logical,role="DSAI2_ORCH345_AUTOMATIC_ORCHESTRATION_RUN")
    invocation=invocation_id or f"ORCH345-AUTO-{uuid4().hex.upper()}"
    observed=observed_at_utc or datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")
    ctx={"orchestration_run_id":run_id,"invocation_id":invocation,"invocation_mode":"AUTO","trigger_source":str(trigger_source),"source_programme_id":programme_id,"source_programme_state_id":programme_state_id,"source_packet_state_ids":dict(sorted(packet_state_ids.items()))}

    orch3=build_authorized_packet_train(authority_resolution=resolution,programme_id=programme_id,packets=programme_packets,completed_packet_ids=completed_packet_ids,max_packets=max_train_packets)
    orch5=build_authorized_portfolio_schedule(authority_resolution=resolution,packets=packet_states,completed_packet_ids=completed_packet_ids,newly_completed_packet_ids=newly_completed_packet_ids,max_parallel=max_parallel_builds)
    selected=list(map(str,orch5.get("selected_packet_ids",[]))); orch4=[]; classifications=[]
    for left_id,right_id in combinations(selected,2):
        classification=classify_packet_pair(by_id[left_id],by_id[right_id])
        admission=authorize_parallel_build_pair(authority_resolution=resolution,left=by_id[left_id],right=by_id[right_id])
        if admission.get("source_classification_id")!=classification.get("record_id") or admission.get("classification")!=PARALLEL_BUILD_CLASS:
            raise RuntimeError("ORCH-4/5 automatic selection identity or admission drift")
        classifications.append(classification); orch4.append(admission)

    receipts=[orch3_receipt(orch3,len(programme_packets),ctx,observed)]
    receipts.extend(orch4_receipt(row,classification,ctx,observed) for row,classification in zip(orch4,classifications))
    receipts.append(orch5_receipt(orch5,packet_states,completed_packet_ids,newly_completed_packet_ids,ctx,observed))
    paths=[persist_receipt(receipt,evidence_output) for receipt in receipts]
    return {"schema":"ovc-dsai2-orch345-automatic-orchestration-invocation/v1","orchestration_run_id":run_id,"invocation_id":invocation,"invocation_mode":"AUTO","trigger_source":str(trigger_source),"source_programme_id":programme_id,"source_programme_state_id":programme_state_id,"source_packet_state_ids":dict(sorted(packet_state_ids.items())),"orch3_execution_record":_clean(orch3),"orch4_execution_records":[_clean(row) for row in orch4],"orch5_execution_record":_clean(orch5),"diagnostic_receipts":receipts,"diagnostic_receipt_ids":[r["record_id"] for r in receipts],"persisted_receipt_paths":[str(path) for path in paths],"receipt_phase":"DECISION_SELECTED","execution_started_observed":False,"execution_completed_observed":False,"authority_delta":"NONE","parallel_merge":False}
