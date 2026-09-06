from __future__ import annotations
import dataclasses
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass

# ---- exact R2 protocol surface ----

PROTOCOL_ID = "OVC-EML-GRAMMAR-0003-RRSCG-ALGORITHM-0.1-R2"
ALGORITHM_NAME = "Representation-Robust Structural Constraint Grammar"
ALGORITHM_ACRONYM = "RRSCG"

PRIMARY_TARGET_PACK = "R18_MID_v1"
DETAIL_TARGET_PACKS = ("T0_v1", "T1_v1")
FALLBACK_TARGET_PACKS = ("T2_v1", "T3_v1")

PRIMARY_CONSTRAINT_VIEWS = (
    "C_LAST_EXACT",
    "C_LAST_HI",
    "C_LAST_MID",
    "CARRIER_BAG_HI",
    "CARRIER_BAG_MID",
)
PRIMARY_VIEWSET_ID = "RRSCG_OPERATION_FREE_VIEWSET_v1"

RESOLUTION_TIERS = (
    ("FULL_CONSENSUS", PRIMARY_CONSTRAINT_VIEWS),
    ("COARSE_CONSENSUS", ("C_LAST_HI","C_LAST_MID","CARRIER_BAG_MID")),
    ("MINIMAL_CONSTRAINT", ("C_LAST_MID",)),
)

PRIMARY_SUPPORT_MIN = 2
PRIMARY_RELATION_MIN = 2
SUPPORT_SENSITIVITIES = (2, 3, 5)
MAJORITY_COUNT = 3

LEGACY_R5_ENRICHMENT_VIEWS = ("BASE","NO_HI","NO_MID","PATH_BEFORE_MID","NO_PATH")

PRIMARY_IDENTITY_COMPONENTS = (
    "operation_free_view_frontiers",
    "full_consensus_core",
    "continuation_envelope",
    "ambiguity_shell",
    "selected_resolution_tier",
    "selected_constraint_frontier",
    "representation_consensus_counts",
    "target_pack",
)
EXCLUDED_FROM_PRIMARY_IDENTITY = (
    "last_operation",
    "operation_path",
    "factor_bag_with_operation",
    "factor_path_order",
    "higher_order_factor_path",
    "occurrence_context",
    "c2e_episode_boundary_phase",
)

# Revised 2: the null keeps the full lawful representation bundle fixed and
# destroys only target association within local source/time strata.
PRIMARY_CONSENSUS_NULL = "CG-NCONSENSUS"
PRIMARY_CONSENSUS_NULL_VERSION = "TARGET_SEQUENCE_CYCLIC_SHIFT_v2"
PRIMARY_CONSENSUS_NULL_REPLICAS = 128
PRIMARY_CONSENSUS_NULL_STRATA = ("segment_id","iso_week")

PRIMARY_CONSENSUS_STATISTIC = "CONSENSUS_ADVANTAGE"
CONSENSUS_ADVANTAGE_DEFINITION = (
    "fixed_population_selected_constraint_efficiency"
    " - fixed_population_mean_single_view_efficiency"
)

EVIDENCE_EXPOSURE = (
    "DEVELOPMENT_EXPOSED_TO_C0C",
    "DEVELOPMENT_EXPOSED_TO_FXCM_2019_R4_R5",
)
SCIENTIFIC_AUTHORITY = "NONE"

# ---- exact R2 model surface ----

@dataclass(frozen=True)
class ConstraintViewEvidence:
    view_id:str
    supported:bool
    antecedent_support:int
    qualified_frontier_supports:tuple[tuple[str,int],...]
    observed_frontier_supports:tuple[tuple[str,int],...]
    target_pack_id:str
    relation_min:int
    training_frontier_id:str
    source_generation_id:str

    @property
    def qualified_frontier(self): return frozenset(k for k,n in self.qualified_frontier_supports if n>=self.relation_min)
    @property
    def observed_frontier(self): return frozenset(k for k,n in self.observed_frontier_supports if n>=1)
    @property
    def relation_exists(self): return self.supported and bool(self.qualified_frontier)

@dataclass(frozen=True)
class ConstraintGrammarEvent:
    event_id:str
    source_generation_id:str
    target_pack_id:str
    representation_set_id:str
    support_min:int
    relation_min:int
    views:tuple[ConstraintViewEvidence,...]
    full_viewset_supported:bool
    full_core:frozenset[str]
    majority:frozenset[str]
    envelope:frozenset[str]
    shell:frozenset[str]
    consensus_counts:tuple[tuple[str,int],...]
    selected_resolution_tier:str|None
    selected_frontier:frozenset[str]
    relation_resolved:bool
    full_consensus_state:str
    state:str
    constraint_id:str

