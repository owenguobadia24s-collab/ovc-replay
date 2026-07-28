from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

COMPARISON_CLASSES = {
    "IDENTICAL_DEFINITION",
    "CONTRACT_CHANGED",
    "FORMULA_CHANGED",
    "DOMAIN_CHANGED",
    "NULL_POLICY_CHANGED",
    "CHRONOLOGY_CHANGED",
    "SYMMETRY_CHANGED",
    "SERIALIZATION_CHANGED",
    "POPULATION_CHANGED",
    "OUTPUT_CHANGED",
    "NOT_COMPARABLE",
}
FORBIDDEN_AUTHORITY_VOCABULARY = {
    "RECOMMENDED_WINNER", "APPROVED", "PROMOTE", "PROMOTED",
    "ACTIVATE", "ACTIVATED", "PREFERRED_VERSION",
}
_ALLOWED_MODES = {"FORMULA_DEFINITION", "RELEASE_OUTPUT", "ROLE_CONTRAST"}


class ComparisonContractError(ValueError):
    """Raised when a non-activating comparison violates its frozen contract."""


class AcknowledgementRequired(ComparisonContractError):
    """Raised when a detailed comparison lacks a valid acknowledgement."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ComparisonContractError(f"{field} must be a non-empty timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ComparisonContractError(f"invalid {field}") from exc
    if parsed.tzinfo is None:
        raise ComparisonContractError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def _contains_forbidden_authority_language(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key).upper()
            if token in FORBIDDEN_AUTHORITY_VOCABULARY:
                return token
            found = _contains_forbidden_authority_language(item)
            if found:
                return found
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            found = _contains_forbidden_authority_language(item)
            if found:
                return found
    elif isinstance(value, str):
        upper = value.upper()
        for token in FORBIDDEN_AUTHORITY_VOCABULARY:
            if token in upper:
                return token
    return None


def _comparison_identity(
    base: Mapping[str, Any], candidate: Mapping[str, Any], context: Mapping[str, Any]
) -> tuple[str, str, str]:
    base_hash = _digest(base)
    candidate_hash = _digest(candidate)
    logical = {
        "base_sha256": base_hash,
        "candidate_sha256": candidate_hash,
        "context": dict(context),
    }
    return f"ro3-c1-comparison:{_digest(logical)}", base_hash, candidate_hash


def comparison_preflight(
    base: Mapping[str, Any],
    candidate: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    mode = str(context.get("comparison_mode", ""))
    if mode not in _ALLOWED_MODES:
        raise ComparisonContractError(f"unknown comparison_mode: {mode or 'MISSING'}")
    if (
        context.get("role") == "VALIDATION"
        or context.get("base_role") == "VALIDATION"
        or context.get("candidate_role") == "VALIDATION"
    ):
        raise ComparisonContractError("VALIDATION_DENY_BEFORE_CONTENT_RESOLUTION")

    reasons: list[str] = []
    comparable = True
    if mode == "FORMULA_DEFINITION":
        if base.get("primitive_id") != candidate.get("primitive_id"):
            comparable = False
            reasons.append("PRIMITIVE_ID_MISMATCH")
        if base.get("unit") != candidate.get("unit"):
            reasons.append("UNIT_DOMAIN_CHANGED")
    elif mode == "RELEASE_OUTPUT":
        for field in ("instrument", "role", "clock", "side"):
            if context.get(f"base_{field}") != context.get(f"candidate_{field}"):
                comparable = False
                reasons.append(f"{field.upper()}_MISMATCH")
        if context.get("base_population_sha256") != context.get("candidate_population_sha256"):
            reasons.append("POPULATION_CHANGED")
    else:
        if context.get("base_role") == context.get("candidate_role"):
            comparable = False
            reasons.append("ROLE_CONTRAST_REQUIRES_DISTINCT_ROLES")
        if {context.get("base_role"), context.get("candidate_role")} - {"DISCOVERY", "DEVELOPMENT"}:
            comparable = False
            reasons.append("ROLE_CONTRAST_ROLE_NOT_ALLOWED")

    comparison_id, base_hash, candidate_hash = _comparison_identity(base, candidate, context)
    return {
        "schema": "ovc-ro3-comparison-preflight/v1",
        "comparison_id": comparison_id,
        "comparison_mode": mode,
        "base_sha256": base_hash,
        "candidate_sha256": candidate_hash,
        "status": "COMPARABLE" if comparable else "NOT_COMPARABLE",
        "reasons": sorted(set(reasons)),
        "writes": "NONE",
    }


def build_non_activating_evidence_header(preflight: Mapping[str, Any]) -> dict[str, Any]:
    comparison_id = str(preflight.get("comparison_id", ""))
    if not comparison_id.startswith("ro3-c1-comparison:"):
        raise ComparisonContractError("invalid comparison identity")
    header = {
        "schema": "ovc-ro3-non-activating-evidence-header/v1",
        "comparison_id": comparison_id,
        "evidence_class": "NON_ACTIVATING_EVIDENCE",
        "authority_effect": "NONE",
        "statement": "This comparison is read-only evidence. It cannot select a winner, approve, promote or activate a formula, release, selector or threshold.",
        "detailed_diff_access": "ACKNOWLEDGEMENT_REQUIRED",
        "prohibited_effects": [
            "FORMULA_MUTATION",
            "RELEASE_REBUILD_OR_SELECTION",
            "SELECTOR_OR_THRESHOLD_CHANGE",
            "SEMANTIC_OR_MODEL_PROMOTION",
            "VALIDATION_CONSUMPTION",
            "PROBABILITY_RISK_EXPOSURE_EXECUTION",
        ],
    }
    return {**header, "header_id": f"ro3-non-activating-header:{_digest(header)}"}


def create_comparison_acknowledgement(
    comparison_id: str,
    operator_id: str,
    acknowledged_at: str,
    expires_at: str,
) -> dict[str, Any]:
    if not comparison_id.startswith("ro3-c1-comparison:"):
        raise ComparisonContractError("invalid comparison identity")
    if not operator_id.strip():
        raise ComparisonContractError("operator identity is required")
    acknowledged = _parse_time(acknowledged_at, "acknowledged_at")
    expires = _parse_time(expires_at, "expires_at")
    if expires <= acknowledged:
        raise ComparisonContractError("acknowledgement expiry must follow acknowledgement time")
    record = {
        "schema": "ovc-ro3-comparison-acknowledgement/v1",
        "comparison_id": comparison_id,
        "operator_id": operator_id,
        "acknowledged_at": acknowledged_at,
        "expires_at": expires_at,
        "acknowledged_statement": "I understand that this detailed comparison is non-activating evidence and is not approval of any formula, release, selector or threshold change.",
        "record_state": "FROZEN_APPEND_ONLY",
        "authority_effect": "NONE",
        "supersedes": None,
    }
    return {**record, "acknowledgement_id": f"ro3-comparison-ack:{_digest(record)}"}


def validate_comparison_acknowledgement(
    acknowledgement: Mapping[str, Any] | None,
    comparison_id: str,
    operator_id: str,
    now: str,
) -> None:
    if acknowledgement is None:
        raise AcknowledgementRequired("DETAILED_DIFF_DENIED_ACKNOWLEDGEMENT_REQUIRED")
    if acknowledgement.get("comparison_id") != comparison_id:
        raise AcknowledgementRequired("DETAILED_DIFF_DENIED_ACKNOWLEDGEMENT_MISMATCH")
    if acknowledgement.get("operator_id") != operator_id or not operator_id:
        raise AcknowledgementRequired("DETAILED_DIFF_DENIED_OPERATOR_IDENTITY_MISMATCH")
    if acknowledgement.get("record_state") != "FROZEN_APPEND_ONLY" or acknowledgement.get("authority_effect") != "NONE":
        raise AcknowledgementRequired("DETAILED_DIFF_DENIED_ACKNOWLEDGEMENT_NOT_FROZEN")
    if not str(acknowledgement.get("acknowledgement_id", "")).startswith("ro3-comparison-ack:"):
        raise AcknowledgementRequired("DETAILED_DIFF_DENIED_ACKNOWLEDGEMENT_ID_INVALID")
    if _parse_time(now, "now") >= _parse_time(acknowledgement.get("expires_at"), "expires_at"):
        raise AcknowledgementRequired("DETAILED_DIFF_DENIED_ACKNOWLEDGEMENT_EXPIRED")


def _definition_classes(
    base: Mapping[str, Any], candidate: Mapping[str, Any], context: Mapping[str, Any]
) -> list[str]:
    classes: set[str] = set()
    if (
        base == candidate
        and not context.get("contract_changed")
        and not context.get("schema_changed")
        and not context.get("population_changed")
        and not context.get("output_changed")
    ):
        return ["IDENTICAL_DEFINITION"]
    if base.get("formula") != candidate.get("formula") or base.get("required_inputs") != candidate.get("required_inputs"):
        classes.add("FORMULA_CHANGED")
    if base.get("unit") != candidate.get("unit") or base.get("domain") != candidate.get("domain"):
        classes.add("DOMAIN_CHANGED")
    if base.get("null_rule") != candidate.get("null_rule"):
        classes.add("NULL_POLICY_CHANGED")
    if base.get("lookback_bars") != candidate.get("lookback_bars") or base.get("first_valid_rule") != candidate.get("first_valid_rule"):
        classes.add("CHRONOLOGY_CHANGED")
    if base.get("symmetry_rule") != candidate.get("symmetry_rule"):
        classes.add("SYMMETRY_CHANGED")
    if context.get("contract_changed") or context.get("schema_changed"):
        classes.add("CONTRACT_CHANGED")
    if context.get("serialization_changed"):
        classes.add("SERIALIZATION_CHANGED")
    if (
        context.get("comparison_mode") == "RELEASE_OUTPUT"
        and (
            context.get("population_changed")
            or context.get("base_population_sha256") != context.get("candidate_population_sha256")
        )
    ):
        classes.add("POPULATION_CHANGED")
    if context.get("output_changed"):
        classes.add("OUTPUT_CHANGED")
    return sorted(classes or {"NOT_COMPARABLE"})


def compare_formula_versions(
    base: Mapping[str, Any],
    candidate: Mapping[str, Any],
    context: Mapping[str, Any],
    acknowledgement: Mapping[str, Any] | None,
    operator_id: str,
    now: str,
) -> dict[str, Any]:
    preflight = comparison_preflight(base, candidate, context)
    header = build_non_activating_evidence_header(preflight)
    validate_comparison_acknowledgement(acknowledgement, preflight["comparison_id"], operator_id, now)
    classes = ["NOT_COMPARABLE"] if preflight["status"] != "COMPARABLE" else _definition_classes(base, candidate, context)
    changes = {
        key: {"base": base.get(key), "candidate": candidate.get(key)}
        for key in sorted(set(base) | set(candidate))
        if base.get(key) != candidate.get(key)
    }
    result = {
        "non_activating_evidence_header": header,
        "schema": "ovc-ro3-c1-formula-version-diff/v1",
        "comparison_id": preflight["comparison_id"],
        "comparison_mode": preflight["comparison_mode"],
        "preflight_status": preflight["status"],
        "classification": classes,
        "base_sha256": preflight["base_sha256"],
        "candidate_sha256": preflight["candidate_sha256"],
        "acknowledgement_id": acknowledgement.get("acknowledgement_id") if acknowledgement else None,
        "changes": changes,
        "winner": None,
        "authority_effect": "NONE",
        "writes": "NONE",
    }
    forbidden = _contains_forbidden_authority_language({"classification": classes, "changes": changes})
    if forbidden:
        raise ComparisonContractError(f"comparison output contains forbidden authority vocabulary: {forbidden}")
    result["comparison_output_id"] = f"ro3-c1-formula-diff:{_digest(result)}"
    return result


def compare_release_outputs(
    base_rows: Iterable[Mapping[str, Any]],
    candidate_rows: Iterable[Mapping[str, Any]],
    context: Mapping[str, Any],
    acknowledgement: Mapping[str, Any] | None,
    operator_id: str,
    now: str,
) -> dict[str, Any]:
    base = sorted((dict(row) for row in base_rows), key=lambda row: str(row.get("record_id", "")))
    candidate = sorted((dict(row) for row in candidate_rows), key=lambda row: str(row.get("record_id", "")))
    preflight = comparison_preflight({"rows": base}, {"rows": candidate}, context)
    header = build_non_activating_evidence_header(preflight)
    validate_comparison_acknowledgement(acknowledgement, preflight["comparison_id"], operator_id, now)
    base_by_id = {str(row.get("record_id")): row for row in base}
    candidate_by_id = {str(row.get("record_id")): row for row in candidate}
    shared = sorted(set(base_by_id) & set(candidate_by_id))
    changed = [record_id for record_id in shared if base_by_id[record_id] != candidate_by_id[record_id]]
    classes: list[str] = []
    if "POPULATION_CHANGED" in preflight["reasons"] or set(base_by_id) != set(candidate_by_id):
        classes.append("POPULATION_CHANGED")
    if changed:
        classes.append("OUTPUT_CHANGED")
    if not classes:
        classes.append("IDENTICAL_DEFINITION")
    result = {
        "non_activating_evidence_header": header,
        "schema": "ovc-ro3-c1-release-output-diff/v1",
        "comparison_id": preflight["comparison_id"],
        "comparison_mode": preflight["comparison_mode"],
        "classification": sorted(classes),
        "base_record_count": len(base),
        "candidate_record_count": len(candidate),
        "shared_record_count": len(shared),
        "changed_record_ids": changed,
        "base_only_record_ids": sorted(set(base_by_id) - set(candidate_by_id)),
        "candidate_only_record_ids": sorted(set(candidate_by_id) - set(base_by_id)),
        "acknowledgement_id": acknowledgement.get("acknowledgement_id") if acknowledgement else None,
        "winner": None,
        "authority_effect": "NONE",
        "writes": "NONE",
    }
    result["comparison_output_id"] = f"ro3-c1-release-diff:{_digest(result)}"
    return result


def build_affected_surface_report(
    comparison_id: str,
    child_references: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = sorted(
        (dict(row) for row in child_references),
        key=lambda row: (str(row.get("surface_type", "")), str(row.get("child_id", ""))),
    )
    for row in rows:
        if set(row) - {
            "surface_type", "child_id", "source_binding", "consequence",
            "availability", "operation_mode",
        }:
            raise ComparisonContractError("affected-surface report may contain compact trace metadata only")
        if row.get("surface_type") not in {"C2_CHILD", "PATTERN_DISCOVERY_TRACE"}:
            raise ComparisonContractError("unknown affected-surface type")
    result = {
        "schema": "ovc-ro3-c1-affected-surface/v1",
        "comparison_id": comparison_id,
        "presentation": "SEPARATE_BANNERED_TRACE_ONLY",
        "banner": "C2 and Pattern Discovery authority are unchanged; affected surfaces are read-only trace only.",
        "co_render_with_c1_null_explanation": False,
        "references": rows,
        "reference_count": len(rows),
        "authority_effect": "NONE",
        "writes": "NONE",
    }
    return {**result, "affected_surface_id": f"ro3-c1-affected-surface:{_digest(result)}"}
