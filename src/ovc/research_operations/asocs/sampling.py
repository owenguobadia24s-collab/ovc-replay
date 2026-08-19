from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

UPPER_EXACT_CONSTRUCTS = (
    "C2_OBSERVATION", "C2_HORIZON", "C2_LEVEL", "C2_CONTAINER", "C2_RELATION",
    "C2_FORMULA", "C2_TRANSITION", "C2_PARENT_CONTEXT", "C2_COMPUTABILITY",
    "C2E_EPISODE", "C2E_PHASE", "OCCURRENCE_CONTEXT_ATTACHMENT",
)
TARGET_MONTHS = tuple(f"2026-{m:02d}" for m in range(1, 7))

class ASOCSSamplingError(ValueError):
    pass

def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()

def file_sha256(path: str | Path) -> str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def read_gzip_jsonl(path: str | Path, *, expected_sha256: str) -> list[dict[str, Any]]:
    path=Path(path)
    actual=file_sha256(path)
    if actual != expected_sha256:
        raise ASOCSSamplingError(f"INPUT_HASH_MISMATCH:{path.name}:{actual}")
    out=[]
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for i,line in enumerate(f,1):
            try: value=json.loads(line)
            except json.JSONDecodeError as e: raise ASOCSSamplingError(f"INVALID_JSONL:{path.name}:{i}") from e
            if not isinstance(value, dict): raise ASOCSSamplingError(f"NON_OBJECT_JSONL:{path.name}:{i}")
            out.append(value)
    return out

def selection_score(population_hash: str, nonce_hex: str, stratum_id: str, object_id: str) -> str:
    return hashlib.sha256((population_hash + nonce_hex + stratum_id + object_id).encode('utf-8')).hexdigest()

