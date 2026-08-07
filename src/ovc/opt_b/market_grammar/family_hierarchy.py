"""Deterministic C2G sensitivity, assignment and hierarchy research (shadow only)."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from enum import Enum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence
SCHEMA_VERSION='0.1'; METRIC_ID='WEIGHTED_MANHATTAN_V0_1'; AUTHORITY_STATE='SHADOW_EXPERIMENT'; Q=Decimal('0.000000000001')
ALLOWED_RECORD_TYPES=frozenset({'STATE','TRANSITION','EPISODE'})
ALLOWED_TOP_LEVEL=frozenset({'record_id','record_type','source_release_id','instrument_id','side','scope_id','clock_id','first_valid_time','source_sha256','structural_features','computability_status','not_evaluable_reason'})
FORBIDDEN_TOP_LEVEL=frozenset({'family_id','variant_id','grammar_id','parse_id','outcome','outcome_id','return','returns','mfe','mae','future_price','future_path','probability','risk','exposure','execution','trade_label','semantic_label'})
FORBIDDEN_FEATURE_TOKENS=('source_','provider','manifest','record_id','sha','hash','clock','computability','missing','censor','outcome','return','mfe','mae','future','probability','risk','exposure','execution','trade','semantic')

def _text(value,field,upper=False):
    result=str(value).strip()
    if not result: raise ValueError(f'{field} must be non-empty')
    return result.upper() if upper else result

def _time(value,field='first_valid_time'):
    text=_text(value,field)
    if text.endswith('Z'): text=text[:-1]+'+00:00'
    try: parsed=datetime.fromisoformat(text)
    except ValueError as exc: raise ValueError(f'{field} must be ISO-8601') from exc
    if parsed.tzinfo is None: raise ValueError(f'{field} must be timezone-aware')
    return parsed.astimezone(timezone.utc)

def _ctime(value): return _time(value).isoformat().replace('+00:00','Z')
def _dec(value,field,lo=Decimal('0'),hi=Decimal('1')):
    try: result=Decimal(str(value))
    except (InvalidOperation,ValueError) as exc: raise ValueError(f'{field} must be decimal') from exc
    if not result.is_finite() or result<lo or result>hi: raise ValueError(f'{field} must be in [{lo},{hi}]')
    return result.quantize(Q,rounding=ROUND_HALF_EVEN)
def _ds(value):
    text=format(value.quantize(Q,rounding=ROUND_HALF_EVEN),'f').rstrip('0').rstrip('.')
    return text or '0'
def _bytes(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def _id(prefix,value): return prefix+sha256(_bytes(value)).hexdigest()
def _feature_key(value):
    key=_text(value,'feature_key').lower()
    if any(token in key for token in FORBIDDEN_FEATURE_TOKENS): raise ValueError(f'non-structural feature is forbidden: {key}')
    return key

class AssignmentStatus(str,Enum):
    ASSIGNED='ASSIGNED'; AMBIGUOUS='AMBIGUOUS'; RESIDUAL='RESIDUAL'; UNASSIGNED='UNASSIGNED'; NOT_EVALUABLE='NOT_EVALUABLE'
class HierarchyRelation(str,Enum):
    PARENT_OF='PARENT_OF'; PARTIAL_OVERLAP_WITH='PARTIAL_OVERLAP_WITH'

@dataclass(frozen=True)
class SensitivityPack:
    pack_id:str; sensitivity:Decimal; feature_weights:Mapping[str,Decimal]; assignment_radius:Decimal; ambiguity_margin:Decimal; minimum_support:int; variant_radius:Decimal; containment_threshold:Decimal; partial_overlap_threshold:Decimal; missingness_policy:str='NOT_EVALUABLE'; metric_id:str=METRIC_ID; tie_break:str='MAX_COVERAGE_MIN_TOTAL_DISTANCE_LEXICOGRAPHIC_ID'; canonical:bool=False
    def __post_init__(self):
        object.__setattr__(self,'pack_id',_text(self.pack_id,'pack_id')); object.__setattr__(self,'sensitivity',_dec(self.sensitivity,'sensitivity'))
        weights={_feature_key(k):_dec(v,f'feature_weights.{k}',Decimal('0.000000000001')) for k,v in self.feature_weights.items()}; object.__setattr__(self,'feature_weights',MappingProxyType(dict(sorted(weights.items()))))
        for field in ('assignment_radius','ambiguity_margin','variant_radius','containment_threshold','partial_overlap_threshold'): object.__setattr__(self,field,_dec(getattr(self,field),field))
        object.__setattr__(self,'minimum_support',int(self.minimum_support)); object.__setattr__(self,'missingness_policy',_text(self.missingness_policy,'missingness_policy',True)); object.__setattr__(self,'metric_id',_text(self.metric_id,'metric_id',True)); object.__setattr__(self,'tie_break',_text(self.tie_break,'tie_break',True))
        if self.canonical: raise ValueError('sensitivity packs cannot be canonical')
        if not self.feature_weights: raise ValueError('feature_weights must be non-empty')
        if self.minimum_support<2: raise ValueError('minimum_support must be at least 2')
        if self.missingness_policy!='NOT_EVALUABLE': raise ValueError('missingness_policy must be NOT_EVALUABLE')
        if self.metric_id!=METRIC_ID: raise ValueError(f'metric_id must be {METRIC_ID}')
        if self.tie_break!='MAX_COVERAGE_MIN_TOTAL_DISTANCE_LEXICOGRAPHIC_ID': raise ValueError('unsupported tie_break')
        if self.ambiguity_margin>self.assignment_radius: raise ValueError('ambiguity_margin cannot exceed assignment_radius')
    @classmethod
    def from_mapping(cls,value):
        allowed={'pack_id','sensitivity','feature_weights','assignment_radius','ambiguity_margin','minimum_support','variant_radius','containment_threshold','partial_overlap_threshold','missingness_policy','metric_id','tie_break','canonical'}; unknown=sorted(set(value)-allowed)
        if unknown: raise ValueError('unsupported sensitivity pack fields: '+', '.join(unknown))
        return cls(**dict(value))
    def to_dict(self):
        return {'pack_id':self.pack_id,'sensitivity':_ds(self.sensitivity),'feature_weights':{k:_ds(v) for k,v in self.feature_weights.items()},'assignment_radius':_ds(self.assignment_radius),'ambiguity_margin':_ds(self.ambiguity_margin),'minimum_support':self.minimum_support,'variant_radius':_ds(self.variant_radius),'containment_threshold':_ds(self.containment_threshold),'partial_overlap_threshold':_ds(self.partial_overlap_threshold),'missingness_policy':self.missingness_policy,'metric_id':self.metric_id,'tie_break':self.tie_break,'canonical':False}

@dataclass(frozen=True)
class StructuralRecord:
    record_id:str; record_type:str; source_release_id:str; instrument_id:str; side:str; scope_id:str; clock_id:str; first_valid_time:str; source_sha256:str; structural_features:Mapping[str,Decimal]; computability_status:str='EVALUABLE'; not_evaluable_reason:str|None=None
    def __post_init__(self):
        for field in ('record_id','source_release_id','instrument_id','scope_id','clock_id'): object.__setattr__(self,field,_text(getattr(self,field),field))
        object.__setattr__(self,'record_type',_text(self.record_type,'record_type',True)); object.__setattr__(self,'side',_text(self.side,'side',True)); object.__setattr__(self,'first_valid_time',_ctime(self.first_valid_time))
        digest=_text(self.source_sha256,'source_sha256').lower()
        if len(digest)!=64 or any(ch not in '0123456789abcdef' for ch in digest): raise ValueError('source_sha256 must be lowercase SHA-256 hex')
        object.__setattr__(self,'source_sha256',digest); features={_feature_key(k):_dec(v,f'structural_features.{k}') for k,v in self.structural_features.items()}; object.__setattr__(self,'structural_features',MappingProxyType(dict(sorted(features.items())))); object.__setattr__(self,'computability_status',_text(self.computability_status,'computability_status',True))
        if self.not_evaluable_reason is not None: object.__setattr__(self,'not_evaluable_reason',_text(self.not_evaluable_reason,'not_evaluable_reason'))
        if self.record_type not in ALLOWED_RECORD_TYPES: raise ValueError(f'unsupported record_type: {self.record_type}')
        if self.side not in {'BID','ASK'}: raise ValueError('side must be BID or ASK')
        if self.computability_status not in {'EVALUABLE','NOT_EVALUABLE'}: raise ValueError('computability_status must be EVALUABLE or NOT_EVALUABLE')
        if self.computability_status=='EVALUABLE' and self.not_evaluable_reason is not None: raise ValueError('EVALUABLE record cannot have not_evaluable_reason')
        if self.computability_status=='NOT_EVALUABLE' and self.not_evaluable_reason is None: raise ValueError('NOT_EVALUABLE record requires not_evaluable_reason')
    @classmethod
    def from_mapping(cls,value):
        keys=set(value); forbidden=sorted(keys&FORBIDDEN_TOP_LEVEL); unknown=sorted(keys-ALLOWED_TOP_LEVEL)
        if forbidden: raise ValueError('future/outcome/downstream fields are forbidden: '+', '.join(forbidden))
        if unknown: raise ValueError('unsupported structural record fields: '+', '.join(unknown))
        return cls(**dict(value))
    @property
    def scope_key(self): return (self.source_release_id,self.instrument_id,self.side,self.scope_id,self.clock_id,self.record_type)

@dataclass(frozen=True)
class FamilyNode:
    family_id:str; pack_id:str; sensitivity:str; source_release_id:str; instrument_id:str; side:str; scope_id:str; clock_id:str; record_type:str; medoid_record_id:str; member_record_ids:tuple[str,...]; dispersion:str; authority_state:str=AUTHORITY_STATE
    def to_dict(self): return {'family_id':self.family_id,'pack_id':self.pack_id,'sensitivity':self.sensitivity,'source_release_id':self.source_release_id,'instrument_id':self.instrument_id,'side':self.side,'scope_id':self.scope_id,'clock_id':self.clock_id,'record_type':self.record_type,'medoid_record_id':self.medoid_record_id,'member_record_ids':list(self.member_record_ids),'dispersion':self.dispersion,'authority_state':self.authority_state}
@dataclass(frozen=True)
class AssignmentRecord:
    assignment_id:str; pack_id:str; record_id:str; status:AssignmentStatus; primary_family_id:str|None; nearest_distance:str|None; candidate_distances:tuple[tuple[str,str],...]; reason:str; authority_state:str=AUTHORITY_STATE
    def to_dict(self): return {'assignment_id':self.assignment_id,'pack_id':self.pack_id,'record_id':self.record_id,'status':self.status.value,'primary_family_id':self.primary_family_id,'nearest_distance':self.nearest_distance,'candidate_distances':[{'family_id':f,'distance':d} for f,d in self.candidate_distances],'reason':self.reason,'authority_state':self.authority_state}
@dataclass(frozen=True)
class SensitivityResult:
    result_id:str; pack:SensitivityPack; build_cutoff:str; input_record_ids:tuple[str,...]; families:tuple[FamilyNode,...]; assignments:tuple[AssignmentRecord,...]; authority_state:str=AUTHORITY_STATE
    def to_dict(self): return {'result_id':self.result_id,'pack':self.pack.to_dict(),'build_cutoff':self.build_cutoff,'input_record_ids':list(self.input_record_ids),'families':[x.to_dict() for x in self.families],'assignments':[x.to_dict() for x in self.assignments],'schema_version':SCHEMA_VERSION,'authority_state':self.authority_state}
@dataclass(frozen=True)
class HierarchyEdge:
    edge_id:str; relation:HierarchyRelation; parent_family_id:str; child_family_id:str; parent_pack_id:str; child_pack_id:str; parent_sensitivity:str; child_sensitivity:str; containment:str; jaccard:str; medoid_persisted:bool; directional:bool
    def to_dict(self): return {'edge_id':self.edge_id,'relation':self.relation.value,'parent_family_id':self.parent_family_id,'child_family_id':self.child_family_id,'parent_pack_id':self.parent_pack_id,'child_pack_id':self.child_pack_id,'parent_sensitivity':self.parent_sensitivity,'child_sensitivity':self.child_sensitivity,'containment':self.containment,'jaccard':self.jaccard,'medoid_persisted':self.medoid_persisted,'directional':self.directional}
@dataclass(frozen=True)
class HierarchyLedger:
    hierarchy_id:str; result_ids:tuple[str,...]; edges:tuple[HierarchyEdge,...]; split_events:tuple[dict,...]; merge_events:tuple[dict,...]; adjacent_metrics:tuple[dict,...]; authority_state:str=AUTHORITY_STATE
    def to_dict(self): return {'hierarchy_id':self.hierarchy_id,'result_ids':list(self.result_ids),'edges':[x.to_dict() for x in self.edges],'split_events':list(self.split_events),'merge_events':list(self.merge_events),'adjacent_metrics':list(self.adjacent_metrics),'schema_version':SCHEMA_VERSION,'authority_state':self.authority_state}

def weighted_distance(left,right,pack):
    if left.scope_key!=right.scope_key: raise ValueError('distance requires exact matching release/instrument/side/scope/clock/type')
    if left.computability_status!='EVALUABLE' or right.computability_status!='EVALUABLE': return None
    keys=tuple(pack.feature_weights)
    if any(k not in left.structural_features or k not in right.structural_features for k in keys): return None
    total=sum(pack.feature_weights.values(),Decimal('0')); distance=sum((pack.feature_weights[k]*abs(left.structural_features[k]-right.structural_features[k]) for k in keys),Decimal('0'))/total
    return distance.quantize(Q,rounding=ROUND_HALF_EVEN)

def _family(scope_records,pack):
    by_id={x.record_id:x for x in scope_records}; remaining=set(by_id); families=[]; greedy={}
    while remaining:
        scored=[]
        for cid in sorted(remaining):
            covered=[]; total=Decimal('0'); candidate=by_id[cid]
            for oid in sorted(remaining):
                distance=weighted_distance(candidate,by_id[oid],pack)
                if distance is not None and distance<=pack.assignment_radius: covered.append(oid); total+=distance
            scored.append((-len(covered),total.quantize(Q),cid,tuple(covered)))
        _,_,medoid_id,members=min(scored)
        if len(members)<pack.minimum_support: break
        medoid=by_id[medoid_id]; exact=[weighted_distance(medoid,by_id[item],pack) for item in members]; dispersion=sum((x for x in exact if x is not None),Decimal('0'))/Decimal(len(exact)); scope=medoid.scope_key
        payload={'pack_id':pack.pack_id,'sensitivity':_ds(pack.sensitivity),'scope':scope,'medoid_record_id':medoid_id,'member_record_ids':list(members),'metric_id':pack.metric_id}; family_id=_id('C2G.FAM.',payload)
        families.append(FamilyNode(family_id,pack.pack_id,_ds(pack.sensitivity),scope[0],scope[1],scope[2],scope[3],scope[4],scope[5],medoid_id,members,_ds(dispersion)))
        for item in members: greedy[item]=family_id
        remaining.difference_update(members)
    return families,greedy

def build_sensitivity_result(records,pack,*,build_cutoff):
    active=pack if isinstance(pack,SensitivityPack) else SensitivityPack.from_mapping(pack); cutoff=_ctime(build_cutoff); values=[x if isinstance(x,StructuralRecord) else StructuralRecord.from_mapping(x) for x in records]
    if not values: raise ValueError('at least one structural record is required')
    values.sort(key=lambda x:(_time(x.first_valid_time),x.record_id)); ids=[x.record_id for x in values]
    if len(ids)!=len(set(ids)): raise ValueError('duplicate record_id')
    if any(_time(x.first_valid_time)>_time(cutoff) for x in values): raise ValueError('future structural record exceeds build_cutoff')
    reasons={}; by_scope={}; required=set(active.feature_weights)
    for record in values:
        if record.computability_status!='EVALUABLE': reasons[record.record_id]=record.not_evaluable_reason or 'NOT_EVALUABLE'; continue
        missing=sorted(required-set(record.structural_features))
        if missing: reasons[record.record_id]='MISSING_STRUCTURAL_FEATURES:'+','.join(missing); continue
        by_scope.setdefault(record.scope_key,[]).append(record)
    families=[]; greedy={}
    for scope in sorted(by_scope):
        built,membership=_family(by_scope[scope],active); families.extend(built); greedy.update(membership)
    families.sort(key=lambda x:(x.pack_id,x.source_release_id,x.instrument_id,x.side,x.scope_id,x.clock_id,x.record_type,x.family_id)); record_by_id={x.record_id:x for x in values}; fs={}
    for family in families: fs.setdefault((family.source_release_id,family.instrument_id,family.side,family.scope_id,family.clock_id,family.record_type),[]).append(family)
    medoids={f.family_id:record_by_id[f.medoid_record_id] for f in families}; assignments=[]
    for record in sorted(values,key=lambda x:x.record_id):
        if record.record_id in reasons:
            payload={'pack_id':active.pack_id,'record_id':record.record_id,'status':'NOT_EVALUABLE','reason':reasons[record.record_id]}; assignments.append(AssignmentRecord(_id('C2G.ASN.',payload),active.pack_id,record.record_id,AssignmentStatus.NOT_EVALUABLE,None,None,(),reasons[record.record_id])); continue
        candidates=[]
        for family in fs.get(record.scope_key,[]):
            distance=weighted_distance(record,medoids[family.family_id],active)
            if distance is not None: candidates.append((distance,family.family_id))
        candidates.sort(key=lambda x:(x[0],x[1])); within=[x for x in candidates if x[0]<=active.assignment_radius]
        if not within: status=AssignmentStatus.UNASSIGNED; primary=None; nearest=candidates[0][0] if candidates else None; reason='NO_FAMILY_WITHIN_RADIUS'
        else:
            nearest,primary=within[0]; ambiguous=len(within)>1 and within[1][0]-nearest<=active.ambiguity_margin; status=AssignmentStatus.AMBIGUOUS if ambiguous else AssignmentStatus.ASSIGNED; reason='MULTIPLE_FAMILIES_WITHIN_AMBIGUITY_MARGIN' if ambiguous else 'UNIQUE_NEAREST_FAMILY'
        pairs=tuple((fid,_ds(distance)) for distance,fid in candidates); payload={'pack_id':active.pack_id,'record_id':record.record_id,'status':status.value,'primary_family_id':primary,'nearest_distance':None if nearest is None else _ds(nearest),'candidate_distances':pairs,'reason':reason,'greedy_family_id':greedy.get(record.record_id)}
        assignments.append(AssignmentRecord(_id('C2G.ASN.',payload),active.pack_id,record.record_id,status,primary,None if nearest is None else _ds(nearest),pairs,reason))
    payload={'pack':active.to_dict(),'build_cutoff':cutoff,'input_record_ids':ids,'family_ids':[x.family_id for x in families],'assignments':[x.to_dict() for x in assignments]}
    return SensitivityResult(_id('C2G.RES.',payload),active,cutoff,tuple(ids),tuple(families),tuple(assignments))

def _overlap(left,right):
    a,b=set(left.member_record_ids),set(right.member_record_ids); n=len(a&b)
    if not n: return Decimal('0'),Decimal('0'),0
    return (Decimal(n)/Decimal(min(len(a),len(b)))).quantize(Q),(Decimal(n)/Decimal(len(a|b))).quantize(Q),n
def _scope(f): return (f.source_release_id,f.instrument_id,f.side,f.scope_id,f.clock_id,f.record_type)
def _assigned(result): return {x.record_id:x.primary_family_id for x in result.assignments if x.status in {AssignmentStatus.ASSIGNED,AssignmentStatus.AMBIGUOUS}}
def _acyclic(edges):
    graph={}
    for edge in edges:
        if not edge.directional: continue
        if Decimal(edge.parent_sensitivity)<=Decimal(edge.child_sensitivity): raise ValueError('directional hierarchy must descend from higher to lower sensitivity')
        graph.setdefault(edge.parent_family_id,set()).add(edge.child_family_id); graph.setdefault(edge.child_family_id,set())
    visiting=set(); visited=set()
    def visit(node):
        if node in visiting: raise ValueError('directional family hierarchy contains a cycle')
        if node in visited: return
        visiting.add(node)
        for child in sorted(graph.get(node,())): visit(child)
        visiting.remove(node); visited.add(node)
    for node in sorted(graph): visit(node)

def build_hierarchy(results):
    values=sorted(results,key=lambda x:(x.pack.sensitivity,x.pack.pack_id))
    if len(values)<2: raise ValueError('at least two sensitivity results are required')
    if len({x.pack.pack_id for x in values})!=len(values): raise ValueError('duplicate sensitivity pack')
    if len({x.pack.sensitivity for x in values})!=len(values): raise ValueError('duplicate sensitivity value')
    if len({x.input_record_ids for x in values})!=1: raise ValueError('hierarchy results must use identical input record identities')
    if len({x.build_cutoff for x in values})!=1: raise ValueError('hierarchy results must use identical build_cutoff')
    edges=[]; splits=[]; merges=[]; metrics=[]
    for lower,higher in zip(values,values[1:]):
        pair=[]; threshold=max(lower.pack.containment_threshold,higher.pack.containment_threshold); partial=max(lower.pack.partial_overlap_threshold,higher.pack.partial_overlap_threshold)
        for parent in higher.families:
            for child in lower.families:
                if _scope(parent)!=_scope(child): continue
                containment,jaccard,n=_overlap(parent,child)
                if not n: continue
                if containment>=threshold: relation=HierarchyRelation.PARENT_OF; directional=True; pid,cid=parent.family_id,child.family_id
                elif jaccard>=partial: relation=HierarchyRelation.PARTIAL_OVERLAP_WITH; directional=False; pid,cid=sorted((parent.family_id,child.family_id))
                else: continue
                payload={'relation':relation.value,'parent_family_id':pid,'child_family_id':cid,'parent_pack_id':higher.pack.pack_id,'child_pack_id':lower.pack.pack_id,'parent_sensitivity':_ds(higher.pack.sensitivity),'child_sensitivity':_ds(lower.pack.sensitivity),'containment':_ds(containment),'jaccard':_ds(jaccard)}
                pair.append(HierarchyEdge(_id('C2G.EDGE.',payload),relation,pid,cid,higher.pack.pack_id,lower.pack.pack_id,_ds(higher.pack.sensitivity),_ds(lower.pack.sensitivity),_ds(containment),_ds(jaccard),parent.medoid_record_id in child.member_record_ids or child.medoid_record_id in parent.member_record_ids,directional))
        pair.sort(key=lambda x:(x.relation.value,x.parent_family_id,x.child_family_id,x.edge_id)); edges.extend(pair); directional=[x for x in pair if x.directional]; cp={}; pc={}
        for edge in directional: cp.setdefault(edge.parent_family_id,[]).append(edge.child_family_id); pc.setdefault(edge.child_family_id,[]).append(edge.parent_family_id)
        for fid,children in sorted(cp.items()):
            if len(set(children))>=2: splits.append({'event_id':_id('C2G.SPLIT.',{'parent':fid,'children':sorted(set(children)),'higher':higher.pack.pack_id,'lower':lower.pack.pack_id}),'parent_family_id':fid,'child_family_ids':sorted(set(children)),'higher_pack_id':higher.pack.pack_id,'lower_pack_id':lower.pack.pack_id})
        for fid,parents in sorted(pc.items()):
            if len(set(parents))>=2: merges.append({'event_id':_id('C2G.MERGE.',{'child':fid,'parents':sorted(set(parents)),'higher':higher.pack.pack_id,'lower':lower.pack.pack_id}),'child_family_id':fid,'parent_family_ids':sorted(set(parents)),'higher_pack_id':higher.pack.pack_id,'lower_pack_id':lower.pack.pack_id})
        lm,hm=_assigned(lower),_assigned(higher); shared=sorted(set(lm)&set(hm)); pairs={(x.parent_family_id,x.child_family_id) for x in directional}; stable=sum(1 for rid in shared if (hm[rid],lm[rid]) in pairs); reassignment=Decimal('0') if not shared else Decimal(len(shared)-stable)/Decimal(len(shared))
        metrics.append({'higher_pack_id':higher.pack.pack_id,'lower_pack_id':lower.pack.pack_id,'directional_edge_count':len(directional),'partial_overlap_edge_count':sum(1 for x in pair if not x.directional),'surviving_family_count':len({x.parent_family_id for x in directional}),'medoid_persistence_count':sum(1 for x in directional if x.medoid_persisted),'reassignment_rate':_ds(reassignment)})
    edges.sort(key=lambda x:(Decimal(x.parent_sensitivity),x.relation.value,x.parent_family_id,x.child_family_id),reverse=True); _acyclic(edges); payload={'result_ids':[x.result_id for x in values],'edge_ids':[x.edge_id for x in edges],'split_events':splits,'merge_events':merges,'adjacent_metrics':metrics}
    return HierarchyLedger(_id('C2G.HIER.',payload),tuple(x.result_id for x in values),tuple(edges),tuple(splits),tuple(merges),tuple(metrics))
