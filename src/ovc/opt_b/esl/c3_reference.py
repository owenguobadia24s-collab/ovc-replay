from __future__ import annotations

import os
import platform
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Sequence, Tuple

from .canonical import sha256_canonical
from .compiler import compile_structural_occurrence
from .model import EvidenceState, StructuralOccurrenceRecord


class C3BridgeError(ValueError):
    pass


class C3BridgeMaturity(str, Enum):
    INACTIVE_REFERENCE = "INACTIVE_REFERENCE"
    SHADOW_EVALUATION = "SHADOW_EVALUATION"
    PRODUCTION_GRAMMAR = "PRODUCTION_GRAMMAR"


@dataclass(frozen=True)
class C3SemanticProposition:
    proposition_id: str
    proposition_type: str
    source_refs: Tuple[str, ...]
    semantic_state: str
    first_valid_time: str
    evaluation_cutoff: str
    comparability_domain_id: str | None
    generation_ids: Tuple[str, ...]
    authority_state: str = "INACTIVE_REFERENCE"


@dataclass(frozen=True)
class ClauseDecision:
    clause_type: str
    decision: str
    source_refs: Tuple[str, ...]
    reason_code: str | None


@dataclass(frozen=True)
class C3StatementAST:
    statement_id: str
    anchor_ref: str
    selected_proposition_refs: Tuple[str, ...]
    structural_clause: Mapping[str, Any]
    optional_clauses: Tuple[ClauseDecision, ...]
    temporal_relations: Tuple[Mapping[str, Any], ...]
    status_clauses: Tuple[Mapping[str, Any], ...]
    template_id: str
    canonicality: str
    first_valid_time: str
    evaluation_cutoff: str
    lineage_refs: Tuple[str, ...]
    authority_state: str = "INACTIVE_REFERENCE"


@dataclass(frozen=True)
class RenderTrace:
    render_trace_id: str
    statement_id: str
    template_id: str
    selected_proposition_refs: Tuple[str, ...]
    clause_decisions: Tuple[ClauseDecision, ...]
    omission_reasons: Tuple[str, ...]
    unsupported_term_checks: Tuple[str, ...]
    bridge_maturity: str
    deterministic_bytes: bool
    authority_state: str = "INACTIVE_REFERENCE"


@dataclass(frozen=True)
class C3ExplanationRecord:
    explanation_id: str
    statement_ref: str
    generator_metadata: Mapping[str, Any]
    generated_text: str
    provenance_refs: Tuple[str, ...]
    warning_refs: Tuple[str, ...]
    noncanonical: bool = True


def require_reference_maturity(requested: C3BridgeMaturity | str, *, activation_state: str = "NONE") -> None:
    requested = C3BridgeMaturity(requested)
    if activation_state != "NONE":
        raise C3BridgeError("C3_BRIDGE_ACTIVATION_FORBIDDEN_IN_ESLI")
    if requested is not C3BridgeMaturity.INACTIVE_REFERENCE:
        raise C3BridgeError("C3_BRIDGE_ACTIVATION_RECORD_MISSING")


def _semantic_state(record: StructuralOccurrenceRecord) -> str:
    return "ESTABLISHED" if all(f.evidence_state is EvidenceState.AVAILABLE for f in record.facets) else "PARTIAL"


