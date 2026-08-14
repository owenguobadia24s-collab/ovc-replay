from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping, Sequence

from .canonical import sha256_canonical
from .c3_reference import C3BridgeError, C3BridgeMaturity, C3ExplanationRecord, ClauseDecision, require_reference_maturity


class C3ESLConformanceError(ValueError):
    pass


PROPOSITION_TYPES = frozenset({
    "STRUCTURAL_OCCURRENCE",
    "ORGANISATION_EVIDENCE",
    "CONSTRAINT_EVIDENCE",
    "EVENT_OCCURRENCE",
    "PERSISTENT_OBJECT_REFERENCE",
    "EPISTEMIC_STATUS",
})

CLAUSE_TYPES = frozenset({
    "STRUCTURAL_STATE",
    "ORGANISATION",
    "FAMILY_CONTEXT",
    "CONSTRAINT",
    "EVENT",
    "PERSISTENT_OBJECT",
    "STATUS",
})

RESOLUTION_STATES = frozenset({
    "RESOLVED",
    "PARTIAL",
    "AMBIGUOUS",
    "UNRESOLVED",
    "NOT_AVAILABLE",
    "NOT_EVALUABLE",
    "CONFLICT",
    "QUARANTINED",
})

DEPENDENCY_ROLES = frozenset({"REQUIRED", "OPTIONAL", "CONDITIONAL_REQUIRED", "STRATIFIER", "FILTER", "DISPLAY_ONLY", "PROVENANCE_ONLY", "FORBIDDEN"})


def _strings(values: Sequence[Any], code: str, *, allow_empty: bool = True) -> list[str]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise C3ESLConformanceError(code)
    result = [str(v) for v in values]
    if any(not item for item in result) or (not allow_empty and not result):
        raise C3ESLConformanceError(code)
    return result


def build_c3_esl_dependency_manifest(*, manifest_id: str, dependencies: Sequence[Mapping[str, Any]], template_id: str) -> dict[str, Any]:
    normalized: list[dict[str, str]] = []
    for item in dependencies:
        role = str(item.get("role", ""))
        clause_type = str(item.get("clause_type", ""))
        if role not in DEPENDENCY_ROLES:
            raise C3ESLConformanceError("C3_ESL_DEPENDENCY_ROLE_INVALID")
        if clause_type not in CLAUSE_TYPES:
            raise C3ESLConformanceError("C3_ESL_CLAUSE_TYPE_INVALID")
        source_owner = str(item.get("source_owner", ""))
        source_type = str(item.get("source_type", ""))
        if not source_owner or not source_type:
            raise C3ESLConformanceError("C3_ESL_DEPENDENCY_SOURCE_REQUIRED")
        normalized.append({"clause_type": clause_type, "role": role, "source_owner": source_owner, "source_type": source_type})
    payload = {
        "schema": "ovc-esl-c3-dependency-manifest/v1",
        "manifest_id": str(manifest_id),
        "template_id": str(template_id),
        "dependencies": sorted(normalized, key=lambda x: (x["clause_type"], x["source_owner"], x["source_type"], x["role"])),
        "bridge_maturity": C3BridgeMaturity.INACTIVE_REFERENCE.value,
        "authority_effect": "NONE",
    }
    payload["logical_hash"] = sha256_canonical(payload)
    return payload


