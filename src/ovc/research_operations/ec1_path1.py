from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .canonical import canonical_json_bytes, canonical_sha256

FIELD_ROLES = frozenset({"IDENTITY","RELATIONAL_IDENTITY","DESCRIPTIVE_ONLY","CHRONOLOGY_ONLY","PROVENANCE_ONLY","STRATIFIER","FORBIDDEN"})
IDENTITY_ROLES = frozenset({"IDENTITY","RELATIONAL_IDENTITY"})
POPULATION_STATES = frozenset({"ADMITTED","NOT_EVALUABLE","NOT_COMPARABLE","CENSORED","QUARANTINED","EXCLUDED_BY_FROZEN_RULE"})
DEPENDENCE_EDGE_TYPES = frozenset({"SAME_SOURCE_ANCHOR","BID_ASK_CORRESPONDENCE","PARENT_CHILD_CLOCK","TRANSITION_SEQUENCE_OVERLAP","COMMON_C2E_EPISODE","COMMON_POPULATION_UNIT_ANCESTRY"})

class EC1Path1InvariantError(ValueError): pass
class EC1CapacityError(RuntimeError): pass

@dataclass(frozen=True)
class FieldDescriptor:
    field_path: str
    role: str
    owner: str
    source_path: str
    comparability_basis: str
    missingness_semantics: str
    rationale: str
    def __post_init__(self):
        if self.role not in FIELD_ROLES: raise EC1Path1InvariantError(f"invalid field role {self.role}")
        if not all((self.field_path,self.owner,self.source_path,self.comparability_basis,self.missingness_semantics,self.rationale)): raise EC1Path1InvariantError("field descriptor incomplete")

@dataclass(frozen=True)
class EC1IdentityFieldManifest:
    generation_id: str
    source_bindings: Mapping[str,str]
    fields: tuple[FieldDescriptor,...]
    frozen: bool = True
    def __post_init__(self):
        paths=[x.field_path for x in self.fields]
        if len(paths)!=len(set(paths)): raise EC1Path1InvariantError("duplicate field_path")
        if not self.fields: raise EC1Path1InvariantError("field manifest empty")
    def assert_exhaustive(self, reachable_field_paths: Iterable[str]) -> None:
        reachable=set(reachable_field_paths); classified={x.field_path for x in self.fields}
        if reachable != classified: raise EC1Path1InvariantError(f"identity-field coverage mismatch missing={sorted(reachable-classified)} extra={sorted(classified-reachable)}")
    @property
    def semantic_sha256(self):
        return canonical_sha256({"generation_id":self.generation_id,"source_bindings":dict(self.source_bindings),"fields":[x.__dict__ for x in sorted(self.fields,key=lambda x:x.field_path)]})


def _canonical_value(value: Any) -> str:
    return canonical_json_bytes(value, trailing_newline=False).decode("utf-8")

def predicate_token(field_path: str, value: Any) -> str:
    return f"{field_path}={_canonical_value(value)}"

def canonical_predicates(record: Mapping[str,Any], manifest: EC1IdentityFieldManifest) -> frozenset[str]:
    out=set()
    for desc in manifest.fields:
        if desc.role not in IDENTITY_ROLES: continue
        if desc.field_path not in record: raise EC1Path1InvariantError(f"required identity field absent: {desc.field_path}")
        out.add(predicate_token(desc.field_path, record[desc.field_path]))
    return frozenset(out)

def predicate_roundtrip(token: str) -> tuple[str,Any]:
    path,encoded=token.split("=",1)
    return path,json.loads(encoded)

@dataclass(frozen=True)
class PopulationUnit:
    unit_id: str
    state: str
    predicates: frozenset[str]
    provenance: Mapping[str,Any]
    def __post_init__(self):
        if self.state not in POPULATION_STATES: raise EC1Path1InvariantError("invalid population state")
        if self.state != "ADMITTED" and self.predicates: raise EC1Path1InvariantError("non-admitted units cannot silently enter search predicates")

@dataclass(frozen=True)
class PopulationReconciliation:
    eligible_count: int
    state_counts: Mapping[str,int]
    def validate(self):
        if self.eligible_count != sum(self.state_counts.values()): raise EC1Path1InvariantError("eligible denominator does not reconcile")
        if set(self.state_counts)-POPULATION_STATES: raise EC1Path1InvariantError("unknown population state")

@dataclass(frozen=True)
class PatternClosureClass:
    occurrence_unit_ids: tuple[str,...]
    closed_pattern: tuple[str,...]
    minimal_generators: tuple[tuple[str,...],...]
    @property
    def closure_id(self):
        return "ec1:closure:"+canonical_sha256({"occurrence_unit_ids":list(self.occurrence_unit_ids),"closed_pattern":list(self.closed_pattern)})

