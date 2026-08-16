from __future__ import annotations

import re
from copy import deepcopy
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from .canonical import canonicalize_graph, graph_logical_hash


class AtlasContractError(ValueError):
    """Raised when an Atlas graph violates the frozen Core constitution."""


GRAPH_SCHEMA = "ovc-system-atlas-graph/v1"
AUTHORITY_EFFECT = "NONE_READ_ONLY_DERIVED_GRAPH"
OBJECT_ARRAYS = {
    "entities": "entity_id",
    "relationships": "relationship_id",
    "assertions": "assertion_id",
    "evidence_references": "evidence_id",
    "conflicts": "conflict_id",
}
STATE_PLANES = (
    "lifecycle",
    "implementation",
    "availability",
    "assurance",
    "authority",
    "activation",
    "canonicality",
    "currentness",
    "health",
)
STATE_VALUES = {
    "lifecycle": {"PLANNED", "CURRENT_GENERATION", "SUPERSEDED", "HISTORICAL"},
    "implementation": {"NOT_IMPLEMENTED", "IMPLEMENTED"},
    "availability": {"AVAILABLE", "UNAVAILABLE", "UNKNOWN"},
    "assurance": {"UNQUALIFIED", "CONFORMANT", "DEGRADED"},
    "authority": {"GRANTED", "DENIED", "RESERVED", "UNKNOWN"},
    "activation": {"INACTIVE", "SHADOW", "ACTIVE"},
    "canonicality": {"NONCANONICAL", "CANONICAL", "PUBLISHED"},
    "currentness": {"CURRENT", "STALE", "HISTORICAL", "UNKNOWN"},
    "health": {"HEALTHY", "DEGRADED", "FAILED"},
}
MANDATORY_HIGH_RISK_PREDICATES = {"OWNS", "ACTIVE", "AUTHORISED", "CURRENT", "CANONICAL", "PUBLISHED"}
_TYPED_ID = re.compile(r"^(?:ovc|repo|git|atlas|synthetic):[A-Za-z0-9._:/@+-]+$")
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AtlasContractError(code)


def _validate_scope(scope: Any, *, owner: str) -> None:
    _require(isinstance(scope, Mapping), f"ATLAS_SCOPE_REQUIRED:{owner}")
    _require(isinstance(scope.get("scope_id"), str) and bool(scope["scope_id"]), f"ATLAS_SCOPE_ID_REQUIRED:{owner}")
    _require(isinstance(scope.get("dimensions"), Mapping), f"ATLAS_SCOPE_DIMENSIONS_REQUIRED:{owner}")


def _validate_state_planes(state: Any, *, entity_id: str) -> None:
    _require(isinstance(state, Mapping), f"ATLAS_STATE_PLANES_REQUIRED:{entity_id}")
    _require(set(state) == set(STATE_PLANES), f"ATLAS_STATE_PLANES_INCOMPLETE:{entity_id}")
    for plane in STATE_PLANES:
        _require(state[plane] in STATE_VALUES[plane], f"ATLAS_STATE_VALUE_INVALID:{entity_id}:{plane}")


def _validate_registry_bundle(registries: Mapping[str, Any]) -> None:
    required = {"ontology", "predicate_authority", "visibility", "extractor", "resolver", "query_policy", "visual_grammar"}
    _require(set(registries) == required, "ATLAS_REGISTRY_BUNDLE_INCOMPLETE")
    for registry_name, registry in registries.items():
        _require(isinstance(registry, Mapping), f"ATLAS_REGISTRY_INVALID:{registry_name}")
        _require(registry.get("authority_effect") == "NONE", f"ATLAS_REGISTRY_AUTHORITY_EFFECT:{registry_name}")
        _require(registry.get("status") in {"FROZEN_ATLAS_G1", "SKELETON_ATLAS_G1", "FROZEN_ATLAS_G3"}, f"ATLAS_REGISTRY_STATUS:{registry_name}")
    predicates = registries["predicate_authority"].get("predicates", [])
    registered = {row.get("predicate") for row in predicates if isinstance(row, Mapping)}
    _require(MANDATORY_HIGH_RISK_PREDICATES <= registered, "ATLAS_HIGH_RISK_PREDICATE_POLICY_MISSING")