@dataclass(frozen=True)
class ConstraintEvaluation:
    event_id:str
    target_id:str
    selected_hit:bool
    selected_size:int
    selected_efficiency:float
    full_core_hit:bool
    full_core_size:int
    full_core_efficiency:float
    majority_hit:bool
    majority_size:int
    envelope_hit:bool
    envelope_size:int
    shell_only_hit:bool
    outside_envelope:bool
    single_view_efficiencies:tuple[tuple[str,float],...]
    mean_single_view_efficiency:float
    consensus_advantage:float
    state:str
    selected_resolution_tier:str|None
    evaluation_id:str

@dataclass(frozen=True)
class ConstraintPopulationSummary:
    n_total:int
    n_full_viewset_supported:int
    n_relation_resolved:int
    n_full_core_nonempty:int
    n_full_representation_conflict:int
    full_viewset_support_rate:float
    relation_resolution_rate:float
    full_core_relation_rate:float
    selected_hit_rate:float
    selected_efficiency:float
    full_core_hit_rate:float
    full_core_efficiency:float
    majority_hit_rate:float
    envelope_hit_rate:float
    shell_only_rate:float
    outside_envelope_rate:float
    mean_selected_size:float
    mean_full_core_size:float
    mean_majority_size:float
    mean_envelope_size:float
    mean_single_view_efficiency:float
    consensus_advantage:float
    selected_tier_counts:tuple[tuple[str,int],...]
    summary_id:str

@dataclass(frozen=True)
class ConsensusNullReceipt:
    null_id:str
    null_version:str
    replica_index:int
    seed_hex:str
    cohort:str
    source_generation_id:str
    stratum_fields:tuple[str,...]
    evaluation_event_ids_preserved:bool
    antecedent_constraint_ids_preserved:bool
    target_multisets_preserved_by_stratum:bool
    target_circular_transition_multisets_preserved_by_stratum:bool
    target_assignments_changed:int
    target_assignment_count:int
    receipt_id:str

@dataclass(frozen=True)
class ResolutionSensitivitySummary:
    support_min:int
    n_events:int
    relation_resolution_rate:float
    full_consensus_rate:float
    coarse_consensus_rate:float
    minimal_constraint_rate:float
    abstain_rate:float
    summary_id:str

@dataclass(frozen=True)
class RRSCGStudyResult:
    protocol_id:str
    cohort:str
    source_generation_id:str
    target_pack_id:str
    support_min:int
    relation_min:int
    population_summary:ConstraintPopulationSummary
    resolution_sensitivity:tuple[ResolutionSensitivitySummary,...]
    consensus_null_statistics:tuple[float,...]
    consensus_null_receipts:tuple[ConsensusNullReceipt,...]
    consensus_null_adequate:bool
    consensus_null_reason:str
    consensus_raw_p:float
    result_id:str

# ---- exact canonical identity functions ----
def _normalise(x):
    if dataclasses.is_dataclass(x):
        return {"$dataclass": x.__class__.__name__,
                "fields": {f.name:_normalise(getattr(x,f.name)) for f in dataclasses.fields(x)}}
    if isinstance(x, tuple):
        return {"$tuple":[_normalise(v) for v in x]}
    if isinstance(x, list):
        return {"$list":[_normalise(v) for v in x]}
    if isinstance(x, frozenset):
        vals=[_normalise(v) for v in x]
        vals.sort(key=lambda z: json.dumps(z,sort_keys=True,separators=(",",":"),ensure_ascii=False))
        return {"$frozenset": vals}
    if isinstance(x, set):
        vals=[_normalise(v) for v in x]
        vals.sort(key=lambda z: json.dumps(z,sort_keys=True,separators=(",",":"),ensure_ascii=False))
        return {"$set": vals}
    if isinstance(x, dict):
        return {"$map":[[str(k),_normalise(x[k])] for k in sorted(x,key=lambda z:str(z))]}
    if isinstance(x, Counter):
        return _normalise(dict(x))
    if isinstance(x, bool) or x is None or isinstance(x,(int,str)):
        return x
    if isinstance(x,float):
        if not math.isfinite(x):
            return {"$float":repr(x)}
        # floats are allowed for receipts, but never recommended as scientific morphology identity.
        return {"$float":format(x,".17g")}
    raise TypeError(f"unsupported canonical type: {type(x)!r}")

