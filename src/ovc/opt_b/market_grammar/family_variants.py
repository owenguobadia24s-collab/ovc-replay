"""Deterministic C2G FamilyVariant, residual and counterexample ledger (shadow only)."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable,Mapping
from .family_hierarchy import AssignmentStatus,FamilyNode,SensitivityResult,StructuralRecord,_ds,weighted_distance
AUTHORITY_STATE='SHADOW_EXPERIMENT'; SCHEMA_VERSION='0.1'
def _bytes(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def _id(prefix,value): return prefix+sha256(_bytes(value)).hexdigest()
class VariantAssignmentStatus(str,Enum):
 VARIANT_ASSIGNED='VARIANT_ASSIGNED'; VARIANT_AMBIGUOUS='VARIANT_AMBIGUOUS'; FAMILY_RESIDUAL='FAMILY_RESIDUAL'; FAMILY_AMBIGUOUS='FAMILY_AMBIGUOUS'; FAMILY_UNASSIGNED='FAMILY_UNASSIGNED'; NOT_EVALUABLE='NOT_EVALUABLE'
@dataclass(frozen=True)
class FamilyVariant:
 variant_id:str; parent_family_id:str; pack_id:str; medoid_record_id:str; member_record_ids:tuple[str,...]; support:int; dispersion:str; invariant_core:tuple[tuple[str,str],...]; variation_ranges:tuple[tuple[str,str,str],...]; stability_status:str='STABLE_UNDER_PACK_CRITERIA'; authority_state:str=AUTHORITY_STATE
 def to_dict(self): return {'variant_id':self.variant_id,'parent_family_id':self.parent_family_id,'pack_id':self.pack_id,'medoid_record_id':self.medoid_record_id,'member_record_ids':list(self.member_record_ids),'support':self.support,'dispersion':self.dispersion,'invariant_core':[{'feature':k,'value':v} for k,v in self.invariant_core],'variation_ranges':[{'feature':k,'min':lo,'max':hi} for k,lo,hi in self.variation_ranges],'stability_status':self.stability_status,'authority_state':self.authority_state}
@dataclass(frozen=True)
class VariantExplanation:
 explanation_id:str; record_id:str; family_id:str|None; status:VariantAssignmentStatus; variant_id:str|None; candidate_variant_distances:tuple[tuple[str,str],...]; reason:str; authority_state:str=AUTHORITY_STATE
 def to_dict(self): return {'explanation_id':self.explanation_id,'record_id':self.record_id,'family_id':self.family_id,'status':self.status.value,'variant_id':self.variant_id,'candidate_variant_distances':[{'variant_id':v,'distance':d} for v,d in self.candidate_variant_distances],'reason':self.reason,'authority_state':self.authority_state}
@dataclass(frozen=True)
class CounterexampleRecord:
 counterexample_id:str; record_id:str; family_id:str|None; nearest_variant_id:str|None; nearest_variant_distance:str|None; reason:str
 def to_dict(self): return {'counterexample_id':self.counterexample_id,'record_id':self.record_id,'family_id':self.family_id,'nearest_variant_id':self.nearest_variant_id,'nearest_variant_distance':self.nearest_variant_distance,'reason':self.reason}
@dataclass(frozen=True)
class VariantLedger:
 ledger_id:str; sensitivity_result_id:str; pack_id:str; variants:tuple[FamilyVariant,...]; explanations:tuple[VariantExplanation,...]; counterexamples:tuple[CounterexampleRecord,...]; schema_version:str=SCHEMA_VERSION; authority_state:str=AUTHORITY_STATE
 def to_dict(self): return {'ledger_id':self.ledger_id,'sensitivity_result_id':self.sensitivity_result_id,'pack_id':self.pack_id,'variants':[x.to_dict() for x in self.variants],'explanations':[x.to_dict() for x in self.explanations],'counterexamples':[x.to_dict() for x in self.counterexamples],'schema_version':self.schema_version,'authority_state':self.authority_state}
def _summaries(records):
 keys=sorted(set.intersection(*(set(x.structural_features) for x in records))) if records else []
 invariant=[]; ranges=[]
 for key in keys:
  values=sorted({x.structural_features[key] for x in records})
  if len(values)==1: invariant.append((key,_ds(values[0])))
  else: ranges.append((key,_ds(values[0]),_ds(values[-1])))
 return tuple(invariant),tuple(ranges)
def _discover(family,by_id,result):
 if family.medoid_record_id not in family.member_record_ids: raise ValueError('family medoid must be a real member')
 pack=result.pack; remaining=set(family.member_record_ids); variants=[]
 while remaining:
  scored=[]
  for cid in sorted(remaining):
   candidate=by_id[cid]; covered=[]; total=Decimal('0')
   for oid in sorted(remaining):
    distance=weighted_distance(candidate,by_id[oid],pack)
    if distance is not None and distance<=pack.variant_radius: covered.append(oid); total+=distance
   scored.append((-len(covered),total,cid,tuple(covered)))
  _,_,medoid_id,members=min(scored)
  if len(members)<pack.minimum_support: break
  medoid=by_id[medoid_id]; distances=[weighted_distance(medoid,by_id[x],pack) for x in members]; exact=[x for x in distances if x is not None]; dispersion=sum(exact,Decimal('0'))/Decimal(len(exact))
  if dispersion>pack.variant_radius: raise ValueError('variant dispersion exceeds declared pack radius')
  inv,ranges=_summaries([by_id[x] for x in members]); payload={'parent_family_id':family.family_id,'pack_id':pack.pack_id,'medoid_record_id':medoid_id,'member_record_ids':list(members),'invariant_core':inv,'variation_ranges':ranges}; variant_id=_id('C2G.VAR.',payload)
  variants.append(FamilyVariant(variant_id,family.family_id,pack.pack_id,medoid_id,members,len(members),_ds(dispersion),inv,ranges)); remaining.difference_update(members)
 return variants
def build_variant_ledger(result:SensitivityResult,records:Iterable[StructuralRecord|Mapping[str,object]]):
 values=[x if isinstance(x,StructuralRecord) else StructuralRecord.from_mapping(x) for x in records]; values.sort(key=lambda x:x.record_id); by_id={x.record_id:x for x in values}
 if tuple(sorted(by_id))!=tuple(sorted(result.input_record_ids)): raise ValueError('variant input identities must exactly match sensitivity result')
 if len(by_id)!=len(values): raise ValueError('duplicate record_id')
 variants=[]
 for family in sorted(result.families,key=lambda x:x.family_id):
  if any(mid not in by_id for mid in family.member_record_ids): raise ValueError('family references unknown member')
  variants.extend(_discover(family,by_id,result))
 variants.sort(key=lambda x:(x.parent_family_id,x.variant_id)); by_family={}
 for variant in variants: by_family.setdefault(variant.parent_family_id,[]).append(variant)
 family_map={x.family_id:x for x in result.families}; assignment_map={x.record_id:x for x in result.assignments}; explanations=[]; counterexamples=[]
 for record in values:
  upstream=assignment_map[record.record_id]; family_id=upstream.primary_family_id
  if upstream.status is AssignmentStatus.NOT_EVALUABLE: status=VariantAssignmentStatus.NOT_EVALUABLE; variant_id=None; pairs=(); reason=upstream.reason
  elif upstream.status is AssignmentStatus.UNASSIGNED: status=VariantAssignmentStatus.FAMILY_UNASSIGNED; variant_id=None; pairs=(); reason=upstream.reason
  elif upstream.status is AssignmentStatus.AMBIGUOUS: status=VariantAssignmentStatus.FAMILY_AMBIGUOUS; variant_id=None; pairs=(); reason='UPSTREAM_FAMILY_ASSIGNMENT_AMBIGUOUS'
  else:
   candidates=[]
   for variant in by_family.get(family_id,[]):
    distance=weighted_distance(record,by_id[variant.medoid_record_id],result.pack)
    if distance is not None: candidates.append((distance,variant.variant_id))
   candidates.sort(key=lambda x:(x[0],x[1])); pairs=tuple((vid,_ds(distance)) for distance,vid in candidates); within=[x for x in candidates if x[0]<=result.pack.variant_radius]
   if not within: status=VariantAssignmentStatus.FAMILY_RESIDUAL; variant_id=None; reason='NO_STABLE_VARIANT_WITHIN_RADIUS'
   else:
    nearest,variant_id=within[0]; ambiguous=len(within)>1 and within[1][0]-nearest<=result.pack.ambiguity_margin; status=VariantAssignmentStatus.VARIANT_AMBIGUOUS if ambiguous else VariantAssignmentStatus.VARIANT_ASSIGNED; reason='MULTIPLE_VARIANTS_WITHIN_AMBIGUITY_MARGIN' if ambiguous else 'STABLE_VARIANT_WITHIN_RADIUS'
  payload={'record_id':record.record_id,'family_id':family_id,'status':status.value,'variant_id':variant_id,'candidate_variant_distances':pairs,'reason':reason}; explanations.append(VariantExplanation(_id('C2G.VEX.',payload),record.record_id,family_id,status,variant_id,pairs,reason))
  if status in {VariantAssignmentStatus.FAMILY_RESIDUAL,VariantAssignmentStatus.FAMILY_UNASSIGNED,VariantAssignmentStatus.FAMILY_AMBIGUOUS}:
   nearest_id=pairs[0][0] if pairs else None; nearest_distance=pairs[0][1] if pairs else None; cp={'record_id':record.record_id,'family_id':family_id,'nearest_variant_id':nearest_id,'nearest_variant_distance':nearest_distance,'reason':reason}; counterexamples.append(CounterexampleRecord(_id('C2G.CEX.',cp),record.record_id,family_id,nearest_id,nearest_distance,reason))
 payload={'sensitivity_result_id':result.result_id,'pack_id':result.pack.pack_id,'variant_ids':[x.variant_id for x in variants],'explanations':[x.to_dict() for x in explanations],'counterexamples':[x.to_dict() for x in counterexamples]}; return VariantLedger(_id('C2G.VLD.',payload),result.result_id,result.pack.pack_id,tuple(variants),tuple(explanations),tuple(counterexamples))
