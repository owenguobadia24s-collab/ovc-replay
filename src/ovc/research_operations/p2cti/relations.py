from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .identity import control_record_id


_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p2cti/P2CTI_RELATION_TYPE_REGISTRY_v0_1.json"
)
_OWNER_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p2cti/P2CTI_OWNER_SOURCE_REGISTRY_v0_1.json"
)
_RELATION_TYPES = {
    "DUPLICATE_OF": "DUPLICATION",
    "NEAR_DUPLICATE_OF": "DUPLICATION",
    "SPECIAL_CASE_OF": "SCOPE",
    "GENERALISES": "SCOPE",
    "COMPETES_WITH": "COMPETITION",
    "DESCENDS_FROM": "ANCESTRY",
    "CHALLENGES_METHOD_OF": "METHOD_CHALLENGE",
    "ROUTES_TO": "ROUTING",
    "INDICATES_ARCHITECTURE_NEED": "ARCHITECTURE_NEED",
    "CROSS_MODE_RELATED": "CROSS_MODE",
    "EVIDENCE_FOR": "EVIDENCE",
    "SUPERSEDES": "SUPERSESSION",
}
_SEMANTIC_REVIEW_TYPES = {"DUPLICATE_OF", "NEAR_DUPLICATE_OF", "SPECIAL_CASE_OF", "GENERALISES"}
_REVIEWED = {"INDEPENDENT_RULE_REVIEWED", "HUMAN_RESEARCH_OPERATIONS_DECISION"}
_REF_FIELDS = {"owner_programme", "object_id", "semantic_generation", "content_sha256"}
_OWNER_RELATION_EVIDENCE_FIELDS = {
    "owner_programme", "object_type", "object_id", "semantic_generation", "source_path",
    "content_sha256", "authority_refs", "scientific_payload_copied", "relation_type",
    "left_generation_ref", "right_generation_ref", "source_frontier_id", "resolution_state",
    "evidence_origin",
}
_SOURCE_RELATION_REF_FIELDS = {
    "owner_programme", "object_type", "object_id", "semantic_generation", "source_path",
    "content_sha256", "authority_refs", "scientific_payload_copied",
}
_NON_OWNER_PROVENANCE_PREFIXES = (
    "machine://", "llm://", "similarity://", "retrieval://", "proposed://",
)


class RelationValidationError(ValueError):
    """A relation or duplicate assertion is outside the closed WP4 contract."""


def _load_contract() -> tuple[dict[str, dict[str, Any]], frozenset[str]]:
    value = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "ovc-p2cti-relation-type-registry/v0.1":
        raise RuntimeError("relation registry schema mismatch")
    families = value.get("relation_families")
    relation_types = value.get("relation_types")
    qualifications = value.get("qualification")
    if type(families) is not list or type(relation_types) is not list or type(qualifications) is not list:
        raise RuntimeError("relation registry is incomplete")
    by_id = {row["id"]: row for row in families if type(row) is dict and type(row.get("id")) is str}
    if set(by_id) != set(_RELATION_TYPES.values()):
        raise RuntimeError("closed relation family set does not match implementation")
    registered_types = {
        row.get("id"): row.get("family") for row in relation_types if type(row) is dict
    }
    if registered_types != _RELATION_TYPES:
        raise RuntimeError("closed relation type set does not match implementation")
    if value.get("machine_similarity_authority") != "ADVISORY_ONLY":
        raise RuntimeError("machine similarity must remain advisory")
    if value.get("near_duplicate_collapses_identity") is not False:
        raise RuntimeError("near-duplicate identity collapse must be forbidden")
    return by_id, frozenset(qualifications)


_FAMILIES, _QUALIFICATIONS = _load_contract()