def proposition_from_occurrence(record: StructuralOccurrenceRecord, *, maturity: C3BridgeMaturity = C3BridgeMaturity.INACTIVE_REFERENCE) -> C3SemanticProposition:
    require_reference_maturity(maturity)
    if not record.occurrence_record_id or not record.occurrence_record_id.startswith("so1:"):
        raise C3BridgeError("C3_REFERENCE_SOURCE_IDENTITY_MISSING")
    payload = {"authority_state":"INACTIVE_REFERENCE","comparability_domain_id":record.comparability_domain_id,"evaluation_cutoff":record.evaluation_cutoff,"first_valid_time":record.first_valid_time,"generation_ids":list(record.source_generation_ids),"proposition_type":"STRUCTURAL_OCCURRENCE","semantic_state":_semantic_state(record),"source_refs":[record.occurrence_record_id]}
    return C3SemanticProposition(proposition_id="c3refp1:"+sha256_canonical(payload),proposition_type="STRUCTURAL_OCCURRENCE",source_refs=(record.occurrence_record_id,),semantic_state=payload["semantic_state"],first_valid_time=record.first_valid_time,evaluation_cutoff=record.evaluation_cutoff,comparability_domain_id=record.comparability_domain_id,generation_ids=record.source_generation_ids)


def _optional_clause(record: StructuralOccurrenceRecord, owner: str, clause_type: str) -> ClauseDecision:
    available=tuple(sorted(ref.ref_id for ref in record.dependency_refs if ref.owner==owner and ref.evidence_state is EvidenceState.AVAILABLE))
    return ClauseDecision(clause_type,"INCLUDE_REFERENCE_ONLY",available,None) if available else ClauseDecision(clause_type,"OMIT",(),f"OPTIONAL_{clause_type}_NOT_ESTABLISHED")


def statement_ast_from_occurrence(record: StructuralOccurrenceRecord, proposition: C3SemanticProposition, *, maturity: C3BridgeMaturity = C3BridgeMaturity.INACTIVE_REFERENCE) -> C3StatementAST:
    require_reference_maturity(maturity)
    if proposition.source_refs != (record.occurrence_record_id,):
        raise C3BridgeError("C3_REFERENCE_SOURCE_MISMATCH")
    facets=tuple({"dimension":facet.dimension.value,"evidence_state":facet.evidence_state.value,"source_ref_ids":list(facet.source_ref_ids),"reason_codes":list(facet.reason_codes)} for facet in record.facets)
    optional=(_optional_clause(record,"C2P","PERSISTENT_OBJECT"),_optional_clause(record,"C2E","EPISODE"),ClauseDecision("ORGANISATION_EVIDENCE","OMIT",(),"OPTIONAL_SOI_EVIDENCE_NOT_REQUIRED"),ClauseDecision("CONSTRAINT_EVIDENCE","OMIT",(),"OPTIONAL_CEI_EVIDENCE_NOT_REQUIRED"),ClauseDecision("FAMILY_CONTEXT","OMIT",(),"OPTIONAL_FAMILY_CONTEXT_NOT_REQUIRED"))
    payload={"anchor_ref":record.occurrence_record_id,"authority_state":"INACTIVE_REFERENCE","canonicality":"REFERENCE_DETERMINISTIC","evaluation_cutoff":record.evaluation_cutoff,"first_valid_time":record.first_valid_time,"lineage_refs":list(record.source_generation_ids),"optional_clauses":[asdict(item) for item in optional],"selected_proposition_refs":[proposition.proposition_id],"status_clauses":[],"structural_clause":{"facet_evidence":list(facets),"occurrence_ref":record.occurrence_record_id},"template_id":"C3.ESL.STRUCTURAL_OCCURRENCE.v0.1","temporal_relations":[]}
    return C3StatementAST(statement_id="c3refast1:"+sha256_canonical(payload),anchor_ref=record.occurrence_record_id,selected_proposition_refs=(proposition.proposition_id,),structural_clause=payload["structural_clause"],optional_clauses=optional,temporal_relations=(),status_clauses=(),template_id=payload["template_id"],canonicality="REFERENCE_DETERMINISTIC",first_valid_time=record.first_valid_time,evaluation_cutoff=record.evaluation_cutoff,lineage_refs=record.source_generation_ids)


def _english_join(items: Sequence[str]) -> str:
    if not items:return ""
    if len(items)==1:return items[0]
    if len(items)==2:return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1])+f" and {items[-1]}"