@dataclass(frozen=True)
class PatternLatticeResult:
    classes: tuple[PatternClosureClass,...]
    enumerated_conjunction_count: int
    admitted_unit_count: int
    residual_unit_ids: tuple[str,...]
    @property
    def semantic_sha256(self):
        return canonical_sha256({"classes":[{"occurrence_unit_ids":list(c.occurrence_unit_ids),"closed_pattern":list(c.closed_pattern),"minimal_generators":[list(g) for g in c.minimal_generators]} for c in self.classes],"enumerated_conjunction_count":self.enumerated_conjunction_count,"admitted_unit_count":self.admitted_unit_count,"residual_unit_ids":list(self.residual_unit_ids)})


def _subsets(predicates: frozenset[str], max_predicates: int) -> Iterable[tuple[str,...]]:
    ordered=sorted(predicates)
    if len(ordered)>max_predicates: raise EC1CapacityError(f"predicate dimension {len(ordered)} exceeds synthetic exact bound {max_predicates}")
    for r in range(1,len(ordered)+1):
        yield from itertools.combinations(ordered,r)

def exact_recurring_pattern_lattice(units: Sequence[PopulationUnit], *, min_support: int=2, max_predicates_per_unit: int=18) -> PatternLatticeResult:
    admitted=[u for u in units if u.state=="ADMITTED"]
    predicate_sets={u.unit_id:u.predicates for u in admitted}
    occurrence_by_pattern: dict[tuple[str,...],set[str]]={}
    enumerated=set()
    for unit in admitted:
        for subset in _subsets(unit.predicates,max_predicates_per_unit): enumerated.add(subset)
    for subset in sorted(enumerated):
        members={uid for uid,preds in predicate_sets.items() if set(subset)<=preds}
        if len(members)>=min_support: occurrence_by_pattern[subset]=members
    by_occurrence: dict[tuple[str,...],list[tuple[str,...]]]={}
    for pattern,members in occurrence_by_pattern.items(): by_occurrence.setdefault(tuple(sorted(members)),[]).append(pattern)
    classes=[]; matched=set()
    for occurrence, patterns in sorted(by_occurrence.items()):
        intersection=set(predicate_sets[occurrence[0]])
        for uid in occurrence[1:]: intersection &= set(predicate_sets[uid])
        closed=tuple(sorted(intersection))
        candidate_patterns=sorted(patterns,key=lambda p:(len(p),p))
        minimal=[]
        for p in candidate_patterns:
            ps=set(p)
            if not any(set(q)<ps for q in candidate_patterns): minimal.append(p)
        cls=PatternClosureClass(occurrence,closed,tuple(minimal)); classes.append(cls); matched.update(occurrence)
    residual=tuple(sorted(set(predicate_sets)-matched))
    return PatternLatticeResult(tuple(classes),len(enumerated),len(admitted),residual)

@dataclass(frozen=True)
class DependenceEdge:
    left: str
    right: str
    edge_type: str
    def __post_init__(self):
        if self.edge_type not in DEPENDENCE_EDGE_TYPES: raise EC1Path1InvariantError("unregistered dependence edge type")
        if self.left==self.right: raise EC1Path1InvariantError("self dependence edge forbidden")

@dataclass(frozen=True)
class EvidenceDependenceGraph:
    edges: tuple[DependenceEdge,...]
    stored_graph_depth: int = 1
    def __post_init__(self):
        if self.stored_graph_depth!=1: raise EC1Path1InvariantError("persisted dependence graph is direct-edge only")
    def connected_components(self) -> tuple[tuple[str,...],...]:
        nodes={v for e in self.edges for v in (e.left,e.right)}; adj={n:set() for n in nodes}
        for e in self.edges: adj[e.left].add(e.right); adj[e.right].add(e.left)
        components=[]
        while nodes:
            root=min(nodes); stack=[root]; seen=set()
            while stack:
                n=stack.pop()
                if n in seen: continue
                seen.add(n); stack.extend(sorted(adj[n]-seen,reverse=True))
            nodes-=seen; components.append(tuple(sorted(seen)))
        return tuple(sorted(components))

def require_p1c_incidence_denominator(owner_semantics_resolved: bool) -> None:
    if not owner_semantics_resolved: raise EC1Path1InvariantError("EC1-DEP-C2E-DENOMINATOR-001: incidence/prevalence NOT_EVALUABLE; morphology remains lawful")