def _load_owner_contract() -> dict[str, str]:
    value = json.loads(_OWNER_REGISTRY_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "ovc-p2cti-owner-source-registry/v0.1":
        raise RuntimeError("owner-source registry schema mismatch")
    owners = value.get("owners")
    if type(owners) is not list:
        raise RuntimeError("owner-source registry is incomplete")
    result = {
        row["object_type"]: row["owner"]
        for row in owners
        if type(row) is dict
        and type(row.get("object_type")) is str
        and type(row.get("owner")) is str
    }
    if len(result) != len(owners):
        raise RuntimeError("owner-source registry contains malformed or duplicate object types")
    return result


_OWNER_BY_OBJECT_TYPE = _load_owner_contract()


def _exact_ref(raw: Mapping[str, Any], name: str) -> dict[str, str]:
    if not isinstance(raw, Mapping) or set(raw) != _REF_FIELDS:
        raise RelationValidationError(f"{name} must use the exact semantic-generation reference shape")
    if any(type(raw[field]) is not str or not raw[field] for field in _REF_FIELDS):
        raise RelationValidationError(f"{name} values must be non-empty strings")
    digest = raw["content_sha256"]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise RelationValidationError(f"{name} content_sha256 is invalid")
    return {field: raw[field] for field in sorted(_REF_FIELDS)}


def _current_refs_from_bundle(raw: Mapping[str, Any] | None, source_frontier_id: str) -> frozenset[str]:
    if raw is None:
        return frozenset()
    if not isinstance(raw, Mapping):
        raise RelationValidationError("current_generation_bundle must be an exact canonical bundle")
    if raw.get("schema") != "ovc-p2ctii-generation-zero-bundle/v0.1":
        raise RelationValidationError("current_generation_bundle schema is invalid")
    if raw.get("content_sha256") != canonical_sha256(
        {key: value for key, value in raw.items() if key != "content_sha256"}
    ):
        raise RelationValidationError("current_generation_bundle content hash mismatch")
    generation = raw.get("generation")
    currentness = raw.get("currentness_evaluation")
    frontier = raw.get("source_frontier")
    if not all(isinstance(value, Mapping) for value in (generation, currentness, frontier)):
        raise RelationValidationError("current_generation_bundle is structurally incomplete")
    if (
        generation.get("source_frontier_id") != source_frontier_id
        or frontier.get("frontier_id") != source_frontier_id
        or currentness.get("source_frontier_id") != source_frontier_id
        or currentness.get("generation_id") != generation.get("generation_id")
        or generation.get("completeness_state") != "COMPLETE"
        or currentness.get("currentness_state") != "CURRENT"
        or currentness.get("completeness_state") != "COMPLETE"
    ):
        raise RelationValidationError("current_generation_bundle is stale, incomplete or incoherent")
    entries = raw.get("entries")
    if type(entries) is not list or not entries:
        raise RelationValidationError("current_generation_bundle entries are missing")
    refs = []
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("content_sha256") != canonical_sha256(
            {key: value for key, value in entry.items() if key != "content_sha256"}
        ):
            raise RelationValidationError("current generation entry content hash mismatch")
        source = entry.get("source_object_ref")
        if not isinstance(source, Mapping) or not _REF_FIELDS.issubset(source):
            raise RelationValidationError("current generation source reference is malformed")
        refs.append(_exact_ref({field: source[field] for field in _REF_FIELDS}, "current_generation_ref"))
    identities = [canonical_sha256(item) for item in refs]
    if len(identities) != len(set(identities)):
        raise RelationValidationError("current generation contains duplicate semantic references")
    return frozenset(identities)


def _source_relation_reference(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != _SOURCE_RELATION_REF_FIELDS:
        raise RelationValidationError("source_relation_ref must use the exact closed owner-reference shape")
    for field in _SOURCE_RELATION_REF_FIELDS - {"authority_refs", "scientific_payload_copied"}:
        if type(raw[field]) is not str or not raw[field]:
            raise RelationValidationError(f"source_relation_ref {field} is malformed")
    digest = raw["content_sha256"]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise RelationValidationError("source_relation_ref content_sha256 is invalid")
    refs = raw["authority_refs"]
    if type(refs) is not list or not refs or any(type(ref) is not str or not ref for ref in refs):
        raise RelationValidationError("source_relation_ref authority_refs are invalid")
    if len(refs) != len(set(refs)):
        raise RelationValidationError("source_relation_ref authority_refs must be unique")
    if raw["scientific_payload_copied"] is not False:
        raise RelationValidationError("source_relation_ref must remain reference-only")
    object_type = raw["object_type"]
    declared_owner = _OWNER_BY_OBJECT_TYPE.get(object_type)
    if declared_owner is None:
        raise RelationValidationError(f"unknown source_relation_ref object_type: {object_type}")
    normalized = {field: raw[field] for field in sorted(_SOURCE_RELATION_REF_FIELDS)}
    normalized["authority_refs"] = sorted(refs)
    return normalized


def _owner_relation_evidence(
    raw: Sequence[Mapping[str, Any]], *, relation_type: str, left: Mapping[str, Any],
    right: Mapping[str, Any], source_frontier_id: str,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise RelationValidationError("owner_relation_evidence must be a sequence of typed records")
    if not raw:
        return "UNRESOLVED", [], ["OWNER_RELATION_EVIDENCE_MISSING"]
    normalized: list[dict[str, Any]] = []
    conflicts: set[str] = set()
    unresolved: set[str] = set()
    for row in raw:
        if not isinstance(row, Mapping) or set(row) != _OWNER_RELATION_EVIDENCE_FIELDS:
            raise RelationValidationError("owner relation evidence must use the exact closed field set")
        owner = row["owner_programme"]
        object_type = row["object_type"]
        if type(owner) is not str or not owner or type(object_type) is not str or not object_type:
            raise RelationValidationError("owner relation evidence identity is malformed")
        declared_owner = _OWNER_BY_OBJECT_TYPE.get(object_type)
        if declared_owner is None:
            raise RelationValidationError(f"unknown owner relation evidence object_type: {object_type}")
        if declared_owner != "DECLARED_AUTHORITY_OWNER" and owner != declared_owner:
            conflicts.add("STATE_OWNER_CONFLICT")
        if row["relation_type"] != relation_type:
            conflicts.add("RELATION_TYPE_OWNER_EVIDENCE_CONFLICT")
        normalized_left = _exact_ref(row["left_generation_ref"], "owner_evidence.left_generation_ref")
        normalized_right = _exact_ref(row["right_generation_ref"], "owner_evidence.right_generation_ref")
        if normalized_left != dict(left):
            conflicts.add("LEFT_GENERATION_OWNER_EVIDENCE_CONFLICT")
        if normalized_right != dict(right):
            conflicts.add("RIGHT_GENERATION_OWNER_EVIDENCE_CONFLICT")
        if row["source_frontier_id"] != source_frontier_id:
            unresolved.add("SOURCE_FRONTIER_OWNER_EVIDENCE_STALE")
        if row["resolution_state"] not in {"RESOLVED", "UNRESOLVED", "CONFLICT", "UNAVAILABLE"}:
            raise RelationValidationError("owner relation evidence resolution_state is invalid")
        if row["evidence_origin"] not in {"OWNER_EXPLICIT", "MACHINE_ASSISTED", "HUMAN_REVIEW"}:
            raise RelationValidationError("owner relation evidence origin is invalid")
        for field in ("object_id", "semantic_generation", "source_path"):
            if type(row[field]) is not str or not row[field]:
                raise RelationValidationError(f"owner relation evidence {field} is malformed")
        digest = row["content_sha256"]
        if type(digest) is not str or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise RelationValidationError("owner relation evidence content_sha256 is invalid")
        refs = row["authority_refs"]
        if type(refs) is not list or any(type(ref) is not str or not ref for ref in refs):
            raise RelationValidationError("owner relation evidence authority_refs are invalid")
        if len(refs) != len(set(refs)):
            raise RelationValidationError("owner relation evidence authority_refs must be unique")
        if row["scientific_payload_copied"] is not False:
            raise RelationValidationError("owner relation evidence must remain reference-only")
        if not refs:
            unresolved.add("OWNER_RELATION_AUTHORITY_REFERENCE_MISSING")
        if str(row["source_path"]).casefold().startswith(_NON_OWNER_PROVENANCE_PREFIXES):
            conflicts.add("OWNER_PROVENANCE_CLASS_CONFLICT")
        item = dict(row)
        item["authority_refs"] = sorted(refs)
        item["left_generation_ref"] = normalized_left
        item["right_generation_ref"] = normalized_right
        normalized.append(item)
    normalized.sort(key=canonical_sha256)
    if any(item["resolution_state"] == "CONFLICT" for item in normalized):
        conflicts.add("STATE_OWNER_CONFLICT")
    if any(item["resolution_state"] != "RESOLVED" for item in normalized):
        unresolved.add("CURRENTNESS_UNRESOLVED")
    identities = [canonical_sha256(item) for item in normalized]
    if len(normalized) != 1 or len(set(identities)) != 1:
        conflicts.add("STATE_OWNER_CONFLICT")
    origins = {item["evidence_origin"] for item in normalized}
    if "MACHINE_ASSISTED" in origins and len(origins) > 1:
        conflicts.add("OWNER_PROVENANCE_CLASS_CONFLICT")
    if conflicts:
        return "CONFLICT", normalized, sorted(conflicts | unresolved)
    if unresolved:
        return "UNRESOLVED", normalized, sorted(unresolved)
    return "RESOLVED", normalized[:1], []


def _control(object_type: str, source_frontier_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if type(source_frontier_id) is not str or not source_frontier_id.startswith("p2cti:frontier:"):
        raise RelationValidationError("exact source_frontier_id is required")
    identity = {"payload": dict(payload)}
    body = {
        "schema_family": "P2CTI_CONTROL",
        "schema_version": "0.1",
        "object_type": object_type,
        "record_id": control_record_id(
            object_type=object_type, source_frontier=source_frontier_id, identity_payload=identity
        ),
        "source_frontier_id": source_frontier_id,
        "payload": dict(payload),
        "authority_effect": "NONE",
    }
    return {**body, "content_sha256": canonical_sha256(body)}


def build_relation(
    *, relation_type: str, left_generation_ref: Mapping[str, Any],
    right_generation_ref: Mapping[str, Any], qualification: str,
    source_frontier_id: str, evidence_refs: Sequence[str],
    source_relation_ref: Mapping[str, Any] | None = None,
    owner_relation_evidence: Sequence[Mapping[str, Any]] = (),
    current_generation_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if relation_type not in _RELATION_TYPES:
        raise RelationValidationError(f"unknown relation_type: {relation_type}")
    if qualification not in _QUALIFICATIONS:
        raise RelationValidationError(f"unknown qualification: {qualification}")
    if not isinstance(evidence_refs, Sequence) or isinstance(evidence_refs, (str, bytes)):
        raise RelationValidationError("evidence_refs must be a sequence")
    if any(type(ref) is not str or not ref for ref in evidence_refs) or len(set(evidence_refs)) != len(evidence_refs):
        raise RelationValidationError("evidence_refs must be unique non-empty strings")
    left = _exact_ref(left_generation_ref, "left_generation_ref")
    right = _exact_ref(right_generation_ref, "right_generation_ref")
    if left == right:
        raise RelationValidationError("a relation requires two distinct exact semantic generations")
    family = _RELATION_TYPES[relation_type]
    current_refs = _current_refs_from_bundle(current_generation_bundle, source_frontier_id)
    endpoints_current = all(canonical_sha256(ref) in current_refs for ref in (left, right))
    if source_relation_ref is None:
        source_ref = None
    elif not isinstance(source_relation_ref, Mapping):
        raise RelationValidationError("source_relation_ref must be an exact typed owner record")
    else:
        source_ref = _source_relation_reference(source_relation_ref)
    evidence_state, typed_evidence, evidence_warnings = _owner_relation_evidence(
        owner_relation_evidence, relation_type=relation_type, left=left, right=right,
        source_frontier_id=source_frontier_id,
    )
    if source_ref is not None:
        if len(typed_evidence) != 1:
            pass
        elif source_ref != {
            field: typed_evidence[0][field]
            for field in (
                "owner_programme", "object_type", "object_id", "semantic_generation",
                "source_path", "content_sha256", "authority_refs", "scientific_payload_copied",
            )
        }:
            evidence_state = "CONFLICT"
            evidence_warnings = sorted(set([*evidence_warnings, "SOURCE_RELATION_OWNER_EVIDENCE_CONFLICT"]))
    if any(item.get("evidence_origin") == "MACHINE_ASSISTED" for item in typed_evidence):
        if qualification != "PROPOSED_MACHINE_ASSISTED":
            raise RelationValidationError("machine evidence cannot be relabelled as deterministic or reviewed")
    if qualification == "SOURCE_EXPLICIT_DETERMINISTIC" and source_ref is None:
        raise RelationValidationError("source-explicit qualification requires an exact owner source reference")
    if (
        qualification == "SOURCE_EXPLICIT_DETERMINISTIC"
        and typed_evidence
        and typed_evidence[0]["evidence_origin"] != "OWNER_EXPLICIT"
    ):
        raise RelationValidationError("source-explicit auto-admission requires OWNER_EXPLICIT evidence")
    if not endpoints_current and qualification in _REVIEWED | {"SOURCE_EXPLICIT_DETERMINISTIC"}:
        evidence_state = "UNRESOLVED"
        evidence_warnings = sorted(set([*evidence_warnings, "STALE_SEMANTIC_GENERATION_REASSESSMENT_REQUIRED"]))
    if qualification == "PROPOSED_MACHINE_ASSISTED":
        disposition = "PROPOSED_REVIEW_REQUIRED"
    elif qualification == "CONFLICT":
        disposition = "CONFLICT_PRESERVED"
    elif qualification == "AMBIGUOUS":
        disposition = "AMBIGUITY_PRESERVED"
    elif evidence_state == "CONFLICT":
        disposition = "CONFLICT_PRESERVED"
    elif evidence_state != "RESOLVED" or not endpoints_current:
        disposition = "PROPOSED_REVIEW_REQUIRED"
    elif relation_type in _SEMANTIC_REVIEW_TYPES:
        disposition = "ADMITTED_REVIEWED" if qualification in _REVIEWED else "PROPOSED_REVIEW_REQUIRED"
    elif qualification == "SOURCE_EXPLICIT_DETERMINISTIC" and _FAMILIES[family]["semantic_auto_admission"] is True:
        disposition = "ADMITTED_SOURCE_EXPLICIT"
    elif qualification in _REVIEWED:
        disposition = "ADMITTED_REVIEWED"
    else:
        disposition = "PROPOSED_REVIEW_REQUIRED"
    relation_identity = {
        "relation_type": relation_type,
        "left_generation_ref": left,
        "right_generation_ref": right,
    }
    relation_id = f"p2cti:relation:{canonical_sha256(relation_identity)}"
    payload = {
        "relation_id": relation_id,
        "relation_family": family,
        "relation_type": relation_type,
        "left_generation_ref": left,
        "right_generation_ref": right,
        "qualification": qualification,
        "evidence_refs": sorted(evidence_refs),
        "source_relation_ref": source_ref,
        "owner_relation_evidence": typed_evidence,
        "owner_evidence_state": evidence_state,
        "current_generation_binding": "CURRENT" if endpoints_current else "REASSESSMENT_REQUIRED",
        "warnings": sorted(set(evidence_warnings)),
        "admission_disposition": disposition,
        "identity_collapse_allowed": False,
        "semantic_promotion": False,
        "machine_similarity_authority": "ADVISORY_ONLY",
    }
    return _control("THEORY_RELATION", source_frontier_id, payload)


def build_duplicate_screen(
    *, subject_refs: Sequence[Mapping[str, Any]], source_frontier_id: str,
    method_class: str, machine_signal: str | None = None,
) -> dict[str, Any]:
    if type(subject_refs) is not list and not isinstance(subject_refs, tuple):
        raise RelationValidationError("subject_refs must be an exact pair")
    if len(subject_refs) != 2:
        raise RelationValidationError("duplicate screen requires exactly two subjects")
    refs = [_exact_ref(item, "subject_ref") for item in subject_refs]
    if method_class not in {"EXACT_SOURCE_IDENTITY", "DETERMINISTIC_RULE", "MACHINE_RETRIEVAL", "LLM_RETRIEVAL"}:
        raise RelationValidationError("unknown duplicate method_class")
    exact = refs[0] == refs[1]
    if exact:
        result, qualification = "EXACT_SAME_SOURCE_GENERATION", "SOURCE_EXPLICIT_DETERMINISTIC"
    elif method_class in {"MACHINE_RETRIEVAL", "LLM_RETRIEVAL"}:
        if type(machine_signal) is not str or not machine_signal:
            raise RelationValidationError("machine retrieval requires a non-empty advisory signal")
        result, qualification = "NEAR_DUPLICATE_PROPOSED", "PROPOSED_MACHINE_ASSISTED"
    else:
        result, qualification = "DISTINCT_UNLESS_REVIEWED", "AMBIGUOUS"
    screen_id = f"p2cti:duplicate_screen:{canonical_sha256({'subject_refs': refs, 'method_class': method_class})}"
    return _control("DUPLICATE_SCREEN", source_frontier_id, {
        "screen_id": screen_id,
        "subject_refs": refs,
        "screen_result": result,
        "method_class": method_class,
        "authority_class": "ADVISORY_ONLY",
        "qualification": qualification,
        "machine_signal": machine_signal,
        "identity_collapse_allowed": False,
        "semantic_promotion": False,
    })


def preserve_relation_ambiguity(
    *, subject_refs: Sequence[Mapping[str, Any]], competing_relation_refs: Sequence[str],
    source_frontier_id: str,
) -> dict[str, Any]:
    refs = [_exact_ref(item, "subject_ref") for item in subject_refs]
    if len(refs) < 2 or not competing_relation_refs:
        raise RelationValidationError("ambiguity requires subjects and competing relation refs")
    payload = {
        "ambiguity_id": f"p2cti:relation_ambiguity:{canonical_sha256({'subjects': refs, 'relations': sorted(competing_relation_refs)})}",
        "subject_refs": refs,
        "competing_relation_refs": sorted(set(competing_relation_refs)),
        "review_state": "UNRESOLVED",
        "identity_collapse_allowed": False,
    }
    return _control("RELATION_AMBIGUITY", source_frontier_id, payload)


def preserve_relation_conflict(
    *, subject_refs: Sequence[Mapping[str, Any]], accepted_relation_refs: Sequence[str],
    source_frontier_id: str,
) -> dict[str, Any]:
    refs = [_exact_ref(item, "subject_ref") for item in subject_refs]
    if len(refs) < 2 or len(set(accepted_relation_refs)) < 2:
        raise RelationValidationError("conflict requires subjects and at least two accepted relations")
    payload = {
        "conflict_id": f"p2cti:relation_conflict:{canonical_sha256({'subjects': refs, 'relations': sorted(accepted_relation_refs)})}",
        "subject_refs": refs,
        "accepted_relation_refs": sorted(set(accepted_relation_refs)),
        "blocking_effect": "RELATION_DECISION_BLOCKED",
        "review_state": "CONFLICT",
        "identity_collapse_allowed": False,
    }
    return _control("RELATION_CONFLICT", source_frontier_id, payload)
