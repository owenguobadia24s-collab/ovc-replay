from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from ovc.research_operations.canonical import canonical_json_bytes


PROFILE_ID = "P1CDI-SEMANTIC-PROJECTION-v1"
IDENTITY_FIELDS = frozenset(
    {
        "unit_type",
        "structural_predicates",
        "structural_relations",
        "complete_minimal_core_set",
        "applicability_scope",
        "identity_defining_dependencies",
        "first_valid_semantics",
        "missingness_semantics",
        "representation_dependency",
        "method_dependency",
        "boundary_dependency",
    }
)
EVIDENCE_ONLY_FIELDS = frozenset(
    {
        "recurrence_count",
        "qa_state",
        "evidence_maturity",
        "worker",
        "path",
        "branch",
        "pull_request",
        "run_attempt",
        "cache",
        "integration_provenance",
    }
)


def _copy_json_value(value: Any, path: str = "identity_fields") -> Any:
    if isinstance(value, Mapping):
        copied: dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            if name in EVIDENCE_ONLY_FIELDS:
                raise ValueError(f"evidence/provenance cannot enter semantic identity: {path}.{name}")
            copied[name] = _copy_json_value(item, f"{path}.{name}")
        return copied
    if isinstance(value, list):
        return [_copy_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"semantic projection contains a non-JSON value: {type(value).__name__}")


def _identity_payload(*, owner_semantic_binding: str, identity_fields: Mapping[str, Any]) -> dict[str, Any]:
    if not owner_semantic_binding:
        raise ValueError("owner_semantic_binding must be non-empty")
    observed = set(identity_fields)
    if observed != IDENTITY_FIELDS:
        missing = sorted(IDENTITY_FIELDS - observed)
        extra = sorted(observed - IDENTITY_FIELDS)
        raise ValueError(f"identity field contract mismatch; missing={missing}, extra={extra}")
    return {
        "profile_id": PROFILE_ID,
        "owner_semantic_binding": owner_semantic_binding,
        "identity_fields": _copy_json_value(identity_fields),
    }


def projection_bytes(projection: Mapping[str, Any]) -> bytes:
    if projection.get("profile_id") != PROFILE_ID:
        raise ValueError("semantic projection profile is not compatible with v1")
    payload = _identity_payload(
        owner_semantic_binding=str(projection.get("owner_semantic_binding", "")),
        identity_fields=projection.get("identity_fields", {}),
    )
    return canonical_json_bytes(payload, trailing_newline=False)


def build_semantic_projection(
    *, generation_id: str, owner_semantic_binding: str, identity_fields: Mapping[str, Any]
) -> dict[str, Any]:
    if not generation_id:
        raise ValueError("generation_id must be non-empty")
    payload = _identity_payload(
        owner_semantic_binding=owner_semantic_binding,
        identity_fields=identity_fields,
    )
    digest = hashlib.sha256(canonical_json_bytes(payload, trailing_newline=False)).hexdigest()
    return {
        "record_type": "P1DistinctionSemanticProjection",
        "schema_version": "0.1",
        "authority_effect": "NONE",
        "generation_id": generation_id,
        **payload,
        "projection_sha256": digest,
    }


def exact_semantic_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    """Return true only for exact canonical bytes under the compatible v1 profile."""

    try:
        left_bytes = projection_bytes(left)
        right_bytes = projection_bytes(right)
    except ValueError:
        return False
    left_digest = hashlib.sha256(left_bytes).hexdigest()
    right_digest = hashlib.sha256(right_bytes).hexdigest()
    return (
        left_digest == right_digest
        and left.get("projection_sha256") == left_digest
        and right.get("projection_sha256") == right_digest
        and left_bytes == right_bytes
    )
