from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

PROTECTED_ROLES={"DEVELOPMENT","VALIDATION"}
EXPOSURE_CHANNELS={"HUMAN","ALGORITHM","SUMMARY"}
ALLOCATION_STATES={"PROPOSED","RESERVED_UNCONSUMED","CONSUMED","RELEASED","BLOCKED","SUPERSEDED"}
FORBIDDEN_PROTECTED_LOCATOR_KEYS={"locator","read_path","credential","query","provider_selector","artifact_handle","row_selector"}

class PopulationRegisterError(ValueError): pass

def _req(cond: bool, code: str) -> None:
    if not cond: raise PopulationRegisterError(code)

def validate_register(register: Mapping[str,Any]) -> None:
    _req(register.get("schema_version")=="ovc.population_allocation_exposure_register.v0.1","SCHEMA_VERSION")
    _req(register.get("authority_effect")=="NONE","AUTHORITY_EFFECT")
    rs=register.get("resources"); _req(isinstance(rs,list),"RESOURCES")
    ids=[r.get("population_id") for r in rs]
    _req(all(isinstance(x,str) and x for x in ids) and len(ids)==len(set(ids)),"POPULATION_ID_UNIQUE")
    for r in rs:
        _req(r.get("current_exposure_state") in {"UNKNOWN_REQUIRES_CENSUS","UNEXPOSED_VERIFIED","EXPOSED","QUARANTINED"},"EXPOSURE_STATE")
        cvs=r.get("clock_views"); _req(isinstance(cvs,list) and cvs and len(cvs)==len(set(cvs)),"CLOCK_VIEWS")
    events=register.get("exposure_events",[])
    eids=[e.get("event_id") for e in events]; _req(len(eids)==len(set(eids)),"EXPOSURE_EVENT_ID_UNIQUE")
    for e in events:
        _req(e.get("channel") in EXPOSURE_CHANNELS,"EXPOSURE_CHANNEL")
        _req(e.get("irreversible") is True,"EXPOSURE_IRREVERSIBLE")

def population(register: Mapping[str,Any], population_id: str) -> Mapping[str,Any]:
    for r in register["resources"]:
        if r["population_id"]==population_id: return r
    raise PopulationRegisterError("UNKNOWN_POPULATION")

def record_allocation(register: Mapping[str,Any], allocation: Mapping[str,Any]) -> dict[str,Any]:
    out=deepcopy(register); population(out,allocation.get("population_id"))
    role=allocation.get("role")
    _req(role in {"DISCOVERY","DEVELOPMENT","VALIDATION","REPLAY_QA","HISTORICAL_REPLICATION"},"ROLE")
    _req(allocation.get("state") in ALLOCATION_STATES,"ALLOCATION_STATE")
    _req(bool(allocation.get("allocation_id")),"ALLOCATION_ID")
    _req(not any(a.get("allocation_id")==allocation["allocation_id"] for a in out["allocations"]),"ALLOCATION_ID_UNIQUE")
    if role in PROTECTED_ROLES:
        _req(bool(allocation.get("authority_ref")),"PROTECTED_ROLE_AUTHORITY_REQUIRED")
        if allocation.get("state")=="RESERVED_UNCONSUMED":
            _req(not(FORBIDDEN_PROTECTED_LOCATOR_KEYS & set(allocation)),"PROTECTED_RESERVATION_LOCATOR_FORBIDDEN")
    rec=dict(allocation); rec["authority_effect"]="NONE"; out["allocations"].append(rec); validate_register(out); return out

def record_exposure(register: Mapping[str,Any], event: Mapping[str,Any]) -> dict[str,Any]:
    out=deepcopy(register); pid=event.get("population_id"); population(out,pid)
    _req(bool(event.get("event_id")),"EXPOSURE_EVENT_ID")
    _req(not any(e.get("event_id")==event["event_id"] for e in out["exposure_events"]),"EXPOSURE_EVENT_ID_UNIQUE")
    _req(event.get("channel") in EXPOSURE_CHANNELS,"EXPOSURE_CHANNEL")
    _req(bool(event.get("programme_id")) and bool(event.get("observed_at")) and bool(event.get("source_ref")),"EXPOSURE_IDENTITY")
    rec=dict(event); rec["irreversible"]=True; rec["authority_effect"]="NONE"; out["exposure_events"].append(rec)
    for r in out["resources"]:
        if r["population_id"]==pid: r["current_exposure_state"]="EXPOSED"
    validate_register(out); return out

def eligibility(register: Mapping[str,Any], population_id: str, role: str) -> dict[str,Any]:
    r=population(register,population_id); events=[e for e in register.get("exposure_events",[]) if e.get("population_id")==population_id]
    state=r["current_exposure_state"]
    if state=="QUARANTINED": d="BLOCKED_QUARANTINED"
    elif role in {"DISCOVERY","REPLAY_QA","HISTORICAL_REPLICATION"}: d="REUSABLE_WITH_DISCLOSURE"
    elif state=="UNKNOWN_REQUIRES_CENSUS": d="BLOCKED_EXPOSURE_CENSUS_REQUIRED"
    elif role=="VALIDATION" and events: d="NOT_UNTOUCHED_FOR_INDEPENDENT_VALIDATION"
    elif role in PROTECTED_ROLES: d="PREFLIGHT_AND_OPERATOR_AUTHORITY_REQUIRED"
    else: raise PopulationRegisterError("ROLE")
    return {"population_id":population_id,"role":role,"exposure_state":state,"exposure_event_count":len(events),"channels":sorted({e["channel"] for e in events}),"disposition":d,"authority_effect":"NONE"}
