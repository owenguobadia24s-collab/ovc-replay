from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from ovc.research_operations.canonical import canonical_json_bytes, canonical_sha256

from .identity import (
    PROFILE_ID,
    build_semantic_projection,
    exact_semantic_equal,
    projection_bytes,
)
from .series_root_guard import validate_correspondence_series_root


_RULE_PROFILE_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p1cdi/reference_rule_profile_v1.json"
)
_RELATION_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p1cdi/relation_registry.json"
)
_EVIDENCE_PLANE_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p1cdi/reference_evidence_plane_registry_v1.json"
)
_VECTOR_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "record_id",
        "generation_id",
        "source_refs",
        "denominator",
        "recurrence",
        "dependence",
        "separation",
        "integrity",
        "other_planes",
        "authority_effect",
    }
)
_CORRESPONDENCE_PLANES = frozenset(
    {
        "semantic_relation",
        "core_relation",
        "occurrence_relation",
        "envelope_relation",
        "lineage_relation",
        "independence_state",
    }
)
_HISTORY_FIELDS = frozenset(
    {"record_id", "logical_id", "first_valid_time", "correction_of", "payload", "source_refs"}
)
_SERIES_FIELDS = frozenset(
    {"record_type", "schema_version", "authority_effect", "series_id", "first_generation_id", "predecessor_series_refs"}
)
_GENERATION_FIELDS = frozenset(
    {"record_type", "schema_version", "authority_effect", "generation_id", "series_id", "profile_id", "projection_sha256", "source_first_valid_time", "immutable"}
)
_PROJECTION_FIELDS = frozenset(
    {"record_type", "schema_version", "authority_effect", "generation_id", "profile_id", "owner_semantic_binding", "identity_fields", "projection_sha256"}
)
_DMRP_INDEPENDENCE_FIELDS = frozenset(
    {
        "record_id",
        "owner",
        "left_generation_id",
        "right_generation_id",
        "source_ref",
        "source_generation",
        "source_sha256",
        "current_source_ref",
        "current_source_generation",
        "current_source_sha256",
        "evidence_first_valid_time",
        "currentness_state",
        "independence_state",
        "authority_effect",
    }
)
_PLANE_EVIDENCE_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "record_id",
        "owner",
        "plane",
        "value",
        "left_generation_id",
        "right_generation_id",
        "source_ref",
        "source_generation",
        "source_content",
        "source_sha256",
        "current_source_ref",
        "current_source_generation",
        "current_source_sha256",
        "evidence_first_valid_time",
        "currentness_state",
        "authority_effect",
    }
)
_NON_SEMANTIC_SOURCE_PLANES = frozenset(
    {"core_relation", "occurrence_relation", "envelope_relation", "lineage_relation"}
)
_PRESERVED_RECORD_FIELDS = {
    "replications": frozenset(
        {"record_type", "schema_version", "record_id", "generation_id", "source_refs", "replication_kind", "outcome", "authority_effect"}
    ),
    "null_bindings": frozenset(
        {"record_type", "schema_version", "record_id", "generation_id", "source_refs", "null_class", "authority_effect"}
    ),
    "contradictions": frozenset(
        {"record_type", "schema_version", "record_id", "generation_id", "source_refs", "contradiction_type", "authority_effect"}
    ),
}


class ReferenceEngineError(ValueError):
    """The deterministic reference oracle cannot produce an exact answer."""


def _load_rule_profile() -> dict[str, Any]:
    profile = json.loads(_RULE_PROFILE_PATH.read_text(encoding="utf-8"))
    if profile.get("profile_id") != "P1CDI-REFERENCE-RULE-PROFILE-v1":
        raise RuntimeError("P1CDI reference rule profile identity mismatch")
    if profile.get("status") != "CLOSED" or profile.get("authority_effect") != "NONE":
        raise RuntimeError("P1CDI reference rule profile must be closed and non-authorising")
    if profile.get("identity", {}).get("fuzzy_merge") != "FORBIDDEN":
        raise RuntimeError("P1CDI reference rule profile must forbid fuzzy merge")
    if profile.get("evidence_vector", {}).get("scalar_score") != "FORBIDDEN":
        raise RuntimeError("P1CDI reference rule profile must forbid scalar evidence scores")
    return profile


RULE_PROFILE = _load_rule_profile()
RULE_PROFILE_ID = RULE_PROFILE["profile_id"]
RELATION_REGISTRY = json.loads(_RELATION_REGISTRY_PATH.read_text(encoding="utf-8"))
if RELATION_REGISTRY.get("status") != "CLOSED":
    raise RuntimeError("P1CDI relation registry must be closed")
EVIDENCE_PLANE_REGISTRY = json.loads(
    _EVIDENCE_PLANE_REGISTRY_PATH.read_text(encoding="utf-8")
)
if (
    EVIDENCE_PLANE_REGISTRY.get("status") != "CLOSED"
    or EVIDENCE_PLANE_REGISTRY.get("authority_effect") != "NONE"
):
    raise RuntimeError("P1CDI evidence-plane registry must be closed and non-authorising")

CONFORMANCE_SEPARATION_PRINCIPLE = (
    "SEMANTIC_EQUALITY",
    "CANONICAL_OBJECT_VALIDITY",
    "SOURCE_EVIDENCE_VALIDITY",
    "NON_SEMANTIC_PLANE_TRUTH",
    "SERIES_HISTORY_VALIDITY",
    "SCIENTIFIC_SUPPORT",
    "INDEPENDENCE",
)