def validate_system_graph(graph: Mapping[str, Any], registries: Mapping[str, Any]) -> dict[str, Any]:
    _validate_registry_bundle(registries)
    _require(graph.get("schema") == GRAPH_SCHEMA, "ATLAS_GRAPH_SCHEMA_INVALID")
    _require(graph.get("authority_effect") == AUTHORITY_EFFECT, "ATLAS_GRAPH_AUTHORITY_EFFECT_INVALID")
    _require(graph.get("court_record_status") in {"SYNTHETIC_NOT_COURT_RECORD", "EXACT_GIT_TREE"}, "ATLAS_COURT_RECORD_STATUS_INVALID")

    generation = graph.get("generation")
    _require(isinstance(generation, Mapping), "ATLAS_GENERATION_REQUIRED")
    _require(_TYPED_ID.fullmatch(str(generation.get("generation_id", ""))) is not None, "ATLAS_GENERATION_ID_INVALID")
    _require(_SHA40.fullmatch(str(generation.get("repository_commit", ""))) is not None, "ATLAS_GENERATION_COMMIT_INVALID")
    _require(_SHA40.fullmatch(str(generation.get("repository_tree", ""))) is not None, "ATLAS_GENERATION_TREE_INVALID")
    _require(generation.get("authority_effect") == "NONE", "ATLAS_GENERATION_AUTHORITY_EFFECT_INVALID")

    object_ids: dict[str, set[str]] = {}
    for array_name, identity_key in OBJECT_ARRAYS.items():
        rows = graph.get(array_name)
        _require(isinstance(rows, list), f"ATLAS_OBJECT_ARRAY_REQUIRED:{array_name}")
        identities = [row.get(identity_key) for row in rows if isinstance(row, Mapping)]
        _require(len(identities) == len(rows), f"ATLAS_OBJECT_ROW_INVALID:{array_name}")
        _require(all(isinstance(item, str) and _TYPED_ID.fullmatch(item) for item in identities), f"ATLAS_OBJECT_ID_INVALID:{array_name}")
        _require(len(set(identities)) == len(identities), f"ATLAS_OBJECT_ID_DUPLICATE:{array_name}")
        object_ids[array_name] = set(identities)

    entity_ids = object_ids["entities"]
    evidence_ids = object_ids["evidence_references"]
    assertion_ids = object_ids["assertions"]
    ontology = registries["ontology"]
    entity_types = set(ontology.get("entity_types", []))
    predicate_families = {
        predicate: family
        for family, predicates in ontology.get("relationship_families", {}).items()
        for predicate in predicates
    }

    for entity in graph["entities"]:
        entity_id = entity["entity_id"]
        _require(entity.get("entity_type") in entity_types, f"ATLAS_ENTITY_TYPE_INVALID:{entity_id}")
        _validate_scope(entity.get("scope"), owner=entity_id)
        _validate_state_planes(entity.get("state_planes"), entity_id=entity_id)
        _require(isinstance(entity.get("aliases"), list), f"ATLAS_ENTITY_ALIASES_INVALID:{entity_id}")
        _require(entity.get("visibility_partition") in set(registries["visibility"].get("partitions", {})), f"ATLAS_VISIBILITY_PARTITION_INVALID:{entity_id}")
        refs = entity.get("evidence_refs")
        _require(isinstance(refs, list) and bool(refs) and set(refs) <= evidence_ids, f"ATLAS_ENTITY_EVIDENCE_INVALID:{entity_id}")

    for evidence in graph["evidence_references"]:
        evidence_id = evidence["evidence_id"]
        _require(evidence.get("evidence_class") in set(ontology.get("evidence_classes", [])), f"ATLAS_EVIDENCE_CLASS_INVALID:{evidence_id}")
        _require(evidence.get("visibility_partition") in set(registries["visibility"].get("partitions", {})), f"ATLAS_EVIDENCE_VISIBILITY_INVALID:{evidence_id}")
        blob_sha = evidence.get("source_blob_sha")
        _require(blob_sha is None or _SHA40.fullmatch(str(blob_sha)) is not None, f"ATLAS_EVIDENCE_BLOB_INVALID:{evidence_id}")
        source_path = evidence.get("source_path")
        if source_path is not None:
            normalized_path = str(source_path).replace("\\", "/")
            parsed_path = PurePosixPath(normalized_path)
            _require(not parsed_path.is_absolute() and ".." not in parsed_path.parts and ":" not in parsed_path.parts[0], f"ATLAS_EVIDENCE_PATH_INVALID:{evidence_id}")

    for relationship in graph["relationships"]:
        relationship_id = relationship["relationship_id"]
        _require(relationship.get("subject_id") in entity_ids and relationship.get("object_id") in entity_ids, f"ATLAS_RELATIONSHIP_ENDPOINT_INVALID:{relationship_id}")
        predicate = relationship.get("predicate")
        _require(predicate in predicate_families, f"ATLAS_RELATIONSHIP_PREDICATE_INVALID:{relationship_id}")
        _require(relationship.get("family") == predicate_families[predicate], f"ATLAS_RELATIONSHIP_FAMILY_INVALID:{relationship_id}")
        _require(relationship.get("resolution_status") in {"RECONCILED", "DECLARED_ONLY", "OBSERVED_ONLY", "FORBIDDEN_OBSERVED", "CONFLICTING", "UNRESOLVED"}, f"ATLAS_RELATIONSHIP_STATUS_INVALID:{relationship_id}")
        _require(relationship.get("authority_effect") == "NONE", f"ATLAS_RELATIONSHIP_AUTHORITY_EFFECT:{relationship_id}")
        _validate_scope(relationship.get("scope"), owner=relationship_id)
        refs = relationship.get("evidence_refs")
        _require(isinstance(refs, list) and bool(refs) and set(refs) <= evidence_ids, f"ATLAS_RELATIONSHIP_EVIDENCE_INVALID:{relationship_id}")

    for assertion in graph["assertions"]:
        assertion_id = assertion["assertion_id"]
        _require(assertion.get("subject_id") in entity_ids, f"ATLAS_ASSERTION_SUBJECT_INVALID:{assertion_id}")
        _require(assertion.get("authority_effect") == "NONE", f"ATLAS_ASSERTION_AUTHORITY_EFFECT:{assertion_id}")
        _require(assertion.get("status") in {"CANONICAL", "CANDIDATE", "DENIED", "RESERVED", "UNRESOLVED", "HISTORICAL"}, f"ATLAS_ASSERTION_STATUS_INVALID:{assertion_id}")
        _validate_scope(assertion.get("scope"), owner=assertion_id)
        refs = assertion.get("evidence_refs")
        _require(isinstance(refs, list) and bool(refs) and set(refs) <= evidence_ids, f"ATLAS_ASSERTION_EVIDENCE_INVALID:{assertion_id}")

    for conflict in graph["conflicts"]:
        conflict_id = conflict["conflict_id"]
        _require(conflict.get("subject_id") in entity_ids, f"ATLAS_CONFLICT_SUBJECT_INVALID:{conflict_id}")
        _require(conflict.get("status") in {"OPEN", "RESOLVED", "HISTORICAL"}, f"ATLAS_CONFLICT_STATUS_INVALID:{conflict_id}")
        competing = conflict.get("competing_assertion_ids")
        _require(isinstance(competing, list) and len(competing) >= 2 and set(competing) <= assertion_ids, f"ATLAS_CONFLICT_ASSERTIONS_INVALID:{conflict_id}")
        refs = conflict.get("evidence_refs")
        _require(isinstance(refs, list) and bool(refs) and set(refs) <= evidence_ids, f"ATLAS_CONFLICT_EVIDENCE_INVALID:{conflict_id}")
        _require(conflict.get("authority_effect") == "NONE", f"ATLAS_CONFLICT_AUTHORITY_EFFECT:{conflict_id}")

    expected_hash = graph_logical_hash(graph)
    _require(graph.get("graph_logical_hash") == expected_hash, "ATLAS_GRAPH_LOGICAL_HASH_MISMATCH")
    return {
        "status": "PASS",
        "graph_logical_hash": expected_hash,
        "counts": {name: len(graph[name]) for name in OBJECT_ARRAYS},
        "authority_effect": "NONE_VALIDATION_ONLY",
    }