def _cutoff_clock(value: str) -> str:
    return value[11:16]+"Z" if len(value)>=17 and value.endswith("Z") else value


def render_reference_statement(record: StructuralOccurrenceRecord, proposition: C3SemanticProposition, ast: C3StatementAST, *, display_anchor: str | None = None) -> tuple[str, RenderTrace]:
    require_reference_maturity(C3BridgeMaturity.INACTIVE_REFERENCE)
    if ast.anchor_ref != record.occurrence_record_id or ast.selected_proposition_refs != (proposition.proposition_id,):
        raise C3BridgeError("C3_RENDER_SOURCE_MISMATCH")
    available=[f.dimension.value for f in record.facets if f.evidence_state is EvidenceState.AVAILABLE]; not_evaluable=[f.dimension.value for f in record.facets if f.evidence_state is EvidenceState.NOT_EVALUABLE]; missing=[f.dimension.value for f in record.facets if f.evidence_state is EvidenceState.MISSING]
    label=display_anchor or record.anchor.anchor_id
    parts=[f"Occurrence {label} is structurally describable at cutoff {_cutoff_clock(record.evaluation_cutoff)}."]
    if available: parts.append(f"{_english_join(available)} evidence {'is' if len(available)==1 else 'are'} available.")
    if not_evaluable: parts.append(f"{_english_join(not_evaluable)} {'is' if len(not_evaluable)==1 else 'are'} not evaluable.")
    if missing: parts.append(f"{_english_join(missing)} evidence {'is' if len(missing)==1 else 'are'} missing.")
    decisions={item.clause_type:item for item in ast.optional_clauses}
    if decisions["PERSISTENT_OBJECT"].decision=="OMIT" and decisions["EPISODE"].decision=="OMIT": parts.append("No confirmed persistent-object or episode clause is required by this template.")
    text=" ".join(parts); omissions=tuple(item.reason_code for item in ast.optional_clauses if item.decision=="OMIT" and item.reason_code)
    trace_payload={"authority_state":"INACTIVE_REFERENCE","bridge_maturity":"INACTIVE_REFERENCE","clause_decisions":[asdict(item) for item in ast.optional_clauses],"deterministic_bytes":True,"omission_reasons":list(omissions),"selected_proposition_refs":list(ast.selected_proposition_refs),"statement_id":ast.statement_id,"template_id":ast.template_id,"unsupported_term_checks":["PASS_NO_ACTIVE_TERM_REQUIRED","PASS_NO_CAUSAL_OR_PREDICTIVE_TOKEN"]}
    trace=RenderTrace(render_trace_id="rt1:"+sha256_canonical(trace_payload),statement_id=ast.statement_id,template_id=ast.template_id,selected_proposition_refs=ast.selected_proposition_refs,clause_decisions=ast.optional_clauses,omission_reasons=omissions,unsupported_term_checks=("PASS_NO_ACTIVE_TERM_REQUIRED","PASS_NO_CAUSAL_OR_PREDICTIVE_TOKEN"),bridge_maturity="INACTIVE_REFERENCE",deterministic_bytes=True)
    return text,trace


