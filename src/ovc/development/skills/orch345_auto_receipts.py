from __future__ import annotations
from typing import Any, Mapping, Sequence
from .orch345_auto_receipt_core import make_receipt

def orch3_receipt(source:Mapping[str,Any],candidate_count:int,ctx:Mapping[str,Any],observed:str|None=None)->dict[str,Any]:
    selected=list(source.get("selected_packet_ids",[]))
    return make_receipt("ORCH-3",ctx,{"decision":"TRAIN_AUTHORIZED" if selected else "NO_ELIGIBLE_TRAIN","candidate_packet_count":int(candidate_count),"selected_packet_ids":selected,"selected_train_depth":len(selected),"waiting":list(source.get("waiting",[])),"operator_boundaries":list(source.get("operator_boundaries",[])),"max_train_packets":int(source.get("max_train_packets",0)),"source_execution_record_id":source.get("record_id"),"source_plan_id":source.get("source_plan_id"),"parallel_merge":False},observed)

def orch4_receipt(source:Mapping[str,Any],classification:Mapping[str,Any],ctx:Mapping[str,Any],observed:str|None=None)->dict[str,Any]:
    decision="PARALLEL_ALLOW" if source.get("admission")=="PARALLEL_BUILD_ADMITTED_SERIAL_INTEGRATION_ONLY" else "SERIAL_FALLBACK"
    return make_receipt("ORCH-4",ctx,{"decision":decision,"left_packet_id":source.get("left_packet_id"),"right_packet_id":source.get("right_packet_id"),"classification":source.get("classification"),"reason_codes":list(source.get("reason_codes",[])),"overlaps":dict(classification.get("overlaps",{})),"admission":source.get("admission"),"source_execution_record_id":source.get("record_id"),"source_classification_id":classification.get("record_id"),"parallel_merge":False},observed)

def orch5_receipt(source:Mapping[str,Any],packets:Sequence[Mapping[str,Any]],completed:Sequence[str],newly_completed:Sequence[str],ctx:Mapping[str,Any],observed:str|None=None)->dict[str,Any]:
    selected=list(source.get("selected_packet_ids",[])); waiting=list(source.get("waiting",[])); limit=int(source.get("max_parallel_builds",0)); reasons={}
    for row in waiting:
        reason=str(row.get("reason","UNKNOWN")); reasons[reason]=reasons.get(reason,0)+1
    done,new,selected_set=set(map(str,completed)),set(map(str,newly_completed)),set(map(str,selected)); wakeups=[]
    for packet in packets:
        pid=str(packet.get("packet_id","")); deps={str(v) for v in packet.get("cross_programme_dependencies",()) if str(v)}; caused=sorted(deps&new)
        if pid in selected_set and deps and deps.issubset(done) and caused:
            wakeups.append({"packet_id":pid,"satisfied_dependencies":sorted(deps),"newly_satisfied_by":caused})
    return make_receipt("ORCH-5",ctx,{"decision":"PORTFOLIO_DISPATCH" if selected else "NO_ELIGIBLE_DISPATCH","candidate_packet_count":len(packets),"selected_packet_ids":selected,"selected_programme_ids":list(source.get("selected_programme_ids",[])),"scheduled_slot_count":len(selected),"remaining_schedule_capacity":max(0,limit-len(selected)),"schedule_selection_at_capacity":limit>0 and len(selected)>=limit,"actual_occupancy_observed":False,"waiting":waiting,"waiting_reason_counts":reasons,"serial_fallback_count":reasons.get("SERIAL_FALLBACK",0),"slot_limit_wait_count":reasons.get("PARALLEL_SLOT_LIMIT",0),"blocked":list(source.get("blocked",[])),"operator_wait":list(source.get("operator_wait",[])),"cross_programme_dependency_wakeups":wakeups,"dependency_wakeup_count":len(wakeups),"source_execution_record_id":source.get("record_id"),"source_schedule_id":source.get("source_schedule_id"),"parallel_merge":False},observed)