def _require_string(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise ReferenceEngineError(f"{field} must be a non-empty string")
    return value


def _parse_time(value: object, field: str) -> datetime:
    text = _require_string(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReferenceEngineError(f"{field} must be an ISO date-time") from exc
    if parsed.tzinfo is None:
        raise ReferenceEngineError(f"{field} must include a timezone")
    return parsed


def _canonical_bytes(value: object) -> bytes:
    try:
        return canonical_json_bytes(value, trailing_newline=False)
    except (TypeError, ValueError) as exc:
        raise ReferenceEngineError("record content is not canonical JSON") from exc


def _validate_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or set(record) != _PROJECTION_FIELDS:
        raise ReferenceEngineError("semantic projection must use the exact closed canonical field set")
    if record.get("record_type") != "P1DistinctionSemanticProjection":
        raise ReferenceEngineError("semantic projection record type is invalid")
    if record.get("schema_version") != "0.1" or record.get("authority_effect") != "NONE":
        raise ReferenceEngineError("semantic projection schema or authority is invalid")
    if record.get("profile_id") != PROFILE_ID:
        raise ReferenceEngineError("semantic projection profile is invalid")
    generation_id = _require_string(record.get("generation_id"), "generation_id")
    try:
        rebuilt = build_semantic_projection(
            generation_id=generation_id,
            owner_semantic_binding=record.get("owner_semantic_binding"),
            identity_fields=record.get("identity_fields", {}),
        )
    except ValueError as exc:
        raise ReferenceEngineError("semantic projection cannot be canonically rebuilt") from exc
    if _canonical_bytes(record) != _canonical_bytes(rebuilt):
        raise ReferenceEngineError("semantic projection differs from authoritative canonical reconstruction")
    return rebuilt


def _validate_projection_generation_binding(
    projection: Mapping[str, Any], generation: Mapping[str, Any] | None
) -> dict[str, Any]:
    if generation is None:
        raise ReferenceEngineError("automatic correspondence requires an exact generation binding")
    if not isinstance(generation, Mapping) or set(generation) != _GENERATION_FIELDS:
        raise ReferenceEngineError("projection generation binding must use the exact closed field set")
    if generation.get("record_type") != "P1EmpiricalDistinctionGeneration":
        raise ReferenceEngineError("projection generation record type is invalid")
    if generation.get("schema_version") != "0.1" or generation.get("authority_effect") != "NONE":
        raise ReferenceEngineError("projection generation schema or authority is invalid")
    if generation.get("profile_id") != PROFILE_ID or generation.get("immutable") is not True:
        raise ReferenceEngineError("projection generation profile or immutability is invalid")
    if generation.get("generation_id") != projection.get("generation_id"):
        raise ReferenceEngineError("projection wrapper has a stale or mismatched generation binding")
    if generation.get("projection_sha256") != projection.get("projection_sha256"):
        raise ReferenceEngineError("projection generation does not bind canonical projection content")
    series_id = _require_string(generation.get("series_id"), "series_id")
    source_time = _require_string(
        generation.get("source_first_valid_time"), "source_first_valid_time"
    )
    _parse_time(source_time, "source_first_valid_time")
    expected_generation_id = f"p1:generation:{canonical_sha256({'series_id': series_id, 'projection_sha256': projection['projection_sha256'], 'source_first_valid_time': source_time})}"
    if generation.get("generation_id") != expected_generation_id:
        raise ReferenceEngineError("projection generation deterministic identity mismatch")
    return dict(generation)


def _reconcile_identity_bundles(
    existing: Sequence[Mapping[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    validated = [_identity_bundle(item) for item in existing]
    by_generation: dict[str, tuple[bytes, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]] = {}
    series_bytes: dict[str, bytes] = {}
    for bundle in validated:
        series, generation, projection = bundle
        generation_id = generation["generation_id"]
        bundle_bytes = _canonical_bytes(
            {"series": series, "generation": generation, "projection": projection}
        )
        prior = by_generation.get(generation_id)
        if prior is not None and prior[0] != bundle_bytes:
            raise ReferenceEngineError("same generation identity has conflicting canonical bundle content")
        by_generation.setdefault(generation_id, (bundle_bytes, bundle))
        series_id = series["series_id"]
        observed_series_bytes = _canonical_bytes(series)
        if series_id in series_bytes and series_bytes[series_id] != observed_series_bytes:
            raise ReferenceEngineError("same series identity has conflicting canonical series content")
        series_bytes.setdefault(series_id, observed_series_bytes)

    reconciled = [by_generation[key][1] for key in sorted(by_generation)]
    generation_index = {bundle[1]["generation_id"]: bundle for bundle in reconciled}
    for series, _generation, _projection in reconciled:
        first_generation_id = series["first_generation_id"]
        first = generation_index.get(first_generation_id)
        if first is None:
            raise ReferenceEngineError("series first-generation binding is unavailable or unverifiable")
        first_series, first_generation, first_projection = first
        if first_series["series_id"] != series["series_id"] or first_generation["series_id"] != series["series_id"]:
            raise ReferenceEngineError("series first-generation binding crosses series identity")
        expected_series_id = f"p1:series:{canonical_sha256({'owner': first_projection['owner_semantic_binding'], 'projection_sha256': first_projection['projection_sha256']})}"
        if series["series_id"] != expected_series_id:
            raise ReferenceEngineError("series first-generation deterministic identity mismatch")
    return reconciled


def _reconcile_source_record_groups(
    groups: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, list[Mapping[str, Any]]]:
    identities: dict[str, tuple[bytes, str, Mapping[str, Any]]] = {}
    output: dict[str, list[Mapping[str, Any]]] = {name: [] for name in groups}
    for name in sorted(groups):
        local: dict[str, Mapping[str, Any]] = {}
        for record in groups[name]:
            if not isinstance(record, Mapping):
                raise ReferenceEngineError("source evidence records must be objects")
            record_id = _require_string(record.get("record_id"), "record_id")
            content = _canonical_bytes(record)
            prior = identities.get(record_id)
            if prior is not None and prior[0] != content:
                raise ReferenceEngineError("source record identity has conflicting canonical content")
            if prior is not None and prior[1] != name:
                raise ReferenceEngineError("source record identity is reused across evidence owners")
            identities.setdefault(record_id, (content, name, record))
            local.setdefault(record_id, record)
        output[name] = [local[key] for key in sorted(local)]
    return output


def _identity_bundle(entry: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not isinstance(entry, Mapping) or set(entry) != {"series", "generation", "projection"}:
        raise ReferenceEngineError("existing identity bundle must use the exact field set")
    series = entry["series"]
    generation = entry["generation"]
    projection = entry["projection"]
    if not all(isinstance(value, Mapping) for value in (series, generation, projection)):
        raise ReferenceEngineError("identity bundle records must be objects")
    if set(series) != _SERIES_FIELDS or set(generation) != _GENERATION_FIELDS or set(projection) != _PROJECTION_FIELDS:
        raise ReferenceEngineError("identity bundle records must use their exact closed schema fields")
    if series.get("record_type") != "P1EmpiricalDistinctionSeries":
        raise ReferenceEngineError("identity bundle series type is invalid")
    if generation.get("record_type") != "P1EmpiricalDistinctionGeneration":
        raise ReferenceEngineError("identity bundle generation type is invalid")
    if projection.get("record_type") != "P1DistinctionSemanticProjection":
        raise ReferenceEngineError("identity bundle projection type is invalid")
    if any(record.get("schema_version") != "0.1" for record in (series, generation, projection)):
        raise ReferenceEngineError("identity bundle schema version is invalid")
    if any(record.get("authority_effect") != "NONE" for record in (series, generation, projection)):
        raise ReferenceEngineError("identity bundle authority must remain NONE")
    if generation.get("profile_id") != PROFILE_ID or projection.get("profile_id") != PROFILE_ID:
        raise ReferenceEngineError("identity bundle semantic profile is invalid")
    projection = _validate_projection(projection)
    series_id = _require_string(series.get("series_id"), "series_id")
    generation_id = _require_string(generation.get("generation_id"), "generation_id")
    _require_string(series.get("first_generation_id"), "first_generation_id")
    predecessor_refs = series.get("predecessor_series_refs")
    if (
        not isinstance(predecessor_refs, list)
        or any(type(ref) is not str or not ref for ref in predecessor_refs)
        or len(predecessor_refs) != len(set(predecessor_refs))
    ):
        raise ReferenceEngineError("predecessor series refs must be exact unique strings")
    if generation.get("series_id") != series.get("series_id"):
        raise ReferenceEngineError("generation is not bound to its series")
    if projection.get("generation_id") != generation.get("generation_id"):
        raise ReferenceEngineError("projection is not bound to its generation")
    if projection.get("projection_sha256") != generation.get("projection_sha256"):
        raise ReferenceEngineError("generation does not bind exact projection hash")
    if generation.get("immutable") is not True:
        raise ReferenceEngineError("P1CDI generations must be immutable")
    try:
        actual_projection_sha = hashlib.sha256(projection_bytes(projection)).hexdigest()
    except ValueError as exc:
        raise ReferenceEngineError("historical projection is not canonical") from exc
    if projection.get("projection_sha256") != actual_projection_sha:
        raise ReferenceEngineError("historical projection content/hash mismatch")
    source_first_valid_time = _require_string(
        generation.get("source_first_valid_time"), "source_first_valid_time"
    )
    _parse_time(source_first_valid_time, "source_first_valid_time")
    expected_generation_id = f"p1:generation:{canonical_sha256({'series_id': series_id, 'projection_sha256': actual_projection_sha, 'source_first_valid_time': source_first_valid_time})}"
    if generation_id != expected_generation_id:
        raise ReferenceEngineError("historical generation ID/content binding mismatch")
    if series.get("first_generation_id") == generation_id:
        expected_series_id = f"p1:series:{canonical_sha256({'owner': projection.get('owner_semantic_binding'), 'projection_sha256': actual_projection_sha})}"
        if series_id != expected_series_id:
            raise ReferenceEngineError("historical first-generation series binding mismatch")
    return dict(series), dict(generation), dict(projection)


def assign_series_generation(
    *,
    owner_semantic_binding: str,
    identity_fields: Mapping[str, Any],
    source_first_valid_time: str,
    existing: Sequence[Mapping[str, Any]] = (),
    predecessor_generation_id: str | None = None,
    source_explicit_successor_ref: str | None = None,
) -> dict[str, Any]:
    """Resolve exact rediscovery or create one immutable, deterministic generation."""

    _require_string(owner_semantic_binding, "owner_semantic_binding")
    candidate_first_valid_time = _parse_time(
        source_first_valid_time, "source_first_valid_time"
    )
    candidate = build_semantic_projection(
        generation_id="p1:candidate:unassigned",
        owner_semantic_binding=owner_semantic_binding,
        identity_fields=identity_fields,
    )
    bundles = _reconcile_identity_bundles(existing)
    exact = [bundle for bundle in bundles if exact_semantic_equal(candidate, bundle[2])]
    exact_ids = {bundle[1]["generation_id"] for bundle in exact}
    if len(exact_ids) > 1:
        raise ReferenceEngineError("exact semantic identity resolves to multiple generations")
    if exact:
        series, generation, projection = exact[0]
        return {
            "resolution": "EXACT_REDISCOVERY",
            "series": series,
            "generation": generation,
            "projection": projection,
            "created": False,
            "predecessor_generation_id": None,
            "authority_effect": "NONE",
        }

    projection_sha = candidate["projection_sha256"]
    predecessor: tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None = None
    if predecessor_generation_id is not None:
        _require_string(predecessor_generation_id, "predecessor_generation_id")
        matches = [bundle for bundle in bundles if bundle[1]["generation_id"] == predecessor_generation_id]
        if len(matches) != 1:
            raise ReferenceEngineError("semantic successor requires one exact predecessor generation")
        _require_string(source_explicit_successor_ref, "source_explicit_successor_ref")
        predecessor = matches[0]
        predecessor_first_valid_time = _parse_time(
            predecessor[1]["source_first_valid_time"],
            "predecessor.source_first_valid_time",
        )
        if candidate_first_valid_time <= predecessor_first_valid_time:
            raise ReferenceEngineError(
                "semantic successor source_first_valid_time must move strictly forward"
            )
        series_id = predecessor[0]["series_id"]
        series = predecessor[0]
        resolution = "SEMANTIC_SUCCESSOR"
    else:
        if source_explicit_successor_ref is not None:
            raise ReferenceEngineError("successor source ref requires a predecessor")
        series_id = f"p1:series:{canonical_sha256({'owner': owner_semantic_binding, 'projection_sha256': projection_sha})}"
        resolution = "NEW_SERIES"
        series = None

    generation_identity = {
        "series_id": series_id,
        "projection_sha256": projection_sha,
        "source_first_valid_time": source_first_valid_time,
    }
    generation_id = f"p1:generation:{canonical_sha256(generation_identity)}"
    projection = build_semantic_projection(
        generation_id=generation_id,
        owner_semantic_binding=owner_semantic_binding,
        identity_fields=identity_fields,
    )
    generation = {
        "record_type": "P1EmpiricalDistinctionGeneration",
        "schema_version": "0.1",
        "authority_effect": "NONE",
        "generation_id": generation_id,
        "series_id": series_id,
        "profile_id": PROFILE_ID,
        "projection_sha256": projection_sha,
        "source_first_valid_time": source_first_valid_time,
        "immutable": True,
    }
    if series is None:
        series = {
            "record_type": "P1EmpiricalDistinctionSeries",
            "schema_version": "0.1",
            "authority_effect": "NONE",
            "series_id": series_id,
            "first_generation_id": generation_id,
            "predecessor_series_refs": [],
        }
    return {
        "resolution": resolution,
        "series": series,
        "generation": generation,
        "projection": projection,
        "created": True,
        "predecessor_generation_id": predecessor_generation_id,
        "source_explicit_successor_ref": source_explicit_successor_ref,
        "authority_effect": "NONE",
    }


def resolve_dmrp_independence(
    *,
    left_generation_id: str,
    right_generation_id: str,
    evidence_records: Sequence[Mapping[str, Any]],
    as_of_time: str | None = None,
) -> dict[str, Any]:
    """Resolve only exact, current DMRP-owned independence evidence."""

    left_generation_id = _require_string(left_generation_id, "left_generation_id")
    right_generation_id = _require_string(right_generation_id, "right_generation_id")
    as_of = _parse_time(as_of_time, "as_of_time") if as_of_time is not None else None
    normalized: list[dict[str, Any]] = []
    reconciled = _reconcile_source_record_groups({"dmrp": evidence_records})["dmrp"]
    for record in reconciled:
        if not isinstance(record, Mapping) or set(record) != _DMRP_INDEPENDENCE_FIELDS:
            raise ReferenceEngineError("DMRP independence evidence must use the exact closed field set")
        item = dict(record)
        _require_string(item["record_id"], "record_id")
        if item["owner"] != "DMRP_EXPOSURE_INFLUENCE_RECORDS":
            raise ReferenceEngineError("independence evidence owner mismatch")
        if (
            item["left_generation_id"] != left_generation_id
            or item["right_generation_id"] != right_generation_id
        ):
            raise ReferenceEngineError("independence evidence generation mismatch")
        source_ref = _require_string(item["source_ref"], "source_ref")
        source_generation = _require_string(item["source_generation"], "source_generation")
        source_sha = _require_string(item["source_sha256"], "source_sha256")
        if len(source_sha) != 64 or any(char not in "0123456789abcdef" for char in source_sha):
            raise ReferenceEngineError("source_sha256 must be a lowercase SHA-256 string")
        current_source_ref = _require_string(item["current_source_ref"], "current_source_ref")
        current_source_generation = _require_string(
            item["current_source_generation"], "current_source_generation"
        )
        current_source_sha = _require_string(
            item["current_source_sha256"], "current_source_sha256"
        )
        if len(current_source_sha) != 64 or any(
            char not in "0123456789abcdef" for char in current_source_sha
        ):
            raise ReferenceEngineError("current_source_sha256 must be a lowercase SHA-256 string")
        valid_time = _parse_time(item["evidence_first_valid_time"], "evidence_first_valid_time")
        if item["currentness_state"] not in {"CURRENT", "STALE", "HISTORICAL", "UNRESOLVED", "CONFLICT"}:
            raise ReferenceEngineError("invalid DMRP evidence currentness state")
        if item["independence_state"] not in {
            "INDEPENDENCE_UNKNOWN",
            "AFFIRMATIVELY_DEPENDENT",
            "AFFIRMATIVELY_INDEPENDENT",
        }:
            raise ReferenceEngineError("invalid DMRP independence state")
        if item["authority_effect"] != "NONE":
            raise ReferenceEngineError("DMRP evidence cannot grant P1CDI authority")
        source_moved = (
            source_ref,
            source_generation,
            source_sha,
        ) != (
            current_source_ref,
            current_source_generation,
            current_source_sha,
        )
        if item["currentness_state"] == "CURRENT" and source_moved:
            raise ReferenceEngineError("DMRP evidence marked current after source frontier moved")
        if item["currentness_state"] == "STALE" and not source_moved:
            raise ReferenceEngineError("DMRP evidence stale state lacks a moved source frontier")
        if as_of is None or valid_time <= as_of:
            normalized.append(item)

    if not normalized:
        return {"state": "INDEPENDENCE_UNKNOWN", "source_refs": [], "reason": "NO_EXPOSURE_RECORD"}
    if any(item["currentness_state"] == "CONFLICT" for item in normalized):
        raise ReferenceEngineError("conflicting DMRP exposure evidence")
    if any(item["currentness_state"] != "CURRENT" for item in normalized):
        return {
            "state": "INDEPENDENCE_UNKNOWN",
            "source_refs": sorted(item["source_ref"] for item in normalized),
            "reason": "DMRP_EVIDENCE_NOT_CURRENT",
        }
    states = {item["independence_state"] for item in normalized}
    if len(states) != 1:
        raise ReferenceEngineError("conflicting DMRP independence states")
    state = states.pop()
    return {
        "state": state,
        "source_refs": sorted(item["source_ref"] for item in normalized),
        "reason": "EXPLICIT_CURRENT_DMRP_EVIDENCE" if state != "INDEPENDENCE_UNKNOWN" else "DMRP_EXPLICIT_UNKNOWN",
    }


def build_correspondence_plane_evidence(
    *,
    owner: str,
    plane: str,
    value: str,
    left_generation_id: str,
    right_generation_id: str,
    source_ref: str,
    source_generation: str,
    evidence_first_valid_time: str,
) -> dict[str, Any]:
    """Build one canonical source-owned proof for an existing correspondence plane."""

    owner = _require_string(owner, "owner")
    if plane not in _NON_SEMANTIC_SOURCE_PLANES:
        raise ReferenceEngineError("plane evidence must name one registered non-semantic plane")
    registry_key = {
        "core_relation": "core",
        "occurrence_relation": "occurrence",
        "envelope_relation": "envelope",
        "lineage_relation": "lineage",
    }[plane]
    if type(value) is not str or value not in RELATION_REGISTRY[registry_key]:
        raise ReferenceEngineError("plane evidence value is unregistered")
    left_generation_id = _require_string(left_generation_id, "left_generation_id")
    right_generation_id = _require_string(right_generation_id, "right_generation_id")
    source_ref = _require_string(source_ref, "source_ref")
    source_generation = _require_string(source_generation, "source_generation")
    _parse_time(evidence_first_valid_time, "evidence_first_valid_time")
    source_content = {
        "owner": owner,
        "plane": plane,
        "value": value,
        "left_generation_id": left_generation_id,
        "right_generation_id": right_generation_id,
        "source_generation": source_generation,
    }
    source_sha = hashlib.sha256(_canonical_bytes(source_content)).hexdigest()
    identity = {
        "source_ref": source_ref,
        "source_sha256": source_sha,
        "evidence_first_valid_time": evidence_first_valid_time,
    }
    return {
        "record_type": "P1CorrespondencePlaneEvidence",
        "schema_version": "0.1",
        "record_id": f"p1:plane-evidence:{canonical_sha256(identity)}",
        "owner": owner,
        "plane": plane,
        "value": value,
        "left_generation_id": left_generation_id,
        "right_generation_id": right_generation_id,
        "source_ref": source_ref,
        "source_generation": source_generation,
        "source_content": source_content,
        "source_sha256": source_sha,
        "current_source_ref": source_ref,
        "current_source_generation": source_generation,
        "current_source_sha256": source_sha,
        "evidence_first_valid_time": evidence_first_valid_time,
        "currentness_state": "CURRENT",
        "authority_effect": "NONE",
    }


def _resolve_plane_evidence(
    *,
    left_generation_id: str,
    right_generation_id: str,
    evidence_records: Sequence[Mapping[str, Any]],
    as_of_time: str | None,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    as_of = _parse_time(as_of_time, "as_of_time") if as_of_time is not None else None
    reconciled = _reconcile_source_record_groups({"planes": evidence_records})["planes"]
    by_plane: dict[str, list[dict[str, Any]]] = {
        plane: [] for plane in sorted(_NON_SEMANTIC_SOURCE_PLANES)
    }
    for record in reconciled:
        if set(record) != _PLANE_EVIDENCE_FIELDS:
            raise ReferenceEngineError("plane evidence must use the exact closed field set")
        item = dict(record)
        if item["record_type"] != "P1CorrespondencePlaneEvidence":
            raise ReferenceEngineError("plane evidence record type is invalid")
        if item["schema_version"] != "0.1" or item["authority_effect"] != "NONE":
            raise ReferenceEngineError("plane evidence schema or authority is invalid")
        _require_string(item["record_id"], "record_id")
        _require_string(item["owner"], "owner")
        plane = item["plane"]
        if plane not in _NON_SEMANTIC_SOURCE_PLANES:
            raise ReferenceEngineError("plane evidence names an unregistered plane")
        registry_key = {
            "core_relation": "core",
            "occurrence_relation": "occurrence",
            "envelope_relation": "envelope",
            "lineage_relation": "lineage",
        }[plane]
        if type(item["value"]) is not str or item["value"] not in RELATION_REGISTRY[registry_key]:
            raise ReferenceEngineError("plane evidence carries an unregistered value")
        if (
            item["left_generation_id"] != left_generation_id
            or item["right_generation_id"] != right_generation_id
        ):
            raise ReferenceEngineError("plane evidence generation binding mismatch")
        source_ref = _require_string(item["source_ref"], "source_ref")
        source_generation = _require_string(item["source_generation"], "source_generation")
        source_sha = _require_string(item["source_sha256"], "source_sha256")
        expected_content = {
            "owner": item["owner"],
            "plane": plane,
            "value": item["value"],
            "left_generation_id": left_generation_id,
            "right_generation_id": right_generation_id,
            "source_generation": source_generation,
        }
        if _canonical_bytes(item["source_content"]) != _canonical_bytes(expected_content):
            raise ReferenceEngineError("plane evidence source content is not canonically owner-bound")
        actual_sha = hashlib.sha256(_canonical_bytes(item["source_content"])).hexdigest()
        if source_sha != actual_sha:
            raise ReferenceEngineError("plane evidence source content/hash mismatch")
        current_ref = _require_string(item["current_source_ref"], "current_source_ref")
        current_generation = _require_string(
            item["current_source_generation"], "current_source_generation"
        )
        current_sha = _require_string(item["current_source_sha256"], "current_source_sha256")
        for digest in (source_sha, current_sha):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ReferenceEngineError("plane evidence hashes must be lowercase SHA-256 strings")
        if item["currentness_state"] not in {"CURRENT", "STALE", "HISTORICAL", "UNRESOLVED", "CONFLICT"}:
            raise ReferenceEngineError("plane evidence currentness state is invalid")
        moved = (source_ref, source_generation, source_sha) != (
            current_ref,
            current_generation,
            current_sha,
        )
        if item["currentness_state"] == "CURRENT" and moved:
            raise ReferenceEngineError("plane evidence marked current after source frontier moved")
        if item["currentness_state"] == "STALE" and not moved:
            raise ReferenceEngineError("plane evidence stale state lacks a moved source frontier")
        valid_time = _parse_time(item["evidence_first_valid_time"], "evidence_first_valid_time")
        if as_of is None or valid_time <= as_of:
            by_plane[plane].append(item)

    resolved: dict[str, str] = {}
    refs: dict[str, list[str]] = {}
    for plane, records in by_plane.items():
        if any(item["currentness_state"] == "CONFLICT" for item in records):
            raise ReferenceEngineError(f"conflicting source evidence for {plane}")
        current = [item for item in records if item["currentness_state"] == "CURRENT"]
        values = {item["value"] for item in current}
        if len(values) > 1:
            raise ReferenceEngineError(f"contradictory current source evidence for {plane}")
        if values:
            resolved[plane] = values.pop()
            refs[plane] = sorted(item["record_id"] for item in current)
    return resolved, refs


def stage_correspondence(
    *,
    left_projection: Mapping[str, Any],
    right_projection: Mapping[str, Any],
    left_generation_record: Mapping[str, Any] | None = None,
    right_generation_record: Mapping[str, Any] | None = None,
    planes: Mapping[str, str],
    admission_basis: str,
    source_relation_ref: str | None = None,
    review_ref: str | None = None,
    plane_evidence_records: Sequence[Mapping[str, Any]] = (),
    independence_evidence: Sequence[Mapping[str, Any]] = (),
    as_of_time: str | None = None,
    left_identity_history: Sequence[Mapping[str, Any]] = (),
    right_identity_history: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Stage plane-local correspondence without transferring truth across planes."""

    reference_module = sys.modules[__name__]
    validate_correspondence_series_root(
        reference_module,
        projection=left_projection,
        generation=left_generation_record,
        identity_history=left_identity_history,
    )
    validate_correspondence_series_root(
        reference_module,
        projection=right_projection,
        generation=right_generation_record,
        identity_history=right_identity_history,
    )

    if not isinstance(planes, Mapping) or set(planes) != _CORRESPONDENCE_PLANES:
        raise ReferenceEngineError("correspondence must supply every exact relation plane")
    for field, registry_key in {
        "semantic_relation": "semantic",
        "core_relation": "core",
        "occurrence_relation": "occurrence",
        "envelope_relation": "envelope",
        "lineage_relation": "lineage",
        "independence_state": "independence",
    }.items():
        if type(planes[field]) is not str or planes[field] not in RELATION_REGISTRY[registry_key]:
            raise ReferenceEngineError(f"unregistered correspondence plane value: {field}")
    left_projection = _validate_projection(left_projection)
    right_projection = _validate_projection(right_projection)
    _validate_projection_generation_binding(left_projection, left_generation_record)
    _validate_projection_generation_binding(right_projection, right_generation_record)
    left_generation = left_projection["generation_id"]
    right_generation = right_projection["generation_id"]
    reconciled_evidence = _reconcile_source_record_groups(
        {
            "dmrp": independence_evidence,
            "planes": plane_evidence_records,
        }
    )
    resolved_planes, plane_evidence_refs = _resolve_plane_evidence(
        left_generation_id=left_generation,
        right_generation_id=right_generation,
        evidence_records=reconciled_evidence["planes"],
        as_of_time=as_of_time,
    )
    for plane, resolved_value in resolved_planes.items():
        if planes[plane] != resolved_value:
            raise ReferenceEngineError(f"correspondence claim conflicts with exact source evidence: {plane}")
    independence = resolve_dmrp_independence(
        left_generation_id=left_generation,
        right_generation_id=right_generation,
        evidence_records=reconciled_evidence["dmrp"],
        as_of_time=as_of_time,
    )
    if planes["independence_state"] != independence["state"]:
        raise ReferenceEngineError(
            "correspondence independence must equal exact DMRP-owned evidence resolution"
        )
    exact = exact_semantic_equal(left_projection, right_projection)
    semantic = planes["semantic_relation"]
    if exact and semantic != "EXACT_EQUIVALENT":
        raise ReferenceEngineError("byte-exact projections require EXACT_EQUIVALENT")
    if not exact and semantic == "EXACT_EQUIVALENT":
        raise ReferenceEngineError("non-exact projections cannot claim EXACT_EQUIVALENT")
    if admission_basis == "EXACT_CANONICAL_BYTES":
        if not exact or source_relation_ref is not None or review_ref is not None:
            raise ReferenceEngineError("exact automatic admission must be byte-exact only")
        executability = "AUTO_ADMITTED"
    elif admission_basis == "SOURCE_EXPLICIT_DETERMINISTIC_RELATION":
        _require_string(source_relation_ref, "source_relation_ref")
        if exact:
            raise ReferenceEngineError("exact equality must use exact canonical-byte admission")
        executability = "REVIEW_REQUIRED"
    elif admission_basis == "REVIEWED_NON_EXACT":
        _require_string(review_ref, "review_ref")
        if exact:
            raise ReferenceEngineError("exact equality must not be labelled reviewed non-exact")
        executability = "REVIEW_REQUIRED"
    else:
        raise ReferenceEngineError("unknown correspondence admission basis")
    unresolved_planes = sorted(
        set(_NON_SEMANTIC_SOURCE_PLANES) - set(resolved_planes)
    )
    if independence["state"] == "INDEPENDENCE_UNKNOWN" and not independence["source_refs"]:
        unresolved_planes.append("independence_state")
    plane_admission: dict[str, dict[str, Any]] = {
        "semantic_relation": {
            "status": "RESOLVED",
            "value": semantic,
            "basis": admission_basis,
            "evidence_refs": [],
        }
    }
    for plane in sorted(_NON_SEMANTIC_SOURCE_PLANES):
        if plane in resolved_planes:
            plane_admission[plane] = {
                "status": "RESOLVED",
                "value": resolved_planes[plane],
                "basis": "EXACT_OWNER_SOURCE_EVIDENCE",
                "evidence_refs": plane_evidence_refs[plane],
            }
        else:
            plane_admission[plane] = {
                "status": "UNRESOLVED",
                "value": None,
                "basis": "NO_EXACT_CURRENT_PLANE_EVIDENCE",
                "evidence_refs": [],
            }
    plane_admission["independence_state"] = {
        "status": "RESOLVED" if independence["source_refs"] else "UNRESOLVED",
        "value": independence["state"],
        "basis": independence["reason"],
        "evidence_refs": independence["source_refs"],
    }
    identity = {
        "left_generation_id": left_generation,
        "right_generation_id": right_generation,
        **{key: planes[key] for key in sorted(planes)},
        "admission_basis": admission_basis,
        "source_relation_ref": source_relation_ref,
        "review_ref": review_ref,
        "plane_evidence_refs": plane_evidence_refs,
        "independence_evidence_refs": independence["source_refs"],
    }
    record = None
    if not unresolved_planes:
        record = {
            "record_type": "P1DistinctionCorrespondenceRecord",
            "schema_version": "0.1",
            "correspondence_id": f"p1:correspondence:{canonical_sha256(identity)}",
            "left_generation_id": left_generation,
            "right_generation_id": right_generation,
            **dict(planes),
            "admission_basis": admission_basis,
            "executability": executability,
            "authority_effect": "NONE",
        }
    return {
        "record": record,
        "semantic_identity": "EXACT" if exact else "NON_EXACT",
        "plane_admission": plane_admission,
        "unresolved_planes": unresolved_planes,
        "executability": executability if record is not None else "BLOCKED_UNRESOLVED_PLANES",
        "source_relation_ref": source_relation_ref,
        "review_ref": review_ref,
        "plane_evidence_refs": plane_evidence_refs,
        "independence_evidence_refs": independence["source_refs"],
        "independence_reason": independence["reason"],
        "decision_bearing": False,
        "authority_effect": "NONE",
    }


def _validate_vector(record: Mapping[str, Any], generation_id: str) -> dict[str, Any]:
    if not isinstance(record, Mapping) or set(record) != _VECTOR_FIELDS:
        raise ReferenceEngineError("evidence vector input must use the exact schema field set")
    if record.get("record_type") != "P1DistinctionEvidenceStateVector":
        raise ReferenceEngineError("evidence vector input type is invalid")
    if record.get("schema_version") != "0.1" or record.get("authority_effect") != "NONE":
        raise ReferenceEngineError("evidence vector schema or authority is invalid")
    if record.get("generation_id") != generation_id:
        raise ReferenceEngineError("evidence vector generation mismatch")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or not refs or any(type(ref) is not str or not ref for ref in refs):
        raise ReferenceEngineError("evidence vector requires exact source refs")
    if len(refs) != len(set(refs)) or not isinstance(record.get("other_planes"), Mapping):
        raise ReferenceEngineError("evidence vector source refs or other planes are invalid")
    for plane, allowed in EVIDENCE_PLANE_REGISTRY["vector_planes"].items():
        value = record.get(plane)
        if type(value) is not str or value not in allowed:
            raise ReferenceEngineError(f"unregistered {plane} state")
    other_planes = record["other_planes"]
    allowed_other = EVIDENCE_PLANE_REGISTRY["other_planes"]
    unknown = set(other_planes) - set(allowed_other)
    if unknown:
        raise ReferenceEngineError(f"unknown evidence planes: {sorted(unknown)}")
    forbidden = set(EVIDENCE_PLANE_REGISTRY["forbidden_scalar_keys"])
    for key, value in other_planes.items():
        if type(key) is not str or key.lower() in forbidden:
            raise ReferenceEngineError("hidden scalar or invalid evidence-plane key")
        specification = allowed_other[key]
        allowed_types = specification["type"]
        allowed_types = [allowed_types] if isinstance(allowed_types, str) else allowed_types
        type_matches = {
            "null": value is None,
            "boolean": type(value) is bool,
            "integer": type(value) is int,
            "number": type(value) in {int, float},
            "string": type(value) is str,
        }
        if not any(type_matches[name] for name in allowed_types):
            raise ReferenceEngineError(f"malformed typed evidence plane: {key}")
        if "enum" in specification and value not in specification["enum"]:
            raise ReferenceEngineError(f"unregistered typed evidence-plane value: {key}")
    return dict(record)


def _validate_preserved_record(
    *, name: str, record: Mapping[str, Any], generation_id: str, expected_type: str
) -> dict[str, Any]:
    if not isinstance(record, Mapping) or set(record) != _PRESERVED_RECORD_FIELDS[name]:
        raise ReferenceEngineError(f"{name} source record must use the exact closed field set")
    item = dict(record)
    if item.get("record_type") != expected_type:
        raise ReferenceEngineError(f"invalid {name} source record")
    if item.get("schema_version") != "0.1" or item.get("authority_effect") != "NONE":
        raise ReferenceEngineError(f"{name} schema or authority mismatch")
    _require_string(item.get("record_id"), "record_id")
    if item.get("generation_id") != generation_id:
        raise ReferenceEngineError(f"{name} generation mismatch")
    refs = item.get("source_refs")
    if (
        not isinstance(refs, list)
        or not refs
        or any(type(ref) is not str or not ref for ref in refs)
        or len(refs) != len(set(refs))
    ):
        raise ReferenceEngineError(f"{name} requires exact unique source refs")
    preserved_registry = EVIDENCE_PLANE_REGISTRY["preserved_record_planes"]
    if name == "replications":
        if item["replication_kind"] not in preserved_registry["replication_kind"]:
            raise ReferenceEngineError("invalid replication_kind")
        if item["outcome"] not in preserved_registry["replication_outcome"]:
            raise ReferenceEngineError("invalid replication outcome")
    elif name == "null_bindings":
        if item["null_class"] not in preserved_registry["null_class"]:
            raise ReferenceEngineError("invalid null_class")
    else:
        _require_string(item["contradiction_type"], "contradiction_type")
    return item


def _precedence(values: Sequence[str], ordered: Sequence[str]) -> str:
    observed = set(values)
    for value in ordered:
        if value in observed:
            return value
    raise ReferenceEngineError("evidence plane contains no registered value")


def _combine_recurrence(values: Sequence[str]) -> str:
    observed = set(values)
    if not observed <= {"NOT_TESTED", "PRESENT", "ABSENT", "NOT_EVALUABLE", "CAPACITY_INCOMPLETE"}:
        raise ReferenceEngineError("unregistered recurrence state")
    if "CAPACITY_INCOMPLETE" in observed:
        return "CAPACITY_INCOMPLETE"
    if "NOT_EVALUABLE" in observed or {"PRESENT", "ABSENT"} <= observed:
        return "NOT_EVALUABLE"
    if "PRESENT" in observed:
        return "PRESENT"
    if observed == {"ABSENT"}:
        return "ABSENT"
    if "ABSENT" in observed and "NOT_TESTED" in observed:
        return "NOT_EVALUABLE"
    return "NOT_TESTED"


def _combine_dependence(values: Sequence[str]) -> str:
    observed = set(values)
    if not observed <= {"INDEPENDENCE_UNKNOWN", "DEPENDENT", "INDEPENDENT_AFFIRMATIVE", "UNRESOLVED"}:
        raise ReferenceEngineError("unregistered dependence state")
    if "UNRESOLVED" in observed or {"DEPENDENT", "INDEPENDENT_AFFIRMATIVE"} <= observed:
        return "UNRESOLVED"
    if "DEPENDENT" in observed:
        return "DEPENDENT"
    if observed == {"INDEPENDENT_AFFIRMATIVE"}:
        return "INDEPENDENT_AFFIRMATIVE"
    return "INDEPENDENCE_UNKNOWN"


def assemble_evidence_reference(
    *,
    generation_id: str,
    vector_inputs: Sequence[Mapping[str, Any]],
    replication_records: Sequence[Mapping[str, Any]],
    null_records: Sequence[Mapping[str, Any]],
    contradiction_records: Sequence[Mapping[str, Any]],
    frontier_first_valid_time: str,
    scientific_disposition_ref: str | None = None,
) -> dict[str, Any]:
    """Assemble a typed non-scalar vector while retaining negative source records."""

    _require_string(generation_id, "generation_id")
    _parse_time(frontier_first_valid_time, "frontier_first_valid_time")
    if not vector_inputs:
        raise ReferenceEngineError("at least one source-owned evidence vector is required")
    reconciled = _reconcile_source_record_groups(
        {
            "vectors": vector_inputs,
            "replications": replication_records,
            "null_bindings": null_records,
            "contradictions": contradiction_records,
        }
    )
    vectors = [_validate_vector(record, generation_id) for record in reconciled["vectors"]]
    preserved: dict[str, list[dict[str, Any]]] = {
        "replications": [],
        "null_bindings": [],
        "contradictions": [],
    }
    expected_types = {
        "replications": "P1ReplicationOutcomeRecord",
        "null_bindings": "P1NullEvidenceBinding",
        "contradictions": "P1DistinctionContradictionRecord",
    }
    for name, records in (
        ("replications", reconciled["replications"]),
        ("null_bindings", reconciled["null_bindings"]),
        ("contradictions", reconciled["contradictions"]),
    ):
        for record in records:
            preserved[name].append(
                _validate_preserved_record(
                    name=name,
                    record=record,
                    generation_id=generation_id,
                    expected_type=expected_types[name],
                )
            )
        preserved[name].sort(key=lambda item: item["record_id"])

    source_refs = sorted(
        {
            ref
            for record in [*vectors, *preserved["replications"], *preserved["null_bindings"], *preserved["contradictions"]]
            for ref in record.get("source_refs", [])
        }
    )
    if not source_refs:
        raise ReferenceEngineError("evidence assembly requires source-owned references")
    other_planes: dict[str, list[Any]] = {}
    for vector in vectors:
        for key, value in vector["other_planes"].items():
            if type(key) is not str:
                raise ReferenceEngineError("other evidence plane keys must be strings")
            other_planes.setdefault(key, []).append(value)
    for key, values in other_planes.items():
        unique = {json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False): value for value in values}
        other_planes[key] = [unique[name] for name in sorted(unique)]

    vector_identity = {
        "generation_id": generation_id,
        "source_refs": source_refs,
        "rule_profile_ref": RULE_PROFILE_ID,
        "input_record_ids": sorted(vector["record_id"] for vector in vectors),
    }
    vector = {
        "record_type": "P1DistinctionEvidenceStateVector",
        "schema_version": "0.1",
        "record_id": f"p1:evidence-vector:{canonical_sha256(vector_identity)}",
        "generation_id": generation_id,
        "source_refs": source_refs,
        "denominator": _precedence(
            [item["denominator"] for item in vectors],
            RULE_PROFILE["evidence_vector"]["denominator_precedence"],
        ),
        "recurrence": _combine_recurrence([item["recurrence"] for item in vectors]),
        "dependence": _combine_dependence([item["dependence"] for item in vectors]),
        "separation": _precedence(
            [item["separation"] for item in vectors],
            RULE_PROFILE["evidence_vector"]["separation_precedence"],
        ),
        "integrity": _precedence(
            [item["integrity"] for item in vectors],
            RULE_PROFILE["evidence_vector"]["integrity_precedence"],
        ),
        "other_planes": other_planes,
        "authority_effect": "NONE",
    }
    frontier = {
        "record_type": "P1EvidenceFrontierManifest",
        "schema_version": "0.1",
        "record_id": f"p1:evidence-frontier:{canonical_sha256({'generation_id': generation_id, 'source_refs': source_refs, 'time': frontier_first_valid_time})}",
        "generation_id": generation_id,
        "source_refs": source_refs,
        "frontier_first_valid_time": frontier_first_valid_time,
        "authority_effect": "NONE",
    }
    if scientific_disposition_ref is not None:
        _require_string(scientific_disposition_ref, "scientific_disposition_ref")
        assessment_state = "SOURCE_OWNER_REFERENCE"
    else:
        assessment_state = "UNRESOLVED"
    assessment = {
        "record_type": "P1DistinctionEvidenceAssessment",
        "schema_version": "0.1",
        "record_id": f"p1:evidence-assessment:{canonical_sha256({'vector': vector['record_id'], 'disposition_ref': scientific_disposition_ref})}",
        "generation_id": generation_id,
        "source_refs": source_refs,
        "rule_profile_ref": RULE_PROFILE_ID,
        "scientific_disposition_ref": scientific_disposition_ref,
        "scientific_assessment_state": assessment_state,
        "authority_effect": "NONE",
    }
    return {
        "frontier": frontier,
        "vector": vector,
        "assessment": assessment,
        **preserved,
        "decision_bearing": False,
        "authority_effect": "NONE",
    }


def replay_as_of(
    *, records: Sequence[Mapping[str, Any]], as_of_time: str
) -> list[dict[str, Any]]:
    """Return correction-chain tips visible at AS_OF; later corrections cannot rewrite history."""

    as_of = _parse_time(as_of_time, "as_of_time")
    normalized: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping) or set(record) != _HISTORY_FIELDS:
            raise ReferenceEngineError("history record must use the exact closed field set")
        item = dict(record)
        record_id = _require_string(item["record_id"], "record_id")
        _require_string(item["logical_id"], "logical_id")
        _parse_time(item["first_valid_time"], "first_valid_time")
        if item["correction_of"] is not None:
            _require_string(item["correction_of"], "correction_of")
        refs = item["source_refs"]
        if (
            not isinstance(refs, list)
            or not refs
            or any(type(ref) is not str or not ref for ref in refs)
            or len(refs) != len(set(refs))
        ):
            raise ReferenceEngineError("history record requires unique source refs")
        if record_id in by_id:
            raise ReferenceEngineError("duplicate history record_id")
        by_id[record_id] = item
        normalized.append(item)
    for item in normalized:
        predecessor_id = item["correction_of"]
        if predecessor_id is None:
            continue
        predecessor = by_id.get(predecessor_id)
        if predecessor is None or predecessor["logical_id"] != item["logical_id"]:
            raise ReferenceEngineError("history correction predecessor is missing or cross-logical")
        if _parse_time(predecessor["first_valid_time"], "first_valid_time") >= _parse_time(
            item["first_valid_time"], "first_valid_time"
        ):
            raise ReferenceEngineError("history correction must move first-valid time forward")

    result: list[dict[str, Any]] = []
    logical_ids = sorted({item["logical_id"] for item in normalized})
    for logical_id in logical_ids:
        eligible = [
            item
            for item in normalized
            if item["logical_id"] == logical_id
            and _parse_time(item["first_valid_time"], "first_valid_time") <= as_of
        ]
        if not eligible:
            continue
        corrected_ids = {item["correction_of"] for item in eligible if item["correction_of"] is not None}
        tips = [item for item in eligible if item["record_id"] not in corrected_ids]
        if len(tips) != 1:
            raise ReferenceEngineError(f"ambiguous correction frontier for {logical_id}")
        result.append(tips[0])
    return result
