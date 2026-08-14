from __future__ import annotations

import copy
import re
from typing import Any, Mapping, Sequence

from .canonical import sha256_canonical


class CEIError(ValueError):
    """Raised when CEI evidence would violate the ratified descriptive-only contract."""


CONSTRAINT_TARGETS = frozenset({"EMERGENCE", "PERSISTENCE", "ORGANISATION", "TRANSITION", "STRUCTURAL_EVENT", "AMBIGUITY_BOUNDARY"})
TEMPORAL_ROLES = frozenset({"PRE_EXISTING", "AT_ANCHOR", "CONCURRENT", "TIME_VARYING_DURING_TARGET", "POST_TARGET"})
CONDITION_TYPES = frozenset({"STRUCTURAL", "TEMPORAL", "AUXILIARY", "DATA_QUALITY"})
COMPARISON_DESIGNS = frozenset({"STRATIFIED", "MATCHED", "LONGITUDINAL", "CHRONOLOGICAL", "DECLARED_OTHER"})
POPULATION_STATES = frozenset({"CONDITION_A", "COMPARATOR_B", "EXCLUDED", "CENSORED", "MISSING", "NOT_COMPARABLE", "NOT_EVALUABLE"})
EVIDENCE_STATUSES = frozenset({"EVALUATED", "NOT_EVALUABLE", "NOT_COMPARABLE", "UNRESOLVED", "QUARANTINED"})
AST_NODE_TYPES = frozenset({"ALL_OF", "ANY_OF", "NOT", "FIELD_REF", "CONST", "COMPARE", "ENUM_MATCH", "EXISTS", "RELATION_MATCH", "STATE_MATCH", "SCOPE_MATCH"})
LEAF_NODE_TYPES = frozenset({"FIELD_REF", "CONST"})
_FORBIDDEN_TOKENS = frozenset({"cause", "causal", "causes", "caused", "because", "mechanism", "intent", "institutional_intent", "drives", "predicts", "forecast", "probability", "risk", "exposure", "trade", "execution", "outcome", "expected_return", "mfe", "mae", "validation"})