def build_system_graph(
    *,
    graph_id: str,
    generation: Mapping[str, Any],
    entities: Iterable[Mapping[str, Any]],
    relationships: Iterable[Mapping[str, Any]],
    assertions: Iterable[Mapping[str, Any]],
    evidence_references: Iterable[Mapping[str, Any]],
    conflicts: Iterable[Mapping[str, Any]],
    registry_versions: Mapping[str, str],
    completeness_profile: str,
    court_record_status: str,
    registries: Mapping[str, Any],
) -> dict[str, Any]:
    graph = {
        "schema": GRAPH_SCHEMA,
        "graph_id": graph_id,
        "generation": deepcopy(dict(generation)),
        "registry_versions": dict(registry_versions),
        "completeness_profile": completeness_profile,
        "court_record_status": court_record_status,
        "entities": [deepcopy(dict(row)) for row in entities],
        "relationships": [deepcopy(dict(row)) for row in relationships],
        "assertions": [deepcopy(dict(row)) for row in assertions],
        "evidence_references": [deepcopy(dict(row)) for row in evidence_references],
        "conflicts": [deepcopy(dict(row)) for row in conflicts],
        "authority_effect": AUTHORITY_EFFECT,
    }
    graph = canonicalize_graph(graph)
    graph["graph_logical_hash"] = graph_logical_hash(graph)
    validate_system_graph(graph, registries)
    return graph
