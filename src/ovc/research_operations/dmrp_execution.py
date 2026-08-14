from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .canonical import canonical_sha256

STAGE_SEMANTIC_DEPENDENCIES = {
    "SOURCE_HYDRATION": ("EXACT_SOURCE_RELEASE_MANIFEST",),
    "C2_VNEXT": ("SOURCE_IDENTITY", "EXACT_C2_PACKAGE_OWNER_SEMANTICS"),
    "C2E": ("C2_SEMANTIC_INPUTS", "EXACT_C2E_BOUNDARY_PACK"),
    "P1_DENOMINATOR_CONSTRUCTION": ("EC1_GENERATION", "EXACT_POPULATION_DEFINITION", "CALENDAR_POLICY"),
    "PREDICATE_COMPILATION": ("EC1_IDENTITY_FIELD_MANIFEST", "CANONICAL_SERIALIZATION_CONTRACT"),
    "PATTERN_LATTICE": ("P1_SEARCH_UNIVERSE", "EC1_SEARCH_PARAMETER_PACK"),
    "CORE_CLOSURE_EXTRACTION": ("PATTERN_LATTICE_SEMANTIC_IDENTITY",),
    "ADVERSARIAL_REVIEW": ("QUESTION_REGISTRY", "ADVERSARIAL_PROTOCOL", "EVIDENCE_DEPENDENCIES"),
    "REVIEW_PACKET": ("COMPLETE_EC1_GENERATION", "REPRODUCED_EVIDENCE_REFS"),
}

F0_ALLOWED_FIELDS = frozenset({
    "run_id", "stage_id", "eligible_count", "processed_count", "runtime_seconds", "cpu_seconds",
    "peak_rss_bytes", "io_read_bytes", "io_write_bytes", "artifact_size_bytes", "cache_state",
    "checkpoint_state", "capacity_state", "errors", "reason_codes", "qa_state",
})
F0_FORBIDDEN_FIELDS = frozenset({
    "structural_predicates", "signature", "signature_id", "pattern_id", "pattern_recurrence_count",
    "closed_pattern", "minimal_generators", "episode_morphology", "candidate_id", "candidate_dossier",
    "near_neighbour_examples", "near_neighbor_examples",
})

class F0InformationLeakError(ValueError): pass
class DMRPExecutionBindingError(ValueError): pass

@dataclass(frozen=True)
class DMRPExecutionBinding:
    binding_id: str
    study_id: str
    cycle_id: str
    object_ids: tuple[str,...]
    irof_semantic_run_id: str
    required_stage_output_types: Mapping[str,tuple[str,...]]
    authority_binding_ids: tuple[str,...]
    research_operations_record_refs: tuple[str,...]
    reproduction_requirements: tuple[str,...]
    authority_effect: str = "NONE"

    def __post_init__(self):
        if self.authority_effect != "NONE": raise DMRPExecutionBindingError("execution binding cannot grant authority")
        for value in (self.binding_id,self.study_id,self.cycle_id,self.irof_semantic_run_id):
            if not value: raise DMRPExecutionBindingError("required identity missing")

    def semantic_dict(self) -> dict[str,Any]:
        return {"binding_id":self.binding_id,"study_id":self.study_id,"cycle_id":self.cycle_id,"object_ids":sorted(self.object_ids),"irof_semantic_run_id":self.irof_semantic_run_id,"required_stage_output_types":{k:list(v) for k,v in sorted(self.required_stage_output_types.items())},"authority_binding_ids":sorted(self.authority_binding_ids),"research_operations_record_refs":sorted(self.research_operations_record_refs),"reproduction_requirements":sorted(self.reproduction_requirements)}
    @property
    def semantic_sha256(self): return canonical_sha256(self.semantic_dict())
    def pack_bindings(self): return {"dmrp_execution_binding":self.semantic_sha256}

@dataclass(frozen=True)
class StageSemanticDependencyMatrix:
    bindings: Mapping[str,tuple[str,...]] = field(default_factory=lambda: dict(STAGE_SEMANTIC_DEPENDENCIES))
    def validate_complete(self) -> None:
        if set(self.bindings)!=set(STAGE_SEMANTIC_DEPENDENCIES): raise DMRPExecutionBindingError("stage semantic dependency matrix incomplete")
        for key,required in STAGE_SEMANTIC_DEPENDENCIES.items():
            if tuple(self.bindings[key])!=tuple(required): raise DMRPExecutionBindingError(f"stage binding drift: {key}")

@dataclass(frozen=True)
class F0BlindedProjection:
    values: Mapping[str,Any]
    def __post_init__(self):
        leak_scan(self.values)
        unknown=set(self.values)-F0_ALLOWED_FIELDS
        if unknown: raise F0InformationLeakError(f"operator-visible F0 field not allowlisted: {sorted(unknown)}")
    @property
    def semantic_sha256(self): return canonical_sha256(dict(self.values))


def _walk(value: Any, path: str=""):
    if isinstance(value,Mapping):
        for k,v in value.items():
            p=f"{path}.{k}" if path else str(k); yield p,str(k),v; yield from _walk(v,p)
    elif isinstance(value,(list,tuple)):
        for i,v in enumerate(value): yield from _walk(v,f"{path}[{i}]")

def leak_scan(value: Any) -> None:
    leaks=[]
    for path,key,_ in _walk(value):
        if key in F0_FORBIDDEN_FIELDS: leaks.append(path)
    if leaks: raise F0InformationLeakError(f"F0 structural-content leak: {sorted(leaks)}")

@dataclass(frozen=True)
class OperatorTouch:
    surface: str
    result: str
    fields_seen: tuple[str,...]
    authority_effect: str = "NONE"
    def __post_init__(self):
        if self.authority_effect!="NONE": raise ValueError("operator touch has no authority")
        disallowed=set(self.fields_seen)-F0_ALLOWED_FIELDS
        if disallowed: raise F0InformationLeakError(f"operator touch saw forbidden/unallowlisted fields: {sorted(disallowed)}")

@dataclass
class OperatorTouchLedger:
    touches: list[OperatorTouch]=field(default_factory=list)
    def add(self,touch:OperatorTouch): self.touches.append(touch)
    @property
    def semantic_sha256(self): return canonical_sha256([t.__dict__ for t in self.touches])

def research_operations_real_append_authorised(authority_bindings: Sequence[str]) -> bool:
    return "RESEARCH_OPERATIONS_DMRP_EC1_BOUNDED_APPEND" in authority_bindings
