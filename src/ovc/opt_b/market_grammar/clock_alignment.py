"""Deterministic 15M evaluation / 2H_A_L context as-of resolver (shadow only)."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable,Mapping
AUTHORITY_STATE='SHADOW_EXPERIMENT'
def _time(value):
 text=str(value).strip(); text=text[:-1]+'+00:00' if text.endswith('Z') else text; parsed=datetime.fromisoformat(text)
 if parsed.tzinfo is None: raise ValueError('timestamp must be timezone-aware')
 return parsed.astimezone(timezone.utc)
def _ctime(value): return _time(value).isoformat().replace('+00:00','Z')
def _id(prefix,value): return prefix+sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
class ContextStatus(str,Enum): AVAILABLE='AVAILABLE'; STALE='STALE'; UNAVAILABLE='UNAVAILABLE'; NOT_EVALUABLE='NOT_EVALUABLE'
@dataclass(frozen=True)
class ClockProfile:
 profile_id:str='MG-CLOCK-15M-WITH-2H_A_L-CONTEXT-v0.1'; child_clock_id:str='15M'; parent_clock_id:str='2H_A_L'; max_parent_age_seconds:int=7200; canonical:bool=False; authority_state:str=AUTHORITY_STATE
 def __post_init__(self):
  if self.canonical: raise ValueError('clock profile cannot be canonical')
  if self.child_clock_id!='15M' or self.parent_clock_id!='2H_A_L': raise ValueError('profile is frozen to 15M evaluation and 2H_A_L context')
  if self.max_parent_age_seconds!=7200: raise ValueError('profile max parent age is frozen at 7200 seconds')
 def to_dict(self): return {'profile_id':self.profile_id,'child_clock_id':self.child_clock_id,'parent_clock_id':self.parent_clock_id,'max_parent_age_seconds':self.max_parent_age_seconds,'canonical':False,'authority_state':self.authority_state}
@dataclass(frozen=True)
class ClockRecord:
 record_id:str; source_release_id:str; instrument_id:str; side:str; clock_id:str; first_valid_time:str; computability_status:str='EVALUABLE'; not_evaluable_reason:str|None=None
 def __post_init__(self):
  for field in ('record_id','source_release_id','instrument_id','clock_id'):
   if not str(getattr(self,field)).strip(): raise ValueError(f'{field} must be non-empty')
  object.__setattr__(self,'side',str(self.side).upper()); object.__setattr__(self,'first_valid_time',_ctime(self.first_valid_time)); object.__setattr__(self,'computability_status',str(self.computability_status).upper())
  if self.side not in {'BID','ASK'}: raise ValueError('side must be BID or ASK')
  if self.computability_status not in {'EVALUABLE','NOT_EVALUABLE'}: raise ValueError('invalid computability_status')
  if self.computability_status=='NOT_EVALUABLE' and not self.not_evaluable_reason: raise ValueError('NOT_EVALUABLE requires reason')
 @classmethod
 def from_mapping(cls,value):
  allowed={'record_id','source_release_id','instrument_id','side','clock_id','first_valid_time','computability_status','not_evaluable_reason'}; unknown=sorted(set(value)-allowed)
  if unknown: raise ValueError('unsupported clock record fields: '+', '.join(unknown))
  return cls(**dict(value))
@dataclass(frozen=True)
class ParentResolution:
 resolution_id:str; profile_id:str; child_record_id:str; status:ContextStatus; parent_record_id:str|None; child_first_valid_time:str; parent_first_valid_time:str|None; parent_age_seconds:int|None; reason:str; authority_state:str=AUTHORITY_STATE
 def to_dict(self): return {'resolution_id':self.resolution_id,'profile_id':self.profile_id,'child_record_id':self.child_record_id,'status':self.status.value,'parent_record_id':self.parent_record_id,'child_first_valid_time':self.child_first_valid_time,'parent_first_valid_time':self.parent_first_valid_time,'parent_age_seconds':self.parent_age_seconds,'reason':self.reason,'authority_state':self.authority_state}
@dataclass(frozen=True)
class AlignmentLedger:
 ledger_id:str; profile:ClockProfile; resolutions:tuple[ParentResolution,...]; authority_state:str=AUTHORITY_STATE
 def to_dict(self): return {'ledger_id':self.ledger_id,'profile':self.profile.to_dict(),'resolutions':[x.to_dict() for x in self.resolutions],'authority_state':self.authority_state}
def resolve_parent(child:ClockRecord|Mapping[str,object],parents:Iterable[ClockRecord|Mapping[str,object]],profile:ClockProfile=ClockProfile()):
 c=child if isinstance(child,ClockRecord) else ClockRecord.from_mapping(child)
 if c.clock_id!=profile.child_clock_id: raise ValueError('child record does not match profile child clock')
 values=[x if isinstance(x,ClockRecord) else ClockRecord.from_mapping(x) for x in parents]
 ids=[x.record_id for x in values]
 if len(ids)!=len(set(ids)): raise ValueError('duplicate parent record_id')
 exact=[x for x in values if x.source_release_id==c.source_release_id and x.instrument_id==c.instrument_id and x.side==c.side and x.clock_id==profile.parent_clock_id and _time(x.first_valid_time)<=_time(c.first_valid_time)]
 exact.sort(key=lambda x:(_time(x.first_valid_time),x.record_id))
 if not exact:
  status=ContextStatus.UNAVAILABLE; parent=None; age=None; reason='NO_EXACT_ASOF_PARENT'
 else:
  latest_time=_time(exact[-1].first_valid_time); same=[x for x in exact if _time(x.first_valid_time)==latest_time]
  if len(same)>1: raise ValueError('ambiguous exact parent at latest as-of timestamp')
  parent=same[0]; age=int((_time(c.first_valid_time)-_time(parent.first_valid_time)).total_seconds())
  if age<0: raise ValueError('parent_first_valid_time must not exceed child_first_valid_time')
  if parent.computability_status!='EVALUABLE': status=ContextStatus.NOT_EVALUABLE; reason=parent.not_evaluable_reason or 'PARENT_NOT_EVALUABLE'
  elif age>profile.max_parent_age_seconds: status=ContextStatus.STALE; reason='PARENT_AGE_EXCEEDS_PROFILE_LIMIT'
  else: status=ContextStatus.AVAILABLE; reason='LATEST_EXACT_ASOF_PARENT'
 payload={'profile_id':profile.profile_id,'child_record_id':c.record_id,'status':status.value,'parent_record_id':None if parent is None else parent.record_id,'child_first_valid_time':c.first_valid_time,'parent_first_valid_time':None if parent is None else parent.first_valid_time,'parent_age_seconds':age,'reason':reason}
 return ParentResolution(_id('MG.CLK.RES.',payload),profile.profile_id,c.record_id,status,None if parent is None else parent.record_id,c.first_valid_time,None if parent is None else parent.first_valid_time,age,reason)
def build_alignment_ledger(children,parents,profile=ClockProfile()):
 child_values=[x if isinstance(x,ClockRecord) else ClockRecord.from_mapping(x) for x in children]; parent_values=[x if isinstance(x,ClockRecord) else ClockRecord.from_mapping(x) for x in parents]; child_values.sort(key=lambda x:(_time(x.first_valid_time),x.record_id)); parent_values.sort(key=lambda x:(_time(x.first_valid_time),x.record_id))
 child_ids=[x.record_id for x in child_values]
 if len(child_ids)!=len(set(child_ids)): raise ValueError('duplicate child record_id')
 resolutions=tuple(resolve_parent(child,parent_values,profile) for child in child_values)
 for item in resolutions:
  if item.parent_first_valid_time is not None and _time(item.parent_first_valid_time)>_time(item.child_first_valid_time): raise ValueError('parent chronology violation')
 payload={'profile':profile.to_dict(),'child_record_ids':child_ids,'resolutions':[x.to_dict() for x in resolutions]}; return AlignmentLedger(_id('MG.CLK.LDG.',payload),profile,resolutions)
