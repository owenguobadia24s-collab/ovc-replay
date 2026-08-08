from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .builder import OccurrenceContextError
from .serialization import canonical_json

ALLOWED_KINDS = {
    "ACTIVITY_LIQUIDITY",
    "INTRINSIC_EVENT_TIME",
    "VOLATILITY_STATE",
    "PROVIDER_SOURCE_CHARACTERISTIC",
}
FORBIDDEN_VECTOR_KEYS = {
    "vector",
    "vectors",
    "embedding",
    "embeddings",
    "features",
    "feature_vector",
    "normalized_features",
    "normalised_features",
}
_REQUIRED = {
    "kind",
    "record_id",
    "record_schema_id",
    "record_logical_hash",
    "candidate_or_pack_id",
    "candidate_or_pack_version",
    "first_valid_time",
    "availability_status",
    "qualification_record_id",
    "qualification_status",
}


def _walk_forbidden(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_VECTOR_KEYS:
                raise OccurrenceContextError("OC_MCARB_NOT_ADMITTED", f"mutable/vector payload forbidden: {key}")
            _walk_forbidden(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _walk_forbidden(child)


def _find_admission(registry: Mapping[str, Any], payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for admission in registry.get("admissions", []):
        if (
            admission.get("kind") == payload.get("kind")
            and admission.get("candidate_or_pack_id") == payload.get("candidate_or_pack_id")
            and admission.get("candidate_or_pack_version") == payload.get("candidate_or_pack_version")
            and admission.get("record_schema_id") == payload.get("record_schema_id")
        ):
            return admission
    return None


def build_mcarb_context_ref(
    payload: Mapping[str, Any],
    admission_registry: Mapping[str, Any],
    *,
    fixture_only: bool = False,
) -> dict[str, Any]:
    data = deepcopy(dict(payload))
    missing = sorted(field for field in _REQUIRED if data.get(field) in (None, ""))
    if missing:
        raise OccurrenceContextError("OC_MCARB_REF_UNAVAILABLE", ",".join(missing))
    if data["kind"] not in ALLOWED_KINDS:
        raise OccurrenceContextError("OC_MCARB_NOT_ADMITTED", "unknown auxiliary kind")
    _walk_forbidden(data)
    admission = _find_admission(admission_registry, data)
    if fixture_only:
        allowed_fixture = set(admission_registry.get("fixture_only_categories", []))
        if data["kind"] not in allowed_fixture:
            raise OccurrenceContextError("OC_MCARB_NOT_ADMITTED", "fixture category not registered")
        admission_id = "OC.AUXILIARY.FIXTURE_ONLY.v0.1"
    else:
        if admission_registry.get("status") == "NO_SCIENTIFIC_ADMISSIONS" or admission is None:
            raise OccurrenceContextError("OC_MCARB_NOT_ADMITTED")
        if admission.get("authority_effect", "NONE") != "NONE":
            raise OccurrenceContextError("OC_MCARB_NOT_ADMITTED", "activating admission forbidden")
        admission_id = str(admission["context_admission_id"])
    descriptor = data.get("compact_descriptor")
    if descriptor is not None:
        if not isinstance(descriptor, Mapping):
            raise OccurrenceContextError("OC_MCARB_NOT_ADMITTED", "compact descriptor must be a mapping")
        _walk_forbidden(descriptor)
        # v0.1 has no production descriptor allowlist; fixture descriptors are scalar display-only values.
        if not fixture_only:
            allowed = set(admission.get("compact_descriptor_allowlist", [])) if admission else set()
            if set(descriptor) - allowed:
                raise OccurrenceContextError("OC_MCARB_NOT_ADMITTED", "descriptor field not allowlisted")
        elif any(isinstance(value, (dict, list, tuple)) for value in descriptor.values()):
            raise OccurrenceContextError("OC_MCARB_NOT_ADMITTED", "fixture descriptor must be compact scalars")
    result = {
        "kind": str(data["kind"]),
        "record_id": str(data["record_id"]),
        "record_schema_id": str(data["record_schema_id"]),
        "record_logical_hash": str(data["record_logical_hash"]),
        "domain_id": data.get("domain_id"),
        "candidate_or_pack_id": str(data["candidate_or_pack_id"]),
        "candidate_or_pack_version": str(data["candidate_or_pack_version"]),
        "source_release_id": data.get("source_release_id"),
        "source_record_ids": sorted(set(str(item) for item in data.get("source_record_ids", []))),
        "first_valid_time": str(data["first_valid_time"]),
        "availability_status": str(data["availability_status"]),
        "qualification_record_id": str(data["qualification_record_id"]),
        "qualification_status": str(data["qualification_status"]),
        "context_admission_id": admission_id,
        "compact_descriptor": deepcopy(dict(descriptor)) if descriptor is not None else None,
        "authority_effect": "NONE",
    }
    canonical_json(result)
    return result
