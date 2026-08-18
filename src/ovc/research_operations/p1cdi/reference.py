from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .identity import PROFILE_ID, build_semantic_projection, exact_semantic_equal


_RULE_PROFILE_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p1cdi/reference_rule_profile_v1.json"
)
_RELATION_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p1cdi/relation_registry.json"
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


def _identity_bundle(entry: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not isinstance(entry, Mapping) or set(entry) != {"series", "generation", "projection"}:
        raise ReferenceEngineError("existing identity bundle must use the exact field set")
    series = entry["series"]
    generation = entry["generation"]
    projection = entry["projection"]
    if not all(isinstance(value, Mapping) for value in (series, generation, projection)):
        raise ReferenceEngineError("identity bundle records must be objects")
    if series.get("record_type") != "P1EmpiricalDistinctionSeries":
        raise ReferenceEngineError("identity bundle series type is invalid")
    if generation.get("record_type") != "P1EmpiricalDistinctionGeneration":
        raise ReferenceEngineError("identity bundle generation type is invalid")
    if projection.get("record_type") != "P1DistinctionSemanticProjection":
        raise ReferenceEngineError("identity bundle projection type is invalid")
    if generation.get("series_id") != series.get("series_id"):
        raise ReferenceEngineError("generation is not bound to its series")
    if projection.get("generation_id") != generation.get("generation_id"):
        raise ReferenceEngineError("projection is not bound to its generation")
    if projection.get("projection_sha256") != generation.get("projection_sha256"):
        raise ReferenceEngineError("generation does not bind exact projection hash")
    if generation.get("immutable") is not True:
        raise ReferenceEngineError("P1CDI generations must be immutable")
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
    _parse_time(source_first_valid_time, "source_first_valid_time")
    candidate = build_semantic_projection(
        generation_id="p1:candidate:unassigned",
        owner_semantic_binding=owner_semantic_binding,
        identity_fields=identity_fields,
    )
    bundles = [_identity_bundle(item) for item in existing]
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


def stage_correspondence(
    *,
    left_projection: Mapping[str, Any],
    right_projection: Mapping[str, Any],
    planes: Mapping[str, str],
    admission_basis: str,
    source_relation_ref: str | None = None,
    review_ref: str | None = None,
) -> dict[str, Any]:
    """Stage exact or non-exact multi-plane correspondence without fuzzy inference."""

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
    left_generation = _require_string(left_projection.get("generation_id"), "left_generation_id")
    right_generation = _require_string(right_projection.get("generation_id"), "right_generation_id")
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
    identity = {
        "left_generation_id": left_generation,
        "right_generation_id": right_generation,
        **{key: planes[key] for key in sorted(planes)},
        "admission_basis": admission_basis,
        "source_relation_ref": source_relation_ref,
        "review_ref": review_ref,
    }
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
        "source_relation_ref": source_relation_ref,
        "review_ref": review_ref,
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
    return dict(record)


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
    vectors = [_validate_vector(record, generation_id) for record in vector_inputs]
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
        ("replications", replication_records),
        ("null_bindings", null_records),
        ("contradictions", contradiction_records),
    ):
        for record in records:
            if not isinstance(record, Mapping) or record.get("record_type") != expected_types[name]:
                raise ReferenceEngineError(f"invalid {name} source record")
            if record.get("generation_id") != generation_id or record.get("authority_effect") != "NONE":
                raise ReferenceEngineError(f"{name} generation or authority mismatch")
            refs = record.get("source_refs")
            if (
                not isinstance(refs, list)
                or not refs
                or any(type(ref) is not str or not ref for ref in refs)
                or len(refs) != len(set(refs))
            ):
                raise ReferenceEngineError(f"{name} requires exact unique source refs")
            preserved[name].append(dict(record))
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
        "confidence_score": None,
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