def build_c3_esl_proposition(*, proposition_type: str, source_ref: str, source_owner: str, resolution_state: str, first_valid_time: str, evaluation_cutoff: str, generation_refs: Sequence[Any], dependency_manifest_id: str, term_generation_id: str | None = None, term_admission_state: str = "NOT_ADMITTED") -> dict[str, Any]:
    require_reference_maturity(C3BridgeMaturity.INACTIVE_REFERENCE)
    ptype = str(proposition_type)
    state = str(resolution_state)
    if ptype not in PROPOSITION_TYPES:
        raise C3ESLConformanceError("C3_ESL_PROPOSITION_TYPE_INVALID")
    if state not in RESOLUTION_STATES:
        raise C3ESLConformanceError("C3_ESL_RESOLUTION_STATE_INVALID")
    if term_admission_state == "ADMITTED_ACTIVE":
        raise C3ESLConformanceError("C3_ESL_ACTIVE_TERM_OPERATOR_RESERVED")
    if term_generation_id and term_admission_state not in {"NOT_ADMITTED", "ADMISSION_CANDIDATE", "ADMITTED_SHADOW"}:
        raise C3ESLConformanceError("C3_ESL_TERM_ADMISSION_STATE_INVALID")
    payload = {
        "schema": "ovc-esl-c3-semantic-proposition/v1",
        "proposition_type": ptype,
        "source_ref": str(source_ref),
        "source_owner": str(source_owner),
        "resolution_state": state,
        "first_valid_time": str(first_valid_time),
        "evaluation_cutoff": str(evaluation_cutoff),
        "generation_refs": _strings(generation_refs, "C3_ESL_GENERATION_REFS_INVALID", allow_empty=False),
        "dependency_manifest_id": str(dependency_manifest_id),
        "term_generation_id": term_generation_id,
        "term_admission_state": term_admission_state,
        "bridge_maturity": C3BridgeMaturity.INACTIVE_REFERENCE.value,
        "authority_effect": "NONE",
    }
    payload["proposition_id"] = "c3eslp1:" + sha256_canonical(payload)
    return payload


def build_c3_esl_statement_ast(*, anchor_ref: str, propositions: Sequence[Mapping[str, Any]], dependency_manifest: Mapping[str, Any], template_id: str, predecessor_statement_id: str | None = None) -> dict[str, Any]:
    require_reference_maturity(C3BridgeMaturity.INACTIVE_REFERENCE)
    if dependency_manifest.get("schema") != "ovc-esl-c3-dependency-manifest/v1":
        raise C3ESLConformanceError("C3_ESL_DEPENDENCY_MANIFEST_INVALID")
    by_type: dict[str, list[Mapping[str, Any]]] = {}
    for proposition in propositions:
        if proposition.get("schema") != "ovc-esl-c3-semantic-proposition/v1":
            raise C3ESLConformanceError("C3_ESL_PROPOSITION_SCHEMA_INVALID")
        if proposition.get("bridge_maturity") != C3BridgeMaturity.INACTIVE_REFERENCE.value:
            raise C3ESLConformanceError("C3_ESL_BRIDGE_MATURITY_INVALID")
        by_type.setdefault(str(proposition["proposition_type"]), []).append(proposition)
    clause_decisions: list[dict[str, Any]] = []
    selected: list[str] = []
    for dependency in dependency_manifest["dependencies"]:
        clause = dependency["clause_type"]
        source_type = dependency["source_type"]
        candidates = by_type.get(source_type, [])
        if dependency["role"] == "FORBIDDEN" and candidates:
            raise C3ESLConformanceError("C3_ESL_FORBIDDEN_DEPENDENCY_CONSUMED:" + clause)
        if dependency["role"] in {"REQUIRED", "CONDITIONAL_REQUIRED"} and not candidates:
            clause_decisions.append({"clause_type": clause, "decision": "UNRESOLVED", "source_refs": [], "reason_code": "REQUIRED_CLAUSE_SOURCE_UNAVAILABLE"})
            continue
        if candidates:
            ids = sorted(str(item["proposition_id"]) for item in candidates)
            selected.extend(ids)
            clause_decisions.append({"clause_type": clause, "decision": "INCLUDE", "source_refs": ids, "reason_code": None})
        else:
            clause_decisions.append({"clause_type": clause, "decision": "OMIT", "source_refs": [], "reason_code": "OPTIONAL_CLAUSE_NOT_ESTABLISHED"})
    payload = {
        "schema": "ovc-esl-c3-statement-ast/v1",
        "anchor_ref": str(anchor_ref),
        "selected_proposition_refs": sorted(set(selected)),
        "clause_decisions": clause_decisions,
        "template_id": str(template_id),
        "dependency_manifest_id": dependency_manifest["manifest_id"],
        "predecessor_statement_id": predecessor_statement_id,
        "generation_policy": "APPEND_ONLY_NEW_GENERATION" if predecessor_statement_id else "GENESIS",
        "canonicality": "REFERENCE_DETERMINISTIC",
        "bridge_maturity": C3BridgeMaturity.INACTIVE_REFERENCE.value,
        "authority_effect": "NONE",
    }
    payload["statement_id"] = "c3eslast1:" + sha256_canonical(payload)
    return payload