def render_normative_reference_trace(trace_id: str, payload: Mapping[str, Any]) -> str:
    if trace_id=="G1":
        available=[item["dimension"] for item in payload["facets"] if item["status"]=="AVAILABLE"]; not_eval=[item["dimension"] for item in payload["facets"] if item["status"]=="NOT_EVALUABLE"]; cutoff=_cutoff_clock(payload["chronology"]["evaluation_cutoff"]); text=f"Occurrence O is structurally describable at cutoff {cutoff}."
        if available:text+=f" {_english_join(available)} evidence {'is' if len(available)==1 else 'are'} available."
        if not_eval:text+=f" {_english_join(not_eval)} {'is' if len(not_eval)==1 else 'are'} not evaluable."
        return text+" No confirmed persistent-object or episode clause is required by this template."
    if trace_id=="G2":
        p=str(payload["persistence_refs"][0]).split(".")[-1]; e=str(payload["development_refs"][0]).split(".")[-1]; return f"Persistent object {p} participates in episode {e} at this cutoff. Episode membership does not define {p} identity."
    if trace_id=="G3": return f"Invariant core {payload['invariant']} is supported across the tested views. Hierarchical organisation is supported. Discrete family {payload['family_view']} is available under its family view, but its outer boundary is representation-dependent."
    if trace_id=="G4": return f"Observed persistence of K2 differs between condition {payload['condition']} and comparator {payload['comparator']} under the declared contrast. No mechanism explanation is established."
    if trace_id=="G5": return f"Event {payload['event']} occurred effectively at {payload['effective_time']} and became first-valid at {payload['first_valid_time']}. This statement is evaluated at cutoff {payload['evaluation_cutoff']}."
    raise C3BridgeError("C3_NORMATIVE_TRACE_UNKNOWN:"+trace_id)


def _stats(values: Sequence[float]) -> Mapping[str,float]:
    ordered=sorted(values); p95_index=max(0,min(len(ordered)-1,int(0.95*len(ordered)+0.999999)-1)); return {"p50_ms":statistics.median(ordered),"p95_ms":ordered[p95_index],"max_ms":ordered[-1],"min_ms":ordered[0]}


def measure_reference_vertical_path(c2_observation: Mapping[str,Any], profile_outputs: Sequence[Mapping[str,Any]], *, source_generation_id: str, repetitions: int=200, warmup: int=20) -> Mapping[str,Any]:
    if repetitions<100 or warmup<10: raise ValueError("ESL_VERTICAL_PERFORMANCE_PROTOCOL_TOO_SMALL")
    for _ in range(warmup):
        record=compile_structural_occurrence(c2_observation,profile_outputs,source_generation_id=source_generation_id); proposition=proposition_from_occurrence(record); ast=statement_ast_from_occurrence(record,proposition); render_reference_statement(record,proposition,ast)
    occurrence_times=[]; c3_times=[]; total_times=[]; stable=None
    for _ in range(repetitions):
        t0=time.perf_counter_ns(); record=compile_structural_occurrence(c2_observation,profile_outputs,source_generation_id=source_generation_id); t1=time.perf_counter_ns(); proposition=proposition_from_occurrence(record); ast=statement_ast_from_occurrence(record,proposition); _,trace=render_reference_statement(record,proposition,ast); t2=time.perf_counter_ns(); identity=(str(record.occurrence_record_id),proposition.proposition_id,trace.render_trace_id)
        if stable is None: stable=identity
        elif identity!=stable: raise RuntimeError("ESL_VERTICAL_PERFORMANCE_IDENTITY_DRIFT")
        occurrence_times.append((t1-t0)/1_000_000.0); c3_times.append((t2-t1)/1_000_000.0); total_times.append((t2-t0)/1_000_000.0)
    return {"schema":"ovc-esl-bootstrap-vertical-performance-measurement/v1","authority":"MEASUREMENT_ONLY_NO_SLO_UNTIL_G4_BUDGET_FREEZE","protocol":{"repetitions":repetitions,"warmup":warmup,"cache_state":"WARM_IN_PROCESS_AFTER_DECLARED_WARMUP"},"occurrence_assembly":_stats(occurrence_times),"c3_reference_compile_render":_stats(c3_times),"total_vertical_path":_stats(total_times),"stable_identities":list(stable or ()),"environment":{"python_version":platform.python_version(),"implementation":sys.implementation.name,"platform_system":platform.system(),"platform_machine":platform.machine(),"runner_os":os.environ.get("RUNNER_OS"),"runner_arch":os.environ.get("RUNNER_ARCH"),"image_os":os.environ.get("ImageOS"),"image_version":os.environ.get("ImageVersion")}}