def _copy(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _copy(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_copy(v) for v in value]
    return copy.deepcopy(value)


def _authority() -> dict[str, str]:
    return {
        "authority_state": "INACTIVE_CONFORMANCE_ONLY",
        "authority_effect": "NONE",
        "scientific_selection": "NONE",
        "semantic_promotion": "NONE",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
    }


def _require(value: Any, code: str) -> str:
    text = str(value or "")
    if not text:
        raise CEIError(code)
    return text


def _tokenise(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9_]+", text.lower()) if t}


def _scan_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            tokens = _tokenise(str(key))
            if tokens & _FORBIDDEN_TOKENS:
                raise CEIError(f"CEI_FORBIDDEN_CAUSAL_OR_OUTCOME_FIELD:{path}.{key}")
            _scan_forbidden(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for i, child in enumerate(value):
            _scan_forbidden(child, f"{path}[{i}]")
    elif isinstance(value, str) and (_tokenise(value) & _FORBIDDEN_TOKENS):
        raise CEIError(f"CEI_FORBIDDEN_CAUSAL_OR_OUTCOME_TOKEN:{path}")


def validate_constraint_ast(ast: Mapping[str, Any]) -> dict[str, Any]:
    node = _copy(ast)
    if not isinstance(node, Mapping):
        raise CEIError("CEI_AST_OBJECT_REQUIRED")
    _scan_forbidden(node)
    node_type = str(node.get("type") or "")
    if node_type not in AST_NODE_TYPES:
        raise CEIError("CEI_AST_NODE_TYPE_NOT_REGISTERED:" + node_type)
    children = node.get("children", [])
    if node_type in LEAF_NODE_TYPES:
        if children:
            raise CEIError("CEI_AST_LEAF_CHILDREN_FORBIDDEN")
        if node_type == "FIELD_REF":
            _require(node.get("source_namespace"), "CEI_FIELD_SOURCE_NAMESPACE_REQUIRED")
            _require(node.get("field_path"), "CEI_FIELD_PATH_REQUIRED")
            if node.get("source_authority") != "LAWFUL_UPSTREAM":
                raise CEIError("CEI_CONDITION_SOURCE_AUTHORITY_REQUIRED")
        if node_type == "CONST" and "value" not in node:
            raise CEIError("CEI_CONST_VALUE_REQUIRED")
    else:
        if not isinstance(children, list) or not children:
            raise CEIError("CEI_AST_CHILDREN_REQUIRED")
        if node_type == "NOT" and len(children) != 1:
            raise CEIError("CEI_AST_NOT_ARITY_INVALID")
        for child in children:
            validate_constraint_ast(child)
    return dict(node)


def build_condition(*, name: str, condition_type: str, temporal_role: str, source_ref: str, first_valid_time: str, target_anchor_time: str, ast: Mapping[str, Any]) -> dict[str, Any]:
    ctype = str(condition_type)
    role = str(temporal_role)
    if ctype not in CONDITION_TYPES:
        raise CEIError("CEI_CONDITION_TYPE_INVALID:" + ctype)
    if role not in TEMPORAL_ROLES:
        raise CEIError("CEI_TEMPORAL_ROLE_INVALID:" + role)
    validated_ast = validate_constraint_ast(ast)
    fvt = _require(first_valid_time, "CEI_CONDITION_FVT_REQUIRED")
    anchor = _require(target_anchor_time, "CEI_TARGET_ANCHOR_REQUIRED")
    if role in {"PRE_EXISTING", "AT_ANCHOR"} and fvt > anchor:
        raise CEIError("CEI_RETROSPECTIVE_PRECONDITION_FORBIDDEN")
    payload = {
        "schema": "ovc-esl-constraint-condition/v1",
        "name": _require(name, "CEI_CONDITION_NAME_REQUIRED"),
        "condition_type": ctype,
        "temporal_role": role,
        "source_ref": _require(source_ref, "CEI_CONDITION_SOURCE_REQUIRED"),
        "source_authority": "LAWFUL_UPSTREAM",
        "first_valid_time": fvt,
        "target_anchor_time": anchor,
        "render_as_precondition": role in {"PRE_EXISTING", "AT_ANCHOR"},
        "constraint_ast": validated_ast,
        "authority": _authority(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "constraint_condition_id": "cei-cond-v1:" + logical_hash, "logical_hash": logical_hash}


def build_population_manifest(*, population_id: str, eligible_occurrence_ids: Sequence[str], states: Mapping[str, str], sample_unit: str, chronology_partition: str, comparability_domain_id: str) -> dict[str, Any]:
    eligible = sorted({str(x) for x in eligible_occurrence_ids})
    if not eligible:
        raise CEIError("CEI_POPULATION_EMPTY")
    state_map = {str(k): str(v) for k, v in states.items()}
    if set(state_map) != set(eligible):
        raise CEIError("CEI_POPULATION_RECONCILIATION_INCOMPLETE")
    for state in state_map.values():
        if state not in POPULATION_STATES:
            raise CEIError("CEI_POPULATION_STATE_INVALID:" + state)
    payload = {
        "schema": "ovc-esl-constraint-population-manifest/v1",
        "population_id": _require(population_id, "CEI_POPULATION_ID_REQUIRED"),
        "eligible_occurrence_ids": eligible,
        "states": dict(sorted(state_map.items())),
        "sample_unit": _require(sample_unit, "CEI_SAMPLE_UNIT_REQUIRED"),
        "chronology_partition": _require(chronology_partition, "CEI_CHRONOLOGY_PARTITION_REQUIRED"),
        "comparability_domain_id": _require(comparability_domain_id, "CEI_COMPARABILITY_DOMAIN_REQUIRED"),
        "counts": {state: list(state_map.values()).count(state) for state in sorted(POPULATION_STATES)},
        "authority": _authority(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "population_manifest_id": "cei-pop-v1:" + logical_hash, "logical_hash": logical_hash}


def build_contrast_spec(*, condition_a: Mapping[str, Any], comparator_b: Mapping[str, Any], comparison_design: str, denominator_name: str, metric_ids: Sequence[str], confounding_fields: Sequence[str] = ()) -> dict[str, Any]:
    a = dict(condition_a)
    b = dict(comparator_b)
    if a.get("constraint_condition_id") == b.get("constraint_condition_id"):
        raise CEIError("CEI_COMPARATOR_MUST_DIFFER")
    design = str(comparison_design)
    if design not in COMPARISON_DESIGNS:
        raise CEIError("CEI_COMPARISON_DESIGN_INVALID:" + design)
    metrics = sorted({_require(x, "CEI_METRIC_ID_REQUIRED") for x in metric_ids})
    if not metrics:
        raise CEIError("CEI_METRIC_IDS_REQUIRED")
    payload = {
        "schema": "ovc-esl-constraint-contrast-spec/v1",
        "condition_a_id": _require(a.get("constraint_condition_id"), "CEI_CONDITION_A_ID_REQUIRED"),
        "comparator_b_id": _require(b.get("constraint_condition_id"), "CEI_COMPARATOR_B_ID_REQUIRED"),
        "comparison_design": design,
        "method_neutral": True,
        "matching_or_support_threshold": None,
        "denominator_name": _require(denominator_name, "CEI_DENOMINATOR_NAME_REQUIRED"),
        "metric_ids": metrics,
        "confounding_fields": sorted({str(x) for x in confounding_fields}),
        "causal_adjustment_claim": "FORBIDDEN",
        "authority": _authority(),
    }
    _scan_forbidden({k: v for k, v in payload.items() if k not in {"causal_adjustment_claim"}})
    logical_hash = sha256_canonical(payload)
    return {**payload, "contrast_spec_id": "cei-contrast-v1:" + logical_hash, "logical_hash": logical_hash}


def build_constraint_evidence(*, target: str, condition_a: Mapping[str, Any], comparator_b: Mapping[str, Any], population: Mapping[str, Any], contrast: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]], status: str = "EVALUATED") -> dict[str, Any]:
    target_id = str(target)
    if target_id not in CONSTRAINT_TARGETS:
        raise CEIError("CEI_TARGET_INVALID:" + target_id)
    status_id = str(status)
    if status_id not in EVIDENCE_STATUSES:
        raise CEIError("CEI_EVIDENCE_STATUS_INVALID:" + status_id)
    if condition_a.get("constraint_condition_id") == comparator_b.get("constraint_condition_id"):
        raise CEIError("CEI_COMPARATOR_MUST_DIFFER")
    if contrast.get("condition_a_id") != condition_a.get("constraint_condition_id") or contrast.get("comparator_b_id") != comparator_b.get("constraint_condition_id"):
        raise CEIError("CEI_CONTRAST_CONDITION_BINDING_MISMATCH")
    metric_records = [_copy(m) for m in metrics]
    _scan_forbidden(metric_records)
    payload = {
        "schema": "ovc-esl-constraint-evidence/v1",
        "target": target_id,
        "condition_a_id": condition_a["constraint_condition_id"],
        "comparator_b_id": comparator_b["constraint_condition_id"],
        "population_manifest_id": _require(population.get("population_manifest_id"), "CEI_POPULATION_MANIFEST_ID_REQUIRED"),
        "contrast_spec_id": _require(contrast.get("contrast_spec_id"), "CEI_CONTRAST_SPEC_ID_REQUIRED"),
        "metrics": metric_records,
        "status": status_id,
        "interpretation_class": "DESCRIPTIVE_CONDITIONAL_ASSOCIATION_ONLY",
        "mechanism_handoff": "RESEARCH_OPERATIONS_ONLY",
        "authority": _authority(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "constraint_evidence_id": "cei-evidence-v1:" + logical_hash, "logical_hash": logical_hash}


def render_condition(condition: Mapping[str, Any], *, as_precondition: bool = False) -> str:
    role = str(condition.get("temporal_role") or "")
    name = _require(condition.get("name"), "CEI_CONDITION_NAME_REQUIRED")
    if as_precondition and role not in {"PRE_EXISTING", "AT_ANCHOR"}:
        raise CEIError("CEI_RETROSPECTIVE_PRECONDITION_RENDER_FORBIDDEN")
    prefix = "pre-existing" if role == "PRE_EXISTING" else "at-anchor" if role == "AT_ANCHOR" else role.lower()
    text = f"{prefix} condition: {name}"
    _scan_forbidden(text)
    return text
