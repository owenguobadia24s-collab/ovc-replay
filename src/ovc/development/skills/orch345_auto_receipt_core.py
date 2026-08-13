from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping
from ovc.development.identity import canonical_json_bytes, canonical_sha256

SCHEMAS={"ORCH-3":"ovc-dsai2-orch3-auto-diagnostic-receipt/v2","ORCH-4":"ovc-dsai2-orch4-auto-diagnostic-receipt/v2","ORCH-5":"ovc-dsai2-orch5-auto-diagnostic-receipt/v2"}
ROLES={k:f"DSAI2_{k.replace('-','')}_AUTO_DIAGNOSTIC_RECEIPT" for k in SCHEMAS}

def make_receipt(orch:str, ctx:Mapping[str,Any], logical:Mapping[str,Any], observed:str|None=None)->dict[str,Any]:
    states=ctx.get("source_packet_state_ids")
    required=("orchestration_run_id","invocation_id","trigger_source","source_programme_id","source_programme_state_id")
    if ctx.get("invocation_mode")!="AUTO" or any(not str(ctx.get(k,"")).strip() for k in required) or not isinstance(states,Mapping) or not states:
        raise ValueError("complete AUTO orchestration provenance is required")
    payload={"receipt_class":"TEMPORARY_DIAGNOSTIC_OBSERVABILITY","orchestrator":orch,"observed_at_utc":observed or datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z"),"receipt_phase":"DECISION_SELECTED","execution_started_observed":False,"execution_completed_observed":False,"observability_only":True,"temporary":True,"governance_expansion":False,"authority_effect":"NONE","new_operator_gate":False,"merge_authority":"NONE","orchestration_run_id":str(ctx["orchestration_run_id"]),"invocation_id":str(ctx["invocation_id"]),"invocation_mode":"AUTO","trigger_source":str(ctx["trigger_source"]),"source_programme_id":str(ctx["source_programme_id"]),"source_programme_state_id":str(ctx["source_programme_state_id"]),"source_packet_state_ids":dict(sorted((str(k),str(v)) for k,v in states.items())),**dict(logical)}
    return {"schema":SCHEMAS[orch],**payload,"record_id":canonical_sha256(payload,role=ROLES[orch])}

def validate_receipt(value:Mapping[str,Any])->dict[str,Any]:
    orch=str(value.get("orchestrator","")); payload={k:v for k,v in value.items() if k not in {"schema","record_id"}}
    if value.get("schema")!=SCHEMAS.get(orch) or value.get("invocation_mode")!="AUTO" or value.get("receipt_phase")!="DECISION_SELECTED" or value.get("execution_started_observed") is not False or value.get("execution_completed_observed") is not False or value.get("record_id")!=canonical_sha256(payload,role=ROLES.get(orch,"")):
        raise ValueError("invalid automatic ORCH diagnostic receipt")
    return dict(value)

def persist_receipt(value:Mapping[str,Any],root:Path|str)->Path:
    receipt=validate_receipt(value); path=Path(root)/f"ORCH345_DIAGNOSTIC_{receipt['orchestrator'].replace('-','')}_{receipt['record_id']}.json"; path.parent.mkdir(parents=True,exist_ok=True); data=canonical_json_bytes(receipt)+b"\n"
    if path.exists() and path.read_bytes()!=data: raise ValueError("diagnostic receipt collision")
    if not path.exists(): path.write_bytes(data)
    return path

def load_receipt(path:Path|str)->dict[str,Any]:
    value=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError("diagnostic receipt root must be an object")
    return validate_receipt(value)
