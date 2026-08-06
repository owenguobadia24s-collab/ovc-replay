"""Deterministic, neutral C2E episode and nesting ledger (shadow only)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Iterable, Mapping, Sequence

POLICY_ID = "MG-C2E-BOUNDARY-v0.1"
SCHEMA_VERSION = "0.1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED = frozenset({"record_id","source_release_id","instrument_id","side","scope_id","clock_id","first_valid_time","state_key","transition_kind","parent_record_id","computability_status","not_evaluable_reason","reset_reason","source_sha256"})
FORBIDDEN = frozenset({"family_id","cluster_id","medoid_id","variant_id","sensitivity_pack_id","distance","outcome","outcome_id","return","returns","mfe","mae","future_price","future_path","probability","risk","exposure","execution","trade_label","semantic_label","grammar_id","parse_id"})
COMPLETION = frozenset({"COMPLETION","STRUCTURAL_COMPLETION","TERMINATION"})
INTERRUPTION = frozenset({"INTERRUPTION","STRUCTURAL_INTERRUPTION"})

class ComputabilityStatus(str, Enum):
    EVALUABLE="EVALUABLE"; NOT_EVALUATED="NOT_EVALUATED"; NOT_EVALUABLE="NOT_EVALUABLE"; STALE="STALE"; CENSORED="CENSORED"; CONFLICT="CONFLICT"; QUARANTINED="QUARANTINED"
class EpisodeStatus(str, Enum):
    COMPLETED="COMPLETED"; INTERRUPTED="INTERRUPTED"; CENSORED="CENSORED"; OPEN_AT_CUTOFF="OPEN_AT_CUTOFF"
class BoundaryCause(str, Enum):
    START_OF_INPUT="START_OF_INPUT"; PARENT_CHANGE="PARENT_CHANGE"; RESET="RESET"; COMPLETION="COMPLETION"; COMPUTABILITY_BREAK="COMPUTABILITY_BREAK"; END_OF_INPUT="END_OF_INPUT"
class PhaseKind(str, Enum):
    START="START"; STATE="STATE"; TRANSITION="TRANSITION"; INTERRUPTION="INTERRUPTION"; PARENT_CHANGE="PARENT_CHANGE"; COMPLETION="COMPLETION"
class NestingRelation(str, Enum):
    NESTED_WITHIN="NESTED_WITHIN"; CONTEXT_PARENT="CONTEXT_PARENT"; DERIVED_FROM="DERIVED_FROM"

def _text(value: object, field: str, upper: bool=False) -> str:
    result=str(value).strip()
    if not result: raise ValueError(f"{field} must be non-empty")
    return result.upper() if upper else result

def _time(value: str, field: str="first_valid_time") -> datetime:
    text=_text(value, field)
    if text.endswith("Z"): text=text[:-1]+"+00:00"
    try: parsed=datetime.fromisoformat(text)
    except ValueError as exc: raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None: raise ValueError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)

def _ctime(value: str) -> str: return _time(value).isoformat().replace("+00:00","Z")
def _bytes(value: object) -> bytes: return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _id(prefix: str, value: object) -> str: return prefix+sha256(_bytes(value)).hexdigest()

@dataclass(frozen=True)
class C2LedgerInput:
    record_id:str; source_release_id:str; instrument_id:str; side:str; scope_id:str; clock_id:str; first_valid_time:str; state_key:str
    transition_kind:str="NONE"; parent_record_id:str|None=None; computability_status:ComputabilityStatus=ComputabilityStatus.EVALUABLE
    not_evaluable_reason:str|None=None; reset_reason:str|None=None; source_sha256:str=""
    def __post_init__(self) -> None:
        for field in ("record_id","source_release_id","instrument_id","scope_id","clock_id","state_key"):
            object.__setattr__(self,field,_text(getattr(self,field),field))
        object.__setattr__(self,"side",_text(self.side,"side",True)); object.__setattr__(self,"first_valid_time",_ctime(self.first_valid_time))
        object.__setattr__(self,"transition_kind",_text(self.transition_kind,"transition_kind",True)); object.__setattr__(self,"computability_status",ComputabilityStatus(self.computability_status))
        for field in ("parent_record_id","not_evaluable_reason","reset_reason"):
            if getattr(self,field) is not None: object.__setattr__(self,field,_text(getattr(self,field),field))
        digest=_text(self.source_sha256,"source_sha256").lower()
        if HEX64.fullmatch(digest) is None: raise ValueError("source_sha256 must be a lowercase SHA-256 hex digest")
        object.__setattr__(self,"source_sha256",digest)
        if self.computability_status is not ComputabilityStatus.EVALUABLE and self.not_evaluable_reason is None: raise ValueError("non-evaluable inputs require an explicit not_evaluable_reason")
        if self.computability_status is ComputabilityStatus.EVALUABLE and self.not_evaluable_reason is not None: raise ValueError("EVALUABLE inputs cannot carry a not_evaluable_reason")
    @classmethod
    def from_mapping(cls, value: Mapping[str,object]) -> "C2LedgerInput":
        keys=set(value); forbidden=sorted(keys&FORBIDDEN); unknown=sorted(keys-ALLOWED)
        if forbidden: raise ValueError("downstream/future/outcome fields are forbidden: "+", ".join(forbidden))
        if unknown: raise ValueError("unsupported C2 input fields: "+", ".join(unknown))
        return cls(**dict(value))

@dataclass(frozen=True)
class PhaseRecord:
    phase_id:str; episode_id:str; phase_index:int; phase_kind:PhaseKind; first_valid_time:str; source_record_id:str; state_key:str; transition_kind:str; parent_record_id:str|None
    def to_dict(self) -> dict[str,object]:
        return {"phase_id":self.phase_id,"episode_id":self.episode_id,"phase_index":self.phase_index,"phase_kind":self.phase_kind.value,"first_valid_time":self.first_valid_time,"source_record_id":self.source_record_id,"state_key":self.state_key,"transition_kind":self.transition_kind,"parent_record_id":self.parent_record_id}

@dataclass(frozen=True)
class EpisodeRecord:
    episode_id:str; source_release_id:str; instrument_id:str; side:str; scope_id:str; clock_id:str; start_first_valid_time:str; end_first_valid_time:str
    member_record_ids:tuple[str,...]; member_source_sha256:tuple[str,...]; parent_record_ids:tuple[str,...]; phases:tuple[PhaseRecord,...]
    status:EpisodeStatus; boundary_cause:BoundaryCause; boundary_record_id:str|None; censoring_reason:str|None
    policy_id:str=POLICY_ID; authority_state:str="SHADOW_EXPERIMENT"; semantic_state:str="NEUTRAL_NON_SEMANTIC_NON_PREDICTIVE"
    def to_dict(self) -> dict[str,object]:
        return {"episode_id":self.episode_id,"source_release_id":self.source_release_id,"instrument_id":self.instrument_id,"side":self.side,"scope_id":self.scope_id,"clock_id":self.clock_id,"start_first_valid_time":self.start_first_valid_time,"end_first_valid_time":self.end_first_valid_time,"member_record_ids":list(self.member_record_ids),"member_source_sha256":list(self.member_source_sha256),"parent_record_ids":list(self.parent_record_ids),"phases":[x.to_dict() for x in self.phases],"status":self.status.value,"boundary_cause":self.boundary_cause.value,"boundary_record_id":self.boundary_record_id,"censoring_reason":self.censoring_reason,"policy_id":self.policy_id,"authority_state":self.authority_state,"semantic_state":self.semantic_state}

@dataclass(frozen=True)
class NotEvaluableRecord:
    source_record_id:str; first_valid_time:str; computability_status:ComputabilityStatus; reason:str; source_sha256:str
    def to_dict(self) -> dict[str,object]: return {"source_record_id":self.source_record_id,"first_valid_time":self.first_valid_time,"computability_status":self.computability_status.value,"reason":self.reason,"source_sha256":self.source_sha256}

@dataclass(frozen=True)
class EpisodeLedger:
    ledger_id:str; policy_id:str; source_release_id:str; instrument_id:str; side:str; scope_id:str; clock_id:str; build_cutoff:str
    input_record_ids:tuple[str,...]; input_source_sha256:tuple[str,...]; episodes:tuple[EpisodeRecord,...]; not_evaluable:tuple[NotEvaluableRecord,...]
    schema_version:str=SCHEMA_VERSION; authority_state:str="SHADOW_EXPERIMENT"
    def to_dict(self) -> dict[str,object]:
        return {"ledger_id":self.ledger_id,"policy_id":self.policy_id,"source_release_id":self.source_release_id,"instrument_id":self.instrument_id,"side":self.side,"scope_id":self.scope_id,"clock_id":self.clock_id,"build_cutoff":self.build_cutoff,"input_record_ids":list(self.input_record_ids),"input_source_sha256":list(self.input_source_sha256),"episodes":[x.to_dict() for x in self.episodes],"not_evaluable":[x.to_dict() for x in self.not_evaluable],"schema_version":self.schema_version,"authority_state":self.authority_state}

@dataclass(frozen=True)
class EpisodeBindingRequest:
    child_episode_id:str; parent_episode_id:str; relation:NestingRelation; first_valid_time:str
    def __post_init__(self) -> None:
        object.__setattr__(self,"child_episode_id",_text(self.child_episode_id,"child_episode_id")); object.__setattr__(self,"parent_episode_id",_text(self.parent_episode_id,"parent_episode_id"))
        object.__setattr__(self,"relation",NestingRelation(self.relation)); object.__setattr__(self,"first_valid_time",_ctime(self.first_valid_time))
        if self.child_episode_id==self.parent_episode_id: raise ValueError("episode cannot be its own parent")
@dataclass(frozen=True)
class EpisodeBinding:
    binding_id:str; child_episode_id:str; parent_episode_id:str; relation:NestingRelation; first_valid_time:str
    def to_dict(self) -> dict[str,object]: return {"binding_id":self.binding_id,"child_episode_id":self.child_episode_id,"parent_episode_id":self.parent_episode_id,"relation":self.relation.value,"first_valid_time":self.first_valid_time}

def _phase(record:C2LedgerInput, first:bool, changed:bool) -> PhaseKind:
    if changed:return PhaseKind.PARENT_CHANGE
    if first:return PhaseKind.START
    if record.transition_kind in INTERRUPTION:return PhaseKind.INTERRUPTION
    if record.transition_kind in COMPLETION:return PhaseKind.COMPLETION
    return PhaseKind.TRANSITION if record.transition_kind!="NONE" else PhaseKind.STATE

def _finalise(members:Sequence[C2LedgerInput], kinds:Sequence[PhaseKind], status:EpisodeStatus, cause:BoundaryCause, boundary:str|None, reason:str|None) -> EpisodeRecord:
    if not members: raise ValueError("cannot finalise empty episode")
    payload={"policy_id":POLICY_ID,"source_release_id":members[0].source_release_id,"instrument_id":members[0].instrument_id,"side":members[0].side,"scope_id":members[0].scope_id,"clock_id":members[0].clock_id,"start_first_valid_time":members[0].first_valid_time,"end_first_valid_time":members[-1].first_valid_time,"member_record_ids":[x.record_id for x in members],"member_source_sha256":[x.source_sha256 for x in members],"status":status.value,"boundary_cause":cause.value,"boundary_record_id":boundary,"censoring_reason":reason}
    episode_id=_id("C2E.EP.",payload); phases=[]
    for index,(record,kind) in enumerate(zip(members,kinds,strict=True)):
        pp={"episode_id":episode_id,"phase_index":index,"phase_kind":kind.value,"first_valid_time":record.first_valid_time,"source_record_id":record.record_id,"state_key":record.state_key,"transition_kind":record.transition_kind,"parent_record_id":record.parent_record_id}
        phases.append(PhaseRecord(_id("C2E.PH.",pp),episode_id,index,kind,record.first_valid_time,record.record_id,record.state_key,record.transition_kind,record.parent_record_id))
    return EpisodeRecord(episode_id,members[0].source_release_id,members[0].instrument_id,members[0].side,members[0].scope_id,members[0].clock_id,members[0].first_valid_time,members[-1].first_valid_time,tuple(x.record_id for x in members),tuple(x.source_sha256 for x in members),tuple(sorted({x.parent_record_id for x in members if x.parent_record_id})),tuple(phases),status,cause,boundary,reason)

def build_episode_ledger(records:Iterable[C2LedgerInput|Mapping[str,object]],*,build_cutoff:str) -> EpisodeLedger:
    cutoff=_ctime(build_cutoff); values=[x if isinstance(x,C2LedgerInput) else C2LedgerInput.from_mapping(x) for x in records]
    if not values: raise ValueError("at least one C2 record is required")
    values.sort(key=lambda x:(_time(x.first_valid_time),x.record_id)); ids=[x.record_id for x in values]; times=[x.first_valid_time for x in values]
    if len(ids)!=len(set(ids)): raise ValueError("duplicate record_id")
    if len(times)!=len(set(times)): raise ValueError("duplicate first_valid_time within exact scope")
    if any(_time(x.first_valid_time)>_time(cutoff) for x in values): raise ValueError("future C2 record exceeds build_cutoff")
    scopes={(x.source_release_id,x.instrument_id,x.side,x.scope_id,x.clock_id) for x in values}
    if len(scopes)!=1: raise ValueError("ledger inputs must share release, instrument, side, scope and clock")
    release,instrument,side,scope,clock=next(iter(scopes)); episodes=[]; excluded=[]; active=[]; kinds=[]; active_parent=None
    def close(status:EpisodeStatus,cause:BoundaryCause,boundary:str|None,reason:str|None) -> None:
        nonlocal active,kinds,active_parent
        if active: episodes.append(_finalise(active,kinds,status,cause,boundary,reason))
        active=[]; kinds=[]; active_parent=None
    for record in values:
        if record.computability_status is not ComputabilityStatus.EVALUABLE:
            close(EpisodeStatus.CENSORED,BoundaryCause.COMPUTABILITY_BREAK,record.record_id,record.not_evaluable_reason)
            excluded.append(NotEvaluableRecord(record.record_id,record.first_valid_time,record.computability_status,record.not_evaluable_reason or "UNSPECIFIED",record.source_sha256)); continue
        if record.reset_reason is not None: close(EpisodeStatus.CENSORED,BoundaryCause.RESET,record.record_id,record.reset_reason)
        changed=bool(active) and record.parent_record_id!=active_parent
        if changed: close(EpisodeStatus.INTERRUPTED,BoundaryCause.PARENT_CHANGE,record.record_id,"PARENT_RECORD_CHANGED")
        first=not active
        if first: active_parent=record.parent_record_id
        active.append(record); kinds.append(_phase(record,first,changed))
        if record.transition_kind in COMPLETION: close(EpisodeStatus.COMPLETED,BoundaryCause.COMPLETION,record.record_id,None)
    close(EpisodeStatus.OPEN_AT_CUTOFF,BoundaryCause.END_OF_INPUT,None,None)
    payload={"policy_id":POLICY_ID,"source_release_id":release,"instrument_id":instrument,"side":side,"scope_id":scope,"clock_id":clock,"build_cutoff":cutoff,"input_record_ids":ids,"input_source_sha256":[x.source_sha256 for x in values],"episode_ids":[x.episode_id for x in episodes],"not_evaluable":[x.to_dict() for x in excluded]}
    return EpisodeLedger(_id("C2E.LD.",payload),POLICY_ID,release,instrument,side,scope,clock,cutoff,tuple(ids),tuple(x.source_sha256 for x in values),tuple(episodes),tuple(excluded))

def build_nesting_ledger(episodes:Iterable[EpisodeRecord],requests:Iterable[EpisodeBindingRequest]) -> tuple[EpisodeBinding,...]:
    by_id={x.episode_id:x for x in episodes}
    if not by_id: raise ValueError("episodes are required")
    graph={key:set() for key in by_id}; bindings=[]
    for request in sorted(requests,key=lambda x:(x.child_episode_id,x.parent_episode_id,x.relation.value,x.first_valid_time)):
        if request.child_episode_id not in by_id or request.parent_episode_id not in by_id: raise ValueError("binding references unknown episode")
        child,parent=by_id[request.child_episode_id],by_id[request.parent_episode_id]
        if child.source_release_id!=parent.source_release_id or child.instrument_id!=parent.instrument_id or child.side!=parent.side: raise ValueError("cross-release, instrument or side parentage is forbidden")
        if _time(parent.start_first_valid_time)>_time(child.start_first_valid_time): raise ValueError("parent begins after child")
        if _time(request.first_valid_time)<_time(child.start_first_valid_time): raise ValueError("binding is valid before child episode")
        if _time(request.first_valid_time)>_time(child.end_first_valid_time): raise ValueError("binding is valid after child episode")
        if request.relation in {NestingRelation.NESTED_WITHIN,NestingRelation.CONTEXT_PARENT} and _time(child.end_first_valid_time)>_time(parent.end_first_valid_time): raise ValueError("child episode extends beyond parent interval")
        graph[request.child_episode_id].add(request.parent_episode_id); payload={"child_episode_id":request.child_episode_id,"parent_episode_id":request.parent_episode_id,"relation":request.relation.value,"first_valid_time":request.first_valid_time}
        bindings.append(EpisodeBinding(_id("C2E.BD.",payload),request.child_episode_id,request.parent_episode_id,request.relation,request.first_valid_time))
    visiting=set(); visited=set()
    def visit(node:str) -> None:
        if node in visiting: raise ValueError("episode nesting cycle")
        if node in visited:return
        visiting.add(node)
        for parent in sorted(graph[node]):visit(parent)
        visiting.remove(node); visited.add(node)
    for node in sorted(graph):visit(node)
    keys=[(x.child_episode_id,x.parent_episode_id,x.relation.value,x.first_valid_time) for x in bindings]
    if len(keys)!=len(set(keys)): raise ValueError("duplicate episode binding")
    return tuple(bindings)
