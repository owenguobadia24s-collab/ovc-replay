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


def _exact_ref(raw: Mapping[str, Any], name: str) -> dict[str, str]:
    if not isinstance(raw, Mapping) or set(raw) != _REF_FIELDS:
        raise RelationValidationError(f"{name} must use the exact semantic-generation reference shape")
    if any(type(raw[field]) is not str or not raw[field] for field in _REF_FIELDS):
        raise RelationValidationError(f"{name} values must be non-empty strings")
    digest = raw["content_sha256"]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise RelationValidationError(f"{name} content_sha256 is invalid")
    return {field: raw[field] for field in sorted(_REF_FIELDS)}


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
    source_relation_ref: str | None = None,
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
    source_explicit = type(source_relation_ref) is str and bool(source_relation_ref)
    if qualification == "SOURCE_EXPLICIT_DETERMINISTIC" and not source_explicit:
        raise RelationValidationError("source-explicit qualification requires source_relation_ref")
    if qualification == "PROPOSED_MACHINE_ASSISTED":
        disposition = "PROPOSED_REVIEW_REQUIRED"
    elif qualification == "AMBIGUOUS":
        disposition = "AMBIGUITY_PRESERVED"
    elif qualification == "CONFLICT":
        disposition = "CONFLICT_PRESERVED"
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
        "source_relation_ref": source_relation_ref,
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