def canonical_bytes(x) -> bytes:
    return json.dumps(_normalise(x),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def canonical_text(x) -> str:
    return canonical_bytes(x).decode("utf-8")

def sha256_hex(x) -> str:
    return hashlib.sha256(canonical_bytes(x)).hexdigest()

def morphology_id(pack_id: str, value) -> str:
    b=pack_id.encode("utf-8")+b"\n"+canonical_bytes(value)
    return hashlib.sha256(b).hexdigest()

def bag_key(items):
    """Canonical multiset of hashable items; order destroyed, multiplicity preserved."""
    c=Counter(items)
    rows=[(canonical_text(k),int(v),k) for k,v in c.items()]
    rows.sort(key=lambda r:r[0])
    return tuple((r[2],r[1]) for r in rows)

# ---- exact carrier coarsening helpers ----
def _coarse(c):return ("CHANGED",) if c[0]=="CHANGED" else ("UNCHANGED",)

def r25_hi_v1(c_exact):
    c=list(c_exact);c[4]=_coarse(c[4]);return tuple(c)

def r25_mid_v1(c_exact):
    c=list(c_exact);c[3]=_coarse(c[3]);c[4]=_coarse(c[4]);return tuple(c)

# ---- exact target/support helpers ----
def target_id(event,pack_id):
    return morphology_id(pack_id,event.target(pack_id))

def training_frontier_id(train):
    return sha256_hex(("GrammarEvidenceTrainingFrontierManifest_v2",
        tuple((e.event_id,e.source_generation_id,e.target_fvt,e.component_fvts,e.event_time_utc) for e in train)))

# ---- exact primary view contexts ----
def _last_carrier(interval):
    return None if not interval.path else interval.path[-1][0]

def context_value(interval,view_id):
    if not interval.path:
        return None
    last=_last_carrier(interval)
    if view_id=="C_LAST_EXACT":
        return last
    if view_id=="C_LAST_HI":
        return r25_hi_v1(last)
    if view_id=="C_LAST_MID":
        return r25_mid_v1(last)
    if view_id=="CARRIER_BAG_HI":
        return bag_key(tuple(r25_hi_v1(c) for c,_ in interval.path))
    if view_id=="CARRIER_BAG_MID":
        return bag_key(tuple(r25_mid_v1(c) for c,_ in interval.path))
    raise KeyError(view_id)

# ---- exact continuation-constraint composition ----
def build_view_evidence(train,event,view_id,target_pack_id, support_min, relation_min):
    train_keys=[context_value(e,view_id) for e in train]
    counts=Counter(k for k in train_keys if k is not None)
    key=context_value(event,view_id)
    sup=int(counts[key]) if key is not None else 0
    supported=key is not None and sup>=int(support_min)
    fm=Counter()
    if supported:
        for e in train:
            if context_value(e,view_id)==key:
                fm[target_id(e,target_pack_id)]+=1
    observed=tuple(sorted(((k,int(n)) for k,n in fm.items()),key=lambda kv:kv[0]))
    qualified=tuple((k,n) for k,n in observed if n>=int(relation_min))
    return ConstraintViewEvidence(
        view_id=view_id,supported=bool(supported),antecedent_support=sup,
        qualified_frontier_supports=qualified,observed_frontier_supports=observed,
        target_pack_id=target_pack_id,relation_min=int(relation_min),
        training_frontier_id=training_frontier_id(train),
        source_generation_id=event.source_generation_id,
    )

def compose_constraint_event(event_id,source_generation_id,views,target_pack_id=PRIMARY_TARGET_PACK,
                             support_min=PRIMARY_SUPPORT_MIN,relation_min=PRIMARY_RELATION_MIN,
                             representation_set_id=PRIMARY_VIEWSET_ID):
    by={v.view_id:v for v in views}
    ordered=tuple(by[r] for r in PRIMARY_CONSTRAINT_VIEWS if r in by)
    full_supported=all(r in by and by[r].supported for r in PRIMARY_CONSTRAINT_VIEWS)

    counts=Counter()
    for v in ordered:
        for t in v.qualified_frontier: counts[t]+=1
    n=len(PRIMARY_CONSTRAINT_VIEWS)
    full_core=frozenset(t for t,c in counts.items() if c==n) if full_supported else frozenset()
    majority=frozenset(t for t,c in counts.items() if c>=MAJORITY_COUNT)
    envelope=frozenset(counts)
    shell=frozenset(envelope-full_core)

    selected_tier=None
    selected=frozenset()
    for tier_id,required in RESOLUTION_TIERS:
        if not all(r in by and by[r].supported for r in required):
            continue
        fs=[set(by[r].qualified_frontier) for r in required]
        if not fs:
            continue
        inter=set(fs[0])
        for f in fs[1:]: inter &= f
        if inter:
            selected_tier=tier_id
            selected=frozenset(inter)
            break

    if full_supported and full_core:
        full_state="FULL_CORE"
    elif full_supported and envelope:
        full_state="FULL_REPRESENTATION_CONFLICT"
    elif full_supported:
        full_state="FULL_NO_RELATION"
    else:
        full_state="FULL_VIEWSET_INCOMPLETE"

    if selected_tier=="FULL_CONSENSUS": state="RESOLVED_FULL_CONSENSUS"
    elif selected_tier=="COARSE_CONSENSUS": state="RESOLVED_COARSE_CONSENSUS"
    elif selected_tier=="MINIMAL_CONSTRAINT": state="RESOLVED_MINIMAL_CONSTRAINT"
    else: state="ABSTAIN_NO_CONSTRAINT"

    cid=sha256_hex((
        "RRSCGConstraintEvent_R1_v1",event_id,source_generation_id,target_pack_id,
        representation_set_id,int(support_min),int(relation_min),
        tuple((v.view_id,v.supported,v.antecedent_support,v.qualified_frontier_supports) for v in ordered),
        tuple(sorted(full_core)),tuple(sorted(majority)),tuple(sorted(envelope)),
        selected_tier,tuple(sorted(selected)),full_state,state
    ))
    return ConstraintGrammarEvent(
        event_id=event_id,source_generation_id=source_generation_id,target_pack_id=target_pack_id,
        representation_set_id=representation_set_id,support_min=int(support_min),relation_min=int(relation_min),
        views=ordered,full_viewset_supported=full_supported,full_core=full_core,majority=majority,
        envelope=envelope,shell=shell,consensus_counts=tuple(sorted((k,int(v)) for k,v in counts.items())),
        selected_resolution_tier=selected_tier,selected_frontier=selected,
        relation_resolved=bool(selected),full_consensus_state=full_state,state=state,constraint_id=cid
    )

def build_constraint_event(train,event,target_pack_id=PRIMARY_TARGET_PACK,
                           support_min=PRIMARY_SUPPORT_MIN,relation_min=PRIMARY_RELATION_MIN):
    views=[
        build_view_evidence(train,event,v,target_pack_id,support_min,relation_min)
        for v in PRIMARY_CONSTRAINT_VIEWS
    ]
    return compose_constraint_event(
        event.event_id,event.source_generation_id,views,target_pack_id,support_min,relation_min
    )

def build_constraint_population(train,events,target_pack_id=PRIMARY_TARGET_PACK,
                                support_min=PRIMARY_SUPPORT_MIN,relation_min=PRIMARY_RELATION_MIN):
    return {e.event_id:build_constraint_event(train,e,target_pack_id,support_min,relation_min) for e in events}

# ---- exact evaluation metrics ----
def _mean(xs):
    vals=[float(x) for x in xs if math.isfinite(float(x))]
    return sum(vals)/len(vals) if vals else float("nan")

def evaluate_constraint(event,c,target_override=None):
    y=target_override if target_override is not None else target_id(event,c.target_pack_id)
    selected_hit=c.relation_resolved and y in c.selected_frontier
    full_hit=c.full_viewset_supported and y in c.full_core
    maj_hit=y in c.majority
    env_hit=y in c.envelope
    shell_only=y in c.shell and y not in c.full_core
    outside=bool(c.envelope) and y not in c.envelope

    def eff(hit,size): return (1.0 if hit else 0.0)/max(int(size),1)

    sv=[]
    for v in c.views:
        f=v.qualified_frontier
        sv.append((v.view_id, eff(y in f,len(f)) if v.supported and f else 0.0))
    mean_sv=_mean(x for _,x in sv)
    selected_eff=eff(selected_hit,len(c.selected_frontier)) if c.relation_resolved else 0.0
    advantage=selected_eff-mean_sv

    eid=sha256_hex((
        "RRSCGConstraintEvaluation_R2_v1",event.event_id,c.constraint_id,y,
        selected_eff,mean_sv,advantage
    ))
    return ConstraintEvaluation(
        event_id=event.event_id,target_id=y,
        selected_hit=selected_hit,selected_size=len(c.selected_frontier),
        selected_efficiency=selected_eff,
        full_core_hit=full_hit,full_core_size=len(c.full_core),
        full_core_efficiency=eff(full_hit,len(c.full_core)) if c.full_core else 0.0,
        majority_hit=maj_hit,majority_size=len(c.majority),
        envelope_hit=env_hit,envelope_size=len(c.envelope),
        shell_only_hit=shell_only,outside_envelope=outside,
        single_view_efficiencies=tuple(sv),mean_single_view_efficiency=mean_sv,
        consensus_advantage=advantage,
        state=c.state,selected_resolution_tier=c.selected_resolution_tier,evaluation_id=eid
    )

def summarise_population(events,constraints,target_overrides=None):
    target_overrides=target_overrides or {}
    evs=[evaluate_constraint(e,constraints[e.event_id],target_overrides.get(e.event_id)) for e in events]
    n=len(evs)
    full=sum(constraints[e.event_id].full_viewset_supported for e in events)
    resolved=sum(constraints[e.event_id].relation_resolved for e in events)
    core_non=sum(bool(constraints[e.event_id].full_core) for e in events)
    conflict=sum(constraints[e.event_id].full_consensus_state=="FULL_REPRESENTATION_CONFLICT" for e in events)
    tiers=Counter(x.selected_resolution_tier or "ABSTAIN" for x in evs)

    selected_hit=sum(x.selected_hit for x in evs)/n if n else float("nan")
    full_hit=sum(x.full_core_hit for x in evs)/n if n else float("nan")
    maj_hit=sum(x.majority_hit for x in evs)/n if n else float("nan")
    env_hit=sum(x.envelope_hit for x in evs)/n if n else float("nan")
    shell=sum(x.shell_only_hit for x in evs)/n if n else float("nan")
    outside=sum(x.outside_envelope for x in evs)/n if n else float("nan")
    selected_eff=_mean(x.selected_efficiency for x in evs)
    core_eff=_mean(x.full_core_efficiency for x in evs)
    mean_sv=_mean(x.mean_single_view_efficiency for x in evs)
    advantage=_mean(x.consensus_advantage for x in evs)

    sid=sha256_hex((
        "RRSCGConstraintPopulationSummary_R2_v1",n,full,resolved,core_non,conflict,
        tuple(sorted(tiers.items())),selected_hit,full_hit,selected_eff,core_eff,
        mean_sv,advantage
    ))
    return ConstraintPopulationSummary(
        n_total=n,n_full_viewset_supported=full,n_relation_resolved=resolved,
        n_full_core_nonempty=core_non,n_full_representation_conflict=conflict,
        full_viewset_support_rate=(full/n if n else float("nan")),
        relation_resolution_rate=(resolved/n if n else float("nan")),
        full_core_relation_rate=(core_non/n if n else float("nan")),
        selected_hit_rate=selected_hit,selected_efficiency=selected_eff,
        full_core_hit_rate=full_hit,full_core_efficiency=core_eff,
        majority_hit_rate=maj_hit,envelope_hit_rate=env_hit,shell_only_rate=shell,
        outside_envelope_rate=outside,
        mean_selected_size=_mean(x.selected_size for x in evs),
        mean_full_core_size=_mean(x.full_core_size for x in evs),
        mean_majority_size=_mean(x.majority_size for x in evs),
        mean_envelope_size=_mean(x.envelope_size for x in evs),
        mean_single_view_efficiency=mean_sv,consensus_advantage=advantage,
        selected_tier_counts=tuple(sorted((k,int(v)) for k,v in tiers.items())),
        summary_id=sid
    ),tuple(evs)

ALGORITHM_ID = "OVC-EML-GRAMMAR-0003-RRSCG-ALGORITHM-0.1-R2"
SOURCE_ARCHIVE_SHA256 = "5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5"
SOURCE_BINDING = "BOUND_EXACT"
CAPABILITY_STATE = "INACTIVE_CONFORMANCE_ONLY"
