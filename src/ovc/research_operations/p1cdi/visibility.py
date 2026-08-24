from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

VISIBILITY_CLASSES = (
    "PATH1_FULL",
    "PATH1_SAFE",
    "CROSS_MODE_POST_FREEZE",
    "OPERATOR_RESTRICTED",
    "PROTECTED",
)
LEAK_SURFACES = (
    "FIELDS",
    "TITLES",
    "IDS",
    "COUNTS",
    "AGGREGATES",
    "GRAPH_NEIGHBOURS",
    "DEMAND_TEXT",
    "CANDIDATE_COUNTS",
    "SEARCH_SUGGESTIONS",
    "CACHE_METADATA",
    "ERRORS",
    "PATHS",
)
PATH1_SAFE_REDACTED_FIELDS = (
    "path2_candidate_predicate",
    "path2_candidate_example",
    "path2_candidate_falsifier",
    "path2_parameter_boundary",
    "restricted_neighbourhood",
)
INDEPENDENCE_CLASSES = (
    "INDEPENDENCE_SUPPORTED",
    "DEPENDENCE_SUPPORTED",
    "INDEPENDENCE_UNKNOWN",
)


def _exact_string(value: Any, name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _refs(value: Sequence[str], name: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a sequence")
    rows = [_exact_string(item, name) for item in value]
    if len(rows) != len(set(rows)):
        raise ValueError(f"{name} must not contain duplicates")
    return sorted(rows)


def _surface_list(value: Sequence[str]) -> list[str]:
    rows = _refs(value, "denied_surfaces")
    unknown = sorted(set(rows).difference(LEAK_SURFACES))
    if unknown:
        raise ValueError(f"unknown leak surfaces: {unknown}")
    return sorted(rows)


def _record_id(prefix: str, body: Mapping[str, Any]) -> str:
    return f"p1:{prefix}:{canonical_sha256(body)}"


def build_visibility_decision(
    *,
    source_ref: str,
    classification: str | None,
    classification_complete: bool,
    permission_refs: Sequence[str] = (),
    redacted_fields: Sequence[str] = (),
    denied_surfaces: Sequence[str] = (),
    cross_mode_freeze_ref: str | None = None,
) -> dict[str, Any]:
    """Build a fail-closed visibility decision before any indexing or aggregation.

    Unknown/incomplete visibility, missing PATH1_FULL eligibility, and an unproven
    cross-mode freeze all collapse to PROTECTED.  This is a read-side decision only;
    it cannot admit a source or alter any scientific/candidate authority.
    """

    source = _exact_string(source_ref, "source_ref")
    permissions = _refs(permission_refs, "permission_refs")
    redactions = _refs(redacted_fields, "redacted_fields")
    denied = _surface_list(denied_surfaces)

    requested = classification if classification_complete else "PROTECTED"
    if requested is None:
        requested = "PROTECTED"
    requested = _exact_string(requested, "classification")
    if requested not in VISIBILITY_CLASSES:
        requested = "PROTECTED"

    resolved = requested
    if resolved == "PATH1_FULL" and not permissions:
        resolved = "PROTECTED"
    if resolved == "CROSS_MODE_POST_FREEZE":
        if not cross_mode_freeze_ref or not permissions:
            resolved = "PROTECTED"
        else:
            permissions = sorted(set(permissions + [_exact_string(cross_mode_freeze_ref, "cross_mode_freeze_ref")]))

    if resolved == "PATH1_SAFE":
        redactions = sorted(set(redactions).union(PATH1_SAFE_REDACTED_FIELDS))
    if resolved in {"OPERATOR_RESTRICTED", "PROTECTED"}:
        denied = sorted(LEAK_SURFACES)

    body = {
        "source_ref": source,
        "classification": resolved,
        "classified_before_indexing": True,
        "permission_refs": permissions,
        "redacted_fields": redactions,
        "denied_surfaces": denied,
        "validation_access": "DENIED",
        "authority_effect": "NONE",
    }
    return {
        "record_type": "P1CDIVisibilityDecision",
        "schema_version": "0.1",
        "decision_id": _record_id("visibility", body),
        **body,
    }


def validate_visibility_decision(decision: Mapping[str, Any]) -> None:
    if decision.get("record_type") != "P1CDIVisibilityDecision":
        raise ValueError("P1CDIVisibilityDecision is required")
    if decision.get("schema_version") != "0.1":
        raise ValueError("visibility schema version mismatch")
    classification = decision.get("classification")
    if classification not in VISIBILITY_CLASSES:
        raise ValueError("visibility classification outside frozen registry")
    if decision.get("classified_before_indexing") is not True:
        raise PermissionError("visibility must be classified before indexing")
    if decision.get("validation_access") != "DENIED":
        raise PermissionError("Validation access is hard denied")
    if decision.get("authority_effect") != "NONE":
        raise PermissionError("visibility decisions may not carry authority")
    _refs(decision.get("permission_refs", ()), "permission_refs")
    _refs(decision.get("redacted_fields", ()), "redacted_fields")
    denied = _surface_list(decision.get("denied_surfaces", ()))
    if classification in {"OPERATOR_RESTRICTED", "PROTECTED"} and set(denied) != set(LEAK_SURFACES):
        raise PermissionError("restricted visibility must deny every leak surface")


def _permission_allows(decision: Mapping[str, Any], caller_permission_refs: Sequence[str]) -> bool:
    classification = str(decision["classification"])
    required = set(_refs(decision.get("permission_refs", ()), "permission_refs"))
    caller = set(_refs(caller_permission_refs, "caller_permission_refs"))
    if classification == "PATH1_SAFE":
        return True
    if classification in {"OPERATOR_RESTRICTED", "PROTECTED"}:
        return False
    return bool(required.intersection(caller))


def project_visible_record(
    *,
    decision: Mapping[str, Any],
    record: Mapping[str, Any],
    surface: str,
    caller_permission_refs: Sequence[str] = (),
) -> dict[str, Any]:
    """Return only a visibility-safe projection for one named leak surface.

    Denial deliberately omits source identity, title, counts, paths and reason text so
    the denial itself cannot become an oracle for protected membership.
    """

    validate_visibility_decision(decision)
    requested_surface = _exact_string(surface, "surface")
    if requested_surface not in LEAK_SURFACES:
        raise ValueError("surface outside frozen leak-surface registry")

    denied = set(decision.get("denied_surfaces", ()))
    if requested_surface in denied or not _permission_allows(decision, caller_permission_refs):
        return {
            "visibility": "DENIED",
            "surface": requested_surface,
            "authority_effect": "NONE",
        }

    projected = dict(record)
    for field in decision.get("redacted_fields", ()):
        projected.pop(str(field), None)
    projected.pop("validation_payload", None)
    projected.pop("validation_path", None)
    return {
        "visibility": "VISIBLE",
        "surface": requested_surface,
        "record": projected,
        "authority_effect": "NONE",
    }


def build_visibility_safe_index_entry(
    *,
    decision: Mapping[str, Any],
    record: Mapping[str, Any],
    caller_permission_refs: Sequence[str] = (),
) -> dict[str, Any] | None:
    """Materialise no searchable entry until visibility has already been enforced."""

    projected = project_visible_record(
        decision=decision,
        record=record,
        surface="SEARCH_SUGGESTIONS",
        caller_permission_refs=caller_permission_refs,
    )
    if projected["visibility"] != "VISIBLE":
        return None
    safe_record = projected["record"]
    body = {
        "visibility_decision_id": _exact_string(decision.get("decision_id"), "decision_id"),
        "record": safe_record,
    }
    return {
        "record_type": "P1CDIVisibilitySafeIndexEntry",
        "schema_version": "0.1",
        "entry_id": _record_id("visibility-safe-index", body),
        **body,
        "classified_before_indexing": True,
        "authority_effect": "NONE",
    }


def deny_validation_before_resolution(
    *,
    decision: Mapping[str, Any],
    sensitive_resolver: Callable[[], Any] | None = None,
) -> None:
    """Fail before invoking a resolver that could expose protected Validation data."""

    validate_visibility_decision(decision)
    # The resolver argument exists only so tests can prove it is never invoked.
    _ = sensitive_resolver
    raise PermissionError("VALIDATION_NEGATIVE_REACHABILITY_DENIED_BEFORE_RESOLUTION")


def project_independence_state(
    *,
    exposure_refs: Sequence[str] = (),
    owner_independence_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Absence of exposure evidence never upgrades to independence."""

    exposures = _refs(exposure_refs, "exposure_refs")
    result = "INDEPENDENCE_UNKNOWN"
    owner_ref: str | None = None
    if owner_independence_evidence is not None:
        owner_result = owner_independence_evidence.get("result")
        owner_ref = _exact_string(owner_independence_evidence.get("record_id"), "owner_independence_evidence.record_id")
        if owner_result not in INDEPENDENCE_CLASSES:
            raise ValueError("owner independence evidence outside supported projection vocabulary")
        result = str(owner_result)
    body = {
        "exposure_refs": exposures,
        "owner_evidence_ref": owner_ref,
        "result": result,
    }
    return {
        "record_type": "P1CDIIndependenceProjection",
        "schema_version": "0.1",
        "record_id": _record_id("independence-projection", body),
        **body,
        "authority_effect": "NONE",
    }