def _unique_rows(objects: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows=[dict(x) for x in objects]
    ids=[str(x['object_id']) for x in rows]
    if len(ids) != len(set(ids)): raise ASOCSSamplingError('DUPLICATE_OBJECT_ID')
    return rows

def select_frame(objects: Iterable[Mapping[str, Any]], *, population_hash: str, nonce_hex: str, stratum_id: str, target_size: int) -> dict[str, Any]:
    if target_size < 0: raise ASOCSSamplingError('NEGATIVE_TARGET_SIZE')
    rows=_unique_rows(objects)
    ranked=sorted(rows, key=lambda row:(selection_score(population_hash,nonce_hex,stratum_id,str(row['object_id'])),str(row['object_id'])))
    exhausted=len(ranked)<target_size
    chosen=ranked if exhausted else ranked[:target_size]
    return {
      'stratum_id':stratum_id,'target_size':target_size,'eligible_count':len(ranked),'selection_count':len(chosen),
      'exhaustion':'STRATUM_EXHAUSTED_FULL_CENSUS' if exhausted else 'TARGET_FILLED',
      'object_ids':[str(x['object_id']) for x in chosen],
      'scores':{str(x['object_id']):selection_score(population_hash,nonce_hex,stratum_id,str(x['object_id'])) for x in chosen},
    }

def full_census_frame(objects: Iterable[Mapping[str, Any]], *, population_hash: str, nonce_hex: str, stratum_id: str, reason: str) -> dict[str, Any]:
    rows=_unique_rows(objects)
    ranked=sorted(rows, key=lambda row:(selection_score(population_hash,nonce_hex,stratum_id,str(row['object_id'])),str(row['object_id'])))
    return {
      'stratum_id':stratum_id,'target_size':'FULL_CENSUS','eligible_count':len(ranked),'selection_count':len(ranked),
      'exhaustion':'FULL_CENSUS_NONNUMERIC_DESIGN_FRAME','full_census_reason':reason,
      'object_ids':[str(x['object_id']) for x in ranked],
      'scores':{str(x['object_id']):selection_score(population_hash,nonce_hex,stratum_id,str(x['object_id'])) for x in ranked},
    }

def unavailable_frame(*, stratum_id: str, design_target: Any, reason: str) -> dict[str, Any]:
    return {'stratum_id':stratum_id,'design_target':design_target,'eligible_count':0,'selection_count':0,
            'exhaustion':'STRATUM_UNAVAILABLE_EXACT_ACTIVE_INTERFACE','reason':reason,'object_ids':[],'scores':{}}

def blind_case_id(population_hash: str, nonce_hex: str, review_unit_id: str, *, repeat: bool=False) -> str:
    label='HIDDEN_REPEAT_CASE' if repeat else 'PRIMARY_BLIND_CASE'
    digest=hashlib.sha256((population_hash+nonce_hex+label+review_unit_id).encode()).hexdigest()
    return 'ASOCS.BLIND.'+digest[:24]

def _literal_dt(s: str) -> datetime:
    # Supports G1 literal "YYYYMMDD HH:MM:SS" and trace ISO-naive.
    if len(s)>=19 and s[4]=='-': return datetime.strptime(s[:19],'%Y-%m-%dT%H:%M:%S')
    return datetime.strptime(s,'%Y%m%d %H:%M:%S')

def _iso(dt: datetime) -> str: return dt.strftime('%Y-%m-%dT%H:%M:%S')

def anchor_windows(anchor: datetime) -> dict[str, dict[str,str]]:
    return {
      'LOCAL':{'start':_iso(anchor-timedelta(hours=8)),'end':_iso(anchor+timedelta(hours=8))},
      'DEVELOPMENT':{'start':_iso(anchor-timedelta(days=2)),'end':_iso(anchor+timedelta(days=2))},
      'WIDER':{'start':_iso(anchor-timedelta(days=5)),'end':_iso(anchor+timedelta(days=5))},
    }

def gap_windows(previous: datetime, next_: datetime) -> dict[str, dict[str,str]]:
    return {
      'LOCAL':{'start':_iso(previous-timedelta(hours=8)),'end':_iso(next_+timedelta(hours=8))},
      'DEVELOPMENT':{'start':_iso(previous-timedelta(days=2)),'end':_iso(next_+timedelta(days=2))},
      'WIDER':{'start':_iso(previous-timedelta(days=5)),'end':_iso(next_+timedelta(days=5))},
    }

def _check_upper_fail_closed(target_traces: Sequence[Mapping[str,Any]]) -> dict[str,int]:
    counts={k:0 for k in UPPER_EXACT_CONSTRUCTS}
    for t in target_traces:
        upper=t.get('upper_stack')
        if not isinstance(upper, Mapping): raise ASOCSSamplingError('UPPER_STACK_MISSING')
        for k in UPPER_EXACT_CONSTRUCTS:
            v=upper.get(k)
            if not isinstance(v, Mapping): raise ASOCSSamplingError('UPPER_CONSTRUCT_MISSING:'+k)
            if v.get('disposition') != 'NOT_EVALUABLE': counts[k]+=1
    if any(counts.values()): raise ASOCSSamplingError('UNEXPECTED_EXACT_ACTIVE_EVALUABLE_CONSTRUCT_REQUIRES_NEW_FRAME_IMPLEMENTATION')
    return counts

def build_review_population(
    traces: Sequence[Mapping[str,Any]], gaps: Sequence[Mapping[str,Any]], *, population_hash: str, nonce_hex: str,
    hidden_repeat_fraction: float=0.05, session_cap: int=25,
) -> dict[str,Any]:
    if not 0.05 <= hidden_repeat_fraction <= 0.10: raise ASOCSSamplingError('HIDDEN_REPEAT_FRACTION_OUTSIDE_PLAN')
    if session_cap <= 0: raise ASOCSSamplingError('SESSION_CAP_INVALID')
    target=[dict(t) for t in traces if t.get('region')=='TARGET']
    if len(target)!=17376: raise ASOCSSamplingError(f'G3_TARGET_COUNT_MISMATCH:{len(target)}')
    _check_upper_fail_closed(target)
    by_id={str(t['object_id']):t for t in target}
    if len(by_id)!=len(target): raise ASOCSSamplingError('G3_TARGET_OBJECT_ID_DUPLICATE')

    frames=[]
    base_selected=[]
    for month in TARGET_MONTHS:
        elig=[t for t in target if t.get('source_status')=='COMPLETE' and str(t.get('interval_start','')).startswith(month)]
        f=select_frame(elig,population_hash=population_hash,nonce_hex=nonce_hex,stratum_id=f'BASE_RATE_RANDOM_ANCHORS:{month}',target_size=20)
        if f['selection_count']!=20: raise ASOCSSamplingError('BASE_MONTH_EXHAUSTED:'+month)
        frames.append(f); base_selected.extend(f['object_ids'])
    if len(base_selected)!=120 or len(set(base_selected))!=120: raise ASOCSSamplingError('BASE_RATE_120_BALANCE_FAILED')

    target_gaps=[]
    for g in gaps:
        if g.get('previous_region')==g.get('next_region')=='TARGET':
            target_gaps.append({'object_id':str(g['gap_id']), **dict(g)})
    gap_frame=select_frame(target_gaps,population_hash=population_hash,nonce_hex=nonce_hex,stratum_id='GAP_CENTERED_SOURCE_DISCONTINUITY',target_size=40)
    frames.append(gap_frame)

    continuity_null=[]
    for t in target:
        if t.get('source_status')!='COMPLETE': continue
        c1=t.get('c1')
        if not isinstance(c1,Mapping): continue
        if c1.get('null_reasons',{}).get('true_range_abs')=='SOURCE_CONTINUITY_UNRESOLVED_OR_GAP':
            continuity_null.append(t)
    # Design requires a dedicated null stratum but supplies no numeric target. Full enumeration
    # is the only deterministic implementation that does not invent a post-census numeric cut.
    null_frame=full_census_frame(continuity_null,population_hash=population_hash,nonce_hex=nonce_hex,
                                 stratum_id='C1_CONTINUITY_NULL',reason='DESIGN_REQUIRES_NULL_STRATUM_NO_NUMERIC_TARGET_NO_POST_CENSUS_CUT')
    frames.append(null_frame)

    unavailable_reason='G3_CLAIM_CLASS_FIREWALL:ASOCS_SINGLE_STREAM_MORPHOLOGY_COHERENCE'
    frames += [
      unavailable_frame(stratum_id='C2_LEVEL_CONSTRUCT',design_target='LEVELS_CONSTRUCT_STRATIFIED',reason=unavailable_reason),
      unavailable_frame(stratum_id='C2_CONTAINER_CONSTRUCT',design_target='CONTAINERS_CONSTRUCT_STRATIFIED',reason=unavailable_reason),
      unavailable_frame(stratum_id='C2_RELATION_CONSTRUCT',design_target='RELATIONS_CONSTRUCT_STRATIFIED',reason=unavailable_reason),
      unavailable_frame(stratum_id='C2_TRANSITION:NO_CHANGE',design_target=30,reason=unavailable_reason),
      unavailable_frame(stratum_id='C2_TRANSITION:MEASUREMENT',design_target=30,reason=unavailable_reason),
      unavailable_frame(stratum_id='C2_TRANSITION:CATEGORICAL',design_target=30,reason=unavailable_reason),
      unavailable_frame(stratum_id='C2_TRANSITION:STRUCTURAL',design_target=40,reason=unavailable_reason),
      unavailable_frame(stratum_id='C2_TRANSITION:REFERENCE_IDENTITY',design_target=40,reason=unavailable_reason),
      unavailable_frame(stratum_id='C2_TRANSITION:COMPUTABILITY',design_target=30,reason=unavailable_reason),
      unavailable_frame(stratum_id='C2_PARENT_CONTEXT',design_target='CHANGED_STABLE_ZERO_MULTIPLE_ELIGIBLE',reason=unavailable_reason),
      unavailable_frame(stratum_id='C2E_EPISODE',design_target={'min':75,'max':125},reason=unavailable_reason),
      unavailable_frame(stratum_id='C2E_PHASE_MUTATION',design_target=100,reason=unavailable_reason),
      unavailable_frame(stratum_id='C2E_PHASE_NON_MUTATION_CONTROL',design_target='REQUIRED_NO_NUMERIC_TARGET_SPECIFIED',reason=unavailable_reason),
    ]

    memberships=defaultdict(set)
    for f in frames:
        for oid in f['object_ids']: memberships[str(oid)].add(str(f['stratum_id']))

    units=[]
    for oid,strata in sorted(memberships.items()):
        if oid.startswith('asocs:gap:'):
            g=next(x for x in target_gaps if x['object_id']==oid)
            prev=_literal_dt(str(g['previous_literal_timestamp'])); nxt=_literal_dt(str(g['next_literal_timestamp']))
            unit={'review_unit_id':oid,'unit_type':'SOURCE_GAP','stratum_memberships':sorted(strata),
                  'source_status':'GAP_EVENT','gap_delta_minutes':int(g['delta_minutes']),
                  'anchor':{'previous_literal_timestamp':str(g['previous_literal_timestamp']),'next_literal_timestamp':str(g['next_literal_timestamp'])},
                  'navigation_windows':gap_windows(prev,nxt)}
        else:
            t=by_id[oid]; anchor=_literal_dt(str(t['first_valid_time']))
            unit={'review_unit_id':oid,'unit_type':'ANCHOR_15M','stratum_memberships':sorted(strata),
                  'source_status':str(t['source_status']),'anchor':{'interval_start':str(t['interval_start']),'interval_end':str(t['interval_end']),'first_valid_time':str(t['first_valid_time'])},
                  'navigation_windows':anchor_windows(anchor)}
        unit['blind_case_id']=blind_case_id(population_hash,nonce_hex,oid,repeat=False)
        units.append(unit)
    if len(units)!=len(memberships): raise AssertionError

    repeat_count=max(1,math.ceil(len(units)*hidden_repeat_fraction)) if units else 0
    repeat_ranked=sorted(units,key=lambda u:(selection_score(population_hash,nonce_hex,'HIDDEN_REPEAT',u['review_unit_id']),u['review_unit_id']))
    repeat_source=repeat_ranked[:repeat_count]
    presentations=[]
    for u in units:
        presentations.append({'presentation_case_id':u['blind_case_id'],'review_unit_id':u['review_unit_id'],'presentation_type':'PRIMARY','hidden_repeat':False,'navigation_windows':u['navigation_windows']})
    for u in repeat_source:
        presentations.append({'presentation_case_id':blind_case_id(population_hash,nonce_hex,u['review_unit_id'],repeat=True),'review_unit_id':u['review_unit_id'],'presentation_type':'HIDDEN_REPEAT','hidden_repeat':True,'navigation_windows':u['navigation_windows']})
    if len({p['presentation_case_id'] for p in presentations})!=len(presentations): raise ASOCSSamplingError('BLIND_PRESENTATION_ID_COLLISION')
    presentations.sort(key=lambda p:(selection_score(population_hash,nonce_hex,'PRESENTATION_ORDER',p['presentation_case_id']),p['presentation_case_id']))
    for i,p in enumerate(presentations,1):
        p['case_ordinal']=i; p['session_ordinal']=(i-1)//session_cap+1; p['session_position']=(i-1)%session_cap+1

    compact_frames=[]
    for f in frames:
        compact={k:v for k,v in f.items() if k!='scores'}
        compact['selected_object_ids_sha256']=canonical_sha256(compact.get('object_ids',[]))
        compact_frames.append(compact)
    population_payload={'programme_id':'OVC-ASOCS-6M-v0.1','gate_id':'ASOCSI-G4','population_hash':population_hash,
        'frames':compact_frames,'units':units,
        'hidden_repeat_review_unit_ids':[u['review_unit_id'] for u in repeat_source],
        'presentations':[{'presentation_case_id':p['presentation_case_id'],'review_unit_id':p['review_unit_id'],'presentation_type':p['presentation_type'],'case_ordinal':p['case_ordinal']} for p in presentations]}
    review_population_sha=canonical_sha256(population_payload)
    return {
      'schema':'ovc-asocs-g4-sampling-execution/v0_1','programme_id':'OVC-ASOCS-6M-v0.1','packet_id':'ASOCSI-WP6','gate_id':'ASOCSI-G4',
      'population_hash':population_hash,'nonce_sha256':hashlib.sha256(bytes.fromhex(nonce_hex)).hexdigest(),
      'sampling_config':{'base_rate_target':120,'base_rate_month_quota':20,'gap_centered_target':40,'hidden_repeat_fraction':hidden_repeat_fraction,'session_cap':session_cap},
      'frames':frames,'review_units':units,'hidden_repeat_review_unit_ids':[u['review_unit_id'] for u in repeat_source],
      'presentations':presentations,'unique_review_unit_count':len(units),'hidden_repeat_count':repeat_count,'presentation_count':len(presentations),
      'session_count':math.ceil(len(presentations)/session_cap) if presentations else 0,
      'review_population_sha256':review_population_sha,
      'claim_class':'ASOCS_SINGLE_STREAM_MORPHOLOGY_COHERENCE','upper_stack_review_scope':'NOT_EVALUABLE_EXACT_ACTIVE_INTERFACE',
      'active':False,'canonical':False,'publication':False,'authority_class':'ASOCS_AUDIT_ONLY'
    }