def render_c3_esl_statement(ast: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    require_reference_maturity(C3BridgeMaturity.INACTIVE_REFERENCE)
    if ast.get("schema") != "ovc-esl-c3-statement-ast/v1":
        raise C3ESLConformanceError("C3_ESL_AST_SCHEMA_INVALID")
    included = [item["clause_type"] for item in ast["clause_decisions"] if item["decision"] == "INCLUDE"]
    unresolved = [item["clause_type"] for item in ast["clause_decisions"] if item["decision"] == "UNRESOLVED"]
    omitted = [item["clause_type"] for item in ast["clause_decisions"] if item["decision"] == "OMIT"]
    parts = [f"Structural statement for {ast['anchor_ref']} is rendered from an inactive reference AST."]
    if included:
        parts.append("Included clauses: " + ", ".join(included) + ".")
    if unresolved:
        parts.append("Unresolved required clauses: " + ", ".join(unresolved) + ".")
    if omitted:
        parts.append("Optional clauses not established: " + ", ".join(omitted) + ".")
    text = " ".join(parts)
    trace_payload = {
        "schema": "ovc-esl-c3-render-trace/v1",
        "statement_id": ast["statement_id"],
        "template_id": ast["template_id"],
        "clause_decisions": ast["clause_decisions"],
        "rendered_text_sha256": sha256_canonical({"text": text}),
        "llm_nodes": [],
        "bridge_maturity": C3BridgeMaturity.INACTIVE_REFERENCE.value,
        "authority_effect": "NONE",
    }
    trace_payload["render_trace_id"] = "c3eslrt1:" + sha256_canonical(trace_payload)
    return text, trace_payload


def build_c3_explanation_record(*, statement_ref: str, generated_text: str, generator_metadata: Mapping[str, Any], provenance_refs: Sequence[Any], warning_refs: Sequence[Any] = ()) -> dict[str, Any]:
    payload = {
        "schema": "ovc-esl-c3-explanation-record/v1",
        "statement_ref": str(statement_ref),
        "generator_metadata": dict(generator_metadata),
        "generated_text": str(generated_text),
        "provenance_refs": _strings(provenance_refs, "C3_ESL_EXPLANATION_PROVENANCE_INVALID", allow_empty=False),
        "warning_refs": _strings(warning_refs, "C3_ESL_EXPLANATION_WARNINGS_INVALID"),
        "channel": "EXPLANATION",
        "authority": "NON_CANONICAL",
        "identity_projection": "EXCLUDED",
        "render_trace_eligible": False,
    }
    payload["explanation_id"] = "c3ex1:" + sha256_canonical(payload)
    return payload


def assert_no_explanation_in_canonical_path(*, render_trace: Mapping[str, Any], explanation: Mapping[str, Any] | None = None) -> None:
    if render_trace.get("llm_nodes"):
        raise C3ESLConformanceError("LLM_CANONICAL_PATH_FORBIDDEN")
    if explanation is not None and explanation.get("render_trace_eligible") is not False:
        raise C3ESLConformanceError("LLM_CANONICAL_PATH_FORBIDDEN")


def request_bridge_maturity(target: str, *, authority_record_id: str | None = None, vocabulary_binding_id: str | None = None) -> str:
    target_state = C3BridgeMaturity(target)
    if target_state is C3BridgeMaturity.INACTIVE_REFERENCE:
        return target_state.value
    if not authority_record_id or not vocabulary_binding_id:
        raise C3ESLConformanceError("C3_BRIDGE_ACTIVATION_RECORD_MISSING")
    raise C3ESLConformanceError("C3_BRIDGE_ACTIVATION_OPERATOR_RESERVED")
