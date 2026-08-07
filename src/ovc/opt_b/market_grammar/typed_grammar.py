"""Typed C2P grammar compiler and parser. Inactive shadow experiment only."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping,Sequence
AUTHORITY_STATE='SHADOW_EXPERIMENT'; SCHEMA_VERSION='0.1'
OPERATORS=frozenset({'ALL_OF','ANY_OF','SEQUENCE','WITHIN_N_OBSERVATIONS','SAME_OBJECT','RELATION_TRANSITION','RUN_LENGTH','CONTEXT_AVAILABILITY'})
LAYER_ORDER=('context','location','condition','episode_phase','event','response','transition','possible_resolution')
def _canon(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def _hash(value): return sha256(_canon(value).encode('utf-8')).hexdigest()
def _text(value,field):
 out=str(value).strip()
 if not out: raise ValueError(f'{field} must be non-empty')
 return out
class ParseStatus(str,Enum):
 NO_MATCH='NO_MATCH'; PARTIAL_MATCH='PARTIAL_MATCH'; AMBIGUOUS_MATCH='AMBIGUOUS_MATCH'; GRAMMAR_MATCH='GRAMMAR_MATCH'; GRAMMAR_CONTRADICTION='GRAMMAR_CONTRADICTION'; GRAMMAR_INVALIDATED='GRAMMAR_INVALIDATED'
@dataclass(frozen=True)
class ASTNode:
 operator:str; input_type:str; output_type:str; domain:str; required_fields:tuple[str,...]; children:tuple['ASTNode',...]; parameters:Mapping[str,object]
 @classmethod
 def from_mapping(cls,value):
  required={'operator','input_type','output_type','domain','required_fields','children','parameters'}; unknown=set(value)-required; missing=required-set(value)
  if unknown: raise ValueError('unsupported AST fields: '+', '.join(sorted(unknown)))
  if missing: raise ValueError('missing AST fields: '+', '.join(sorted(missing)))
  op=_text(value['operator'],'operator').upper()
  if op not in OPERATORS: raise ValueError(f'unsupported operator: {op}')
  node=cls(op,_text(value['input_type'],'input_type'),_text(value['output_type'],'output_type'),_text(value['domain'],'domain'),tuple(sorted({_text(x,'required_field') for x in value['required_fields']})),tuple(cls.from_mapping(x) for x in value['children']),MappingProxyType(dict(sorted(dict(value['parameters']).items()))))
  node.validate(); return node
 def validate(self):
  op=self.operator; n=len(self.children); p=self.parameters
  if op in {'ALL_OF','ANY_OF','SEQUENCE'} and n<1: raise ValueError(f'{op} requires at least one child')
  if op in {'WITHIN_N_OBSERVATIONS','RUN_LENGTH'} and n!=1: raise ValueError(f'{op} requires exactly one child')
  if op in {'RELATION_TRANSITION','CONTEXT_AVAILABILITY'} and n: raise ValueError(f'{op} does not accept children')
  if op=='SAME_OBJECT' and n<1: raise ValueError('SAME_OBJECT requires at least one child')
  if op=='WITHIN_N_OBSERVATIONS' and int(p.get('n',0))<1: raise ValueError('WITHIN_N_OBSERVATIONS requires positive n')
  if op=='SAME_OBJECT' and not p.get('binding'): raise ValueError('SAME_OBJECT requires binding')
  if op=='RELATION_TRANSITION' and not all(p.get(k) for k in ('from','to','object_binding')): raise ValueError('RELATION_TRANSITION requires from/to/object_binding')
  if op=='RUN_LENGTH':
   lo=int(p.get('min',0)); hi=int(p.get('max',0))
   if lo<1 or hi<lo: raise ValueError('RUN_LENGTH requires 1 <= min <= max')
  if op=='CONTEXT_AVAILABILITY' and p.get('required_state') not in {'AVAILABLE','STALE','UNAVAILABLE','NOT_EVALUABLE'}: raise ValueError('invalid CONTEXT_AVAILABILITY required_state')
  for child in self.children:
   if child.output_type!=self.input_type: raise ValueError(f'child type mismatch: {child.output_type} != {self.input_type}')
 def to_dict(self): return {'operator':self.operator,'input_type':self.input_type,'output_type':self.output_type,'domain':self.domain,'required_fields':list(self.required_fields),'children':[x.to_dict() for x in self.children],'parameters':dict(self.parameters)}
@dataclass(frozen=True)
class GrammarRelease:
 grammar_release_id:str; layers:Mapping[str,ASTNode|None]; invalidating_conditions:tuple[str,...]; release_sha256:str; canonical:bool=False; published:bool=False; authority_state:str=AUTHORITY_STATE
 @classmethod
 def from_mapping(cls,value):
  allowed={'grammar_release_id','layers','invalidating_conditions','release_sha256','canonical','published','authority_state'}; unknown=set(value)-allowed
  if unknown: raise ValueError('unsupported grammar release fields: '+', '.join(sorted(unknown)))
  if value.get('canonical') is True or value.get('published') is True: raise ValueError('candidate grammar fixture must be noncanonical and unpublished')
  raw_layers=dict(value['layers']); unknown_layers=set(raw_layers)-set(LAYER_ORDER)
  if unknown_layers: raise ValueError('unsupported grammar layer: '+', '.join(sorted(unknown_layers)))
  layers={name:(None if raw_layers.get(name) is None else ASTNode.from_mapping(raw_layers[name])) for name in LAYER_ORDER}
  invalid=tuple(sorted({_text(x,'invalidating_condition') for x in value.get('invalidating_conditions',[])})); release_id=_text(value['grammar_release_id'],'grammar_release_id')
  payload={'grammar_release_id':release_id,'layers':{k:(None if layers[k] is None else layers[k].to_dict()) for k in LAYER_ORDER},'invalidating_conditions':list(invalid),'canonical':False,'published':False,'authority_state':AUTHORITY_STATE}; expected=_hash(payload); supplied=_text(value['release_sha256'],'release_sha256').lower()
  if supplied!=expected: raise ValueError('grammar release hash mismatch')
  return cls(release_id,MappingProxyType(layers),invalid,supplied,False,False,AUTHORITY_STATE)
 def to_dict(self): return {'grammar_release_id':self.grammar_release_id,'layers':{k:(None if self.layers[k] is None else self.layers[k].to_dict()) for k in LAYER_ORDER},'invalidating_conditions':list(self.invalidating_conditions),'release_sha256':self.release_sha256,'canonical':False,'published':False,'authority_state':self.authority_state}
@dataclass(frozen=True)
class ParseResult:
 parse_id:str; status:ParseStatus; grammar_release_id:str; grammar_release_sha256:str; nearest_family_id:str|None; nearest_variant_id:str|None; family_distance:str|None; variant_distance:str|None; current_phases:tuple[str,...]; completed_phases:tuple[str,...]; lawful_next_phases:tuple[str,...]; missing_evidence:tuple[str,...]; conflicting_evidence:tuple[str,...]; invalidation_reasons:tuple[str,...]; upstream_lineage:tuple[str,...]; authority_state:str=AUTHORITY_STATE
 def to_dict(self): return {'parse_id':self.parse_id,'status':self.status.value,'grammar_release_id':self.grammar_release_id,'grammar_release_sha256':self.grammar_release_sha256,'nearest_family_id':self.nearest_family_id,'nearest_variant_id':self.nearest_variant_id,'family_distance':self.family_distance,'variant_distance':self.variant_distance,'current_phases':list(self.current_phases),'completed_phases':list(self.completed_phases),'lawful_next_phases':list(self.lawful_next_phases),'missing_evidence':list(self.missing_evidence),'conflicting_evidence':list(self.conflicting_evidence),'invalidation_reasons':list(self.invalidation_reasons),'upstream_lineage':list(self.upstream_lineage),'authority_state':self.authority_state}
def compile_grammar(value): return GrammarRelease.from_mapping(value)
def _eval(node:ASTNode,evidence):
 fields=dict(evidence.get('fields',{})); missing=[f for f in node.required_fields if f not in fields]; required_ok=not missing and all(bool(fields[f]) for f in node.required_fields)
 if node.operator=='CONTEXT_AVAILABILITY': return evidence.get('context_status')==node.parameters['required_state'],missing
 if node.operator=='RELATION_TRANSITION':
  target=(node.parameters['from'],node.parameters['to'],node.parameters['object_binding']); found=any((x.get('from'),x.get('to'),x.get('object_binding'))==target for x in evidence.get('transitions',[])); return required_ok and found,missing
 if node.operator in {'ALL_OF','ANY_OF'}:
  values=[_eval(child,evidence) for child in node.children]; child_missing=[m for _,ms in values for m in ms]; matched=all(x for x,_ in values) if node.operator=='ALL_OF' else any(x for x,_ in values); return required_ok and matched,missing+child_missing
 if node.operator=='SAME_OBJECT':
  if evidence.get('object_binding')!=node.parameters['binding']: return False,missing
  values=[_eval(child,evidence) for child in node.children]; return required_ok and all(x for x,_ in values),missing+[m for _,ms in values for m in ms]
 if node.operator in {'WITHIN_N_OBSERVATIONS','RUN_LENGTH','SEQUENCE'}:
  observations=list(evidence.get('observations',[]))
  def child_match(child,obs): return _eval(child,{**evidence,'fields':dict(obs)})[0]
  if node.operator=='WITHIN_N_OBSERVATIONS': return required_ok and any(child_match(node.children[0],obs) for obs in observations[-int(node.parameters['n']):]),missing
  if node.operator=='RUN_LENGTH':
   count=0
   for obs in reversed(observations):
    if child_match(node.children[0],obs): count+=1
    else: break
   return required_ok and int(node.parameters['min'])<=count<=int(node.parameters['max']),missing
  pos=0
  for child in node.children:
   found=False
   while pos<len(observations):
    if child_match(child,observations[pos]): found=True; pos+=1; break
    pos+=1
   if not found: return False,missing
  return required_ok,missing
 raise ValueError('unreachable operator')
def parse_grammar(grammar:GrammarRelease,evidence:Mapping[str,object]):
 invalid=tuple(sorted(set(map(str,evidence.get('invalidation_reasons',[]))) & set(grammar.invalidating_conditions))); conflicts=tuple(sorted(map(str,evidence.get('conflicting_evidence',[])))); missing=set(map(str,evidence.get('missing_evidence',[])))
 layer_results=[]
 for name in LAYER_ORDER:
  node=grammar.layers[name]
  if node is not None:
   matched,node_missing=_eval(node,evidence); missing.update(node_missing); layer_results.append((name,matched))
 if invalid: status=ParseStatus.GRAMMAR_INVALIDATED
 elif evidence.get('exclusive_conflict_proof') is True and conflicts: status=ParseStatus.GRAMMAR_CONTRADICTION
 else:
  matched=sum(1 for _,ok in layer_results if ok); total=len(layer_results)
  if total and matched==total: status=ParseStatus.AMBIGUOUS_MATCH if evidence.get('ambiguous_match') is True else ParseStatus.GRAMMAR_MATCH
  elif matched>0 or missing: status=ParseStatus.PARTIAL_MATCH
  else: status=ParseStatus.NO_MATCH
 payload={'grammar_release_id':grammar.grammar_release_id,'grammar_release_sha256':grammar.release_sha256,'status':status.value,'nearest_family_id':evidence.get('nearest_family_id'),'nearest_variant_id':evidence.get('nearest_variant_id'),'family_distance':evidence.get('family_distance'),'variant_distance':evidence.get('variant_distance'),'current_phases':sorted(map(str,evidence.get('current_phases',[]))),'completed_phases':sorted(map(str,evidence.get('completed_phases',[]))),'lawful_next_phases':sorted(map(str,evidence.get('lawful_next_phases',[]))),'missing_evidence':sorted(missing),'conflicting_evidence':list(conflicts),'invalidation_reasons':list(invalid),'upstream_lineage':sorted(map(str,evidence.get('upstream_lineage',[])))}
 return ParseResult('C2P.PARSE.'+_hash(payload),status,grammar.grammar_release_id,grammar.release_sha256,evidence.get('nearest_family_id'),evidence.get('nearest_variant_id'),evidence.get('family_distance'),evidence.get('variant_distance'),tuple(payload['current_phases']),tuple(payload['completed_phases']),tuple(payload['lawful_next_phases']),tuple(payload['missing_evidence']),conflicts,invalid,tuple(payload['upstream_lineage']))
