from __future__ import annotations

import json
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .canonical import canonical_sha256
from .generation import FAMILY_ID_KEYS, PARTITIONS, GenerationBundle, verify_generation_bundle


class AtlasQueryError(ValueError):
    """Raised when a query would be ambiguous, unbounded, or visibility widening."""


QUERY_FAMILIES = (
    "SEARCH",
    "TRACE",
    "DEPENDENCY",
    "IMPACT",
    "EXPLAIN",
    "AUTHORITY",
    "OWNERSHIP",
    "WHY_BLOCKED",
    "HISTORY",
    "DIFF",
)
DEPENDENCY_CLASS = {
    "REQUIRES": "REQUIRED",
    "PREREQUISITE_OF": "REQUIRED",
    "BLOCKED_BY": "REQUIRED",
    "OPTIONALLY_USES": "OPTIONAL",
}
IMPACT_CLASS = {
    "OWNERSHIP": "AUTHORITY_REVIEW",
    "AUTHORITY": "AUTHORITY_REVIEW",
    "ASSURANCE": "ASSURANCE",
    "IMPLEMENTATION": "DIRECT_IMPLEMENTATION",
    "DATA": "DIRECT_SEMANTIC",
}


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AtlasQueryError(code)


def _rows(raw: bytes) -> list[dict[str, Any]]:
    return [json.loads(line) for line in raw.splitlines()]


def _allowed_partitions(values: Iterable[str]) -> tuple[str, ...]:
    allowed = tuple(sorted(set(values), key=PARTITIONS.index))
    _require(bool(allowed), "ATLAS_QUERY_VISIBILITY_REQUIRED")
    _require(all(value in PARTITIONS for value in allowed), "ATLAS_QUERY_VISIBILITY_UNKNOWN")
    return allowed


@dataclass(frozen=True)
class QueryView:
    root_hash: str
    root_manifest: Mapping[str, Any]
    allowed_partitions: tuple[str, ...]
    families: Mapping[str, tuple[Mapping[str, Any], ...]]

    @property
    def entities(self) -> dict[str, Mapping[str, Any]]:
        return {row["entity_id"]: row for row in self.families["entities"]}

    @property
    def relationships(self) -> tuple[Mapping[str, Any], ...]:
        return self.families["relationships"]


def _scan_view(bundle: GenerationBundle, allowed_partitions: Iterable[str]) -> QueryView:
    verify_generation_bundle(bundle)
    allowed = _allowed_partitions(allowed_partitions)
    families: dict[str, tuple[Mapping[str, Any], ...]] = {}
    for family, identity_key in FAMILY_ID_KEYS.items():
        collected = [
            row
            for partition in allowed
            for row in _rows(bundle.files[f"partitions/{partition}/{family}.jsonl"])
        ]
        collected.sort(key=lambda row: row[identity_key])
        families[family] = tuple(collected)
    return QueryView(bundle.root_hash, bundle.root_manifest, allowed, families)


class AtlasQueryIndex:
    """Disposable partitioned index with no semantic or authority standing."""

    def __init__(self, bundle: GenerationBundle):
        verify_generation_bundle(bundle)
        self.root_hash = bundle.root_hash
        self.root_manifest = deepcopy(bundle.root_manifest)
        self._partition_rows = {
            partition: {
                family: tuple(_rows(bundle.files[f"partitions/{partition}/{family}.jsonl"]))
                for family in FAMILY_ID_KEYS
            }
            for partition in PARTITIONS
        }

    def view(self, allowed_partitions: Iterable[str]) -> QueryView:
        allowed = _allowed_partitions(allowed_partitions)
        families: dict[str, tuple[Mapping[str, Any], ...]] = {}
        for family, identity_key in FAMILY_ID_KEYS.items():
            collected = [row for partition in allowed for row in self._partition_rows[partition][family]]
            collected.sort(key=lambda row: row[identity_key])
            families[family] = tuple(collected)
        return QueryView(self.root_hash, self.root_manifest, allowed, families)


def _adjacency(view: QueryView) -> dict[str, list[Mapping[str, Any]]]:
    result: dict[str, list[Mapping[str, Any]]] = {}
    for edge in view.relationships:
        result.setdefault(edge["subject_id"], []).append(edge)
        result.setdefault(edge["object_id"], []).append(edge)
    for rows in result.values():
        rows.sort(key=lambda row: row["relationship_id"])
    return result


def _search(view: QueryView, query: Mapping[str, Any]) -> dict[str, Any]:
    term = str(query.get("term", "")).strip().casefold()
    _require(bool(term), "ATLAS_SEARCH_TERM_REQUIRED")
    matches = []
    for entity in view.families["entities"]:
        entity_id = entity["entity_id"].casefold()
        label = str(entity.get("label", "")).casefold()
        aliases = [str(alias).casefold() for alias in entity.get("aliases", [])]
        if term == entity_id:
            rank, reason = 0, "EXACT_ID"
        elif term == label:
            rank, reason = 1, "EXACT_LABEL"
        elif term in aliases:
            rank, reason = 2, "EXACT_ALIAS"
        elif entity_id.startswith(term) or label.startswith(term) or any(alias.startswith(term) for alias in aliases):
            rank, reason = 3, "PREFIX"
        elif term in entity_id or term in label or any(term in alias for alias in aliases):
            rank, reason = 4, "SUBSTRING"
        else:
            continue
        matches.append({"entity": deepcopy(entity), "match_class": reason, "rank": rank})
    matches.sort(key=lambda row: (row["rank"], row["entity"]["entity_id"]))
    return {"matches": matches}


def _trace(view: QueryView, query: Mapping[str, Any]) -> dict[str, Any]:
    start_id = str(query.get("start_id", ""))
    _require(start_id in view.entities, "ATLAS_TRACE_START_NOT_VISIBLE")
    max_depth = query.get("max_depth")
    _require(isinstance(max_depth, int) and 0 <= max_depth <= 8, "ATLAS_TRACE_DEPTH_INVALID")
    direction = str(query.get("direction", "BOTH"))
    _require(direction in {"OUTBOUND", "INBOUND", "BOTH"}, "ATLAS_TRACE_DIRECTION_INVALID")
    predicates = set(query.get("predicates", []))
    families = set(query.get("relationship_families", []))
    adjacency = _adjacency(view)
    queue = deque([(start_id, 0, [])])
    best_depth = {start_id: 0}
    paths = []
    cycles = []
    while queue:
        entity_id, depth, path = queue.popleft()
        if depth == max_depth:
            continue
        for edge in adjacency.get(entity_id, []):
            if predicates and edge["predicate"] not in predicates:
                continue
            if families and edge["family"] not in families:
                continue
            outbound = edge["subject_id"] == entity_id
            if direction == "OUTBOUND" and not outbound:
                continue
            if direction == "INBOUND" and outbound:
                continue
            target = edge["object_id"] if outbound else edge["subject_id"]
            if target not in view.entities:
                continue
            step = {
                "relationship_id": edge["relationship_id"],
                "from_id": entity_id,
                "to_id": target,
                "predicate": edge["predicate"],
                "family": edge["family"],
                "direction": "OUTBOUND" if outbound else "INBOUND",
            }
            next_path = [*path, step]
            path_nodes = {start_id, *(item["to_id"] for item in path)}
            if target in path_nodes:
                cycles.append({"at_id": target, "path": next_path})
                continue
            next_depth = depth + 1
            if target in best_depth and best_depth[target] <= next_depth:
                continue
            best_depth[target] = next_depth
            paths.append({"target_id": target, "depth": next_depth, "path": next_path})
            queue.append((target, next_depth, next_path))
    paths.sort(key=lambda row: (row["depth"], row["target_id"], canonical_sha256(row["path"])))
    cycles.sort(key=lambda row: (row["at_id"], canonical_sha256(row["path"])))
    return {"start_id": start_id, "paths": paths, "cycles": cycles, "bounded_depth": max_depth}


def _dependency(view: QueryView, query: Mapping[str, Any]) -> dict[str, Any]:
    target_id = str(query.get("entity_id", ""))
    _require(target_id in view.entities, "ATLAS_DEPENDENCY_ENTITY_NOT_VISIBLE")
    rows = []
    for edge in view.relationships:
        if edge["subject_id"] != target_id and edge["object_id"] != target_id:
            continue
        classification = DEPENDENCY_CLASS.get(edge["predicate"])
        if classification is None:
            classification = "TECHNICAL_ONLY" if edge["family"] in {"DATA", "IMPLEMENTATION"} else "UNRESOLVED"
        rows.append({
            "relationship_id": edge["relationship_id"],
            "subject_id": edge["subject_id"],
            "object_id": edge["object_id"],
            "predicate": edge["predicate"],
            "dependency_class": classification,
            "resolution_status": edge["resolution_status"],
        })
    rows.sort(key=lambda row: (row["dependency_class"], row["relationship_id"]))
    return {"entity_id": target_id, "dependencies": rows}


def _impact(view: QueryView, query: Mapping[str, Any]) -> dict[str, Any]:
    changed = sorted(set(query.get("changed_entity_ids", [])))
    _require(bool(changed) and all(entity_id in view.entities for entity_id in changed), "ATLAS_IMPACT_SURFACE_NOT_VISIBLE")
    max_depth = query.get("max_depth", 3)
    _require(isinstance(max_depth, int) and 1 <= max_depth <= 8, "ATLAS_IMPACT_DEPTH_INVALID")
    adjacency = _adjacency(view)
    queue = deque((entity_id, 0) for entity_id in changed)
    seen = set(changed)
    impacts = []
    while queue:
        entity_id, depth = queue.popleft()
        if depth == max_depth:
            continue
        for edge in adjacency.get(entity_id, []):
            target = edge["object_id"] if edge["subject_id"] == entity_id else edge["subject_id"]
            if target not in view.entities or target in seen:
                continue
            next_depth = depth + 1
            impact_class = IMPACT_CLASS.get(edge["family"], "TRANSITIVE" if next_depth > 1 else "POSSIBLE")
            impacts.append({
                "entity_id": target,
                "source_id": entity_id,
                "relationship_id": edge["relationship_id"],
                "depth": next_depth,
                "impact_class": impact_class if next_depth == 1 else "TRANSITIVE",
            })
            seen.add(target)
            queue.append((target, next_depth))
    impacts.sort(key=lambda row: (row["depth"], row["entity_id"], row["relationship_id"]))
    return {"changed_entity_ids": changed, "impacts": impacts}


def _explain(view: QueryView, query: Mapping[str, Any]) -> dict[str, Any]:
    object_id = str(query.get("object_id", ""))
    target = None
    family_name = None
    for family, identity_key in FAMILY_ID_KEYS.items():
        for row in view.families[family]:
            if row[identity_key] == object_id:
                target, family_name = row, family
                break
        if target is not None:
            break
    _require(target is not None, "ATLAS_EXPLAIN_OBJECT_NOT_VISIBLE")
    evidence_by_id = {row["evidence_id"]: row for row in view.families["evidence_references"]}
    evidence = [deepcopy(evidence_by_id[ref]) for ref in target.get("evidence_refs", []) if ref in evidence_by_id]
    evidence.sort(key=lambda row: row["evidence_id"])
    return {
        "object_family": family_name,
        "object": deepcopy(target),
        "evidence_chain": evidence,
        "unresolved_evidence_refs": sorted(set(target.get("evidence_refs", [])) - set(evidence_by_id)),
    }


def _predicate_projection(view: QueryView, predicates: set[str], relationship_family: str) -> dict[str, Any]:
    assertions = [deepcopy(row) for row in view.families["assertions"] if row["predicate"] in predicates]
    relationships = [deepcopy(row) for row in view.relationships if row["family"] == relationship_family]
    assertions.sort(key=lambda row: row["assertion_id"])
    relationships.sort(key=lambda row: row["relationship_id"])
    return {"assertions": assertions, "relationships": relationships}


def _why_blocked(view: QueryView, query: Mapping[str, Any]) -> dict[str, Any]:
    entity_id = str(query.get("entity_id", ""))
    _require(entity_id in view.entities, "ATLAS_BLOCKER_ENTITY_NOT_VISIBLE")
    frontier = []
    for edge in view.relationships:
        if edge["subject_id"] != entity_id or edge["predicate"] not in {"BLOCKED_BY", "REQUIRES"}:
            continue
        blocker = view.entities.get(edge["object_id"])
        if blocker is None:
            continue
        state = blocker["state_planes"]
        blocked = edge["predicate"] == "BLOCKED_BY" or state["availability"] != "AVAILABLE" or state["health"] != "HEALTHY"
        if blocked:
            frontier.append({
                "blocker_id": blocker["entity_id"],
                "relationship_id": edge["relationship_id"],
                "predicate": edge["predicate"],
                "state_planes": deepcopy(state),
            })
    frontier.sort(key=lambda row: (row["blocker_id"], row["relationship_id"]))
    conflicts = [deepcopy(row) for row in view.families["conflicts"] if row["subject_id"] == entity_id and row["status"] == "OPEN"]
    conflicts.sort(key=lambda row: row["conflict_id"])
    return {"entity_id": entity_id, "minimal_current_frontier": frontier, "open_conflicts": conflicts}


def _history(view: QueryView) -> dict[str, Any]:
    return {
        "root_hash": view.root_hash,
        "predecessor_root_hash": view.root_manifest["predecessor_root_hash"],
        "repository_commit": view.root_manifest["repository_commit"],
        "repository_tree": view.root_manifest["repository_tree"],
        "generation_id": view.root_manifest["generation_id"],
    }


def _diff(view: QueryView, comparison: QueryView) -> dict[str, Any]:
    _require(view.allowed_partitions == comparison.allowed_partitions, "ATLAS_DIFF_VISIBILITY_MISMATCH")
    changes: dict[str, Any] = {}
    for family, identity_key in FAMILY_ID_KEYS.items():
        current = {row[identity_key]: row for row in view.families[family]}
        prior = {row[identity_key]: row for row in comparison.families[family]}
        changes[family] = {
            "added": sorted(set(current) - set(prior)),
            "removed": sorted(set(prior) - set(current)),
            "changed": sorted(identity for identity in set(current) & set(prior) if current[identity] != prior[identity]),
        }
    return {
        "from_root_hash": comparison.root_hash,
        "to_root_hash": view.root_hash,
        "changes": changes,
    }


def _execute_view(
    view: QueryView,
    query: Mapping[str, Any],
    *,
    query_policy_version: str,
    comparison_view: QueryView | None = None,
    maximum_result_records: int | None = None,
) -> dict[str, Any]:
    family = str(query.get("family", ""))
    _require(family in QUERY_FAMILIES, "ATLAS_QUERY_FAMILY_UNKNOWN")
    if family == "SEARCH":
        result = _search(view, query)
    elif family == "TRACE":
        result = _trace(view, query)
    elif family == "DEPENDENCY":
        result = _dependency(view, query)
    elif family == "IMPACT":
        result = _impact(view, query)
    elif family == "EXPLAIN":
        result = _explain(view, query)
    elif family == "AUTHORITY":
        result = _predicate_projection(view, {"AUTHORISED", "ACTIVE"}, "AUTHORITY")
    elif family == "OWNERSHIP":
        result = _predicate_projection(view, {"OWNS", "GOVERNS"}, "OWNERSHIP")
    elif family == "WHY_BLOCKED":
        result = _why_blocked(view, query)
    elif family == "HISTORY":
        result = _history(view)
    else:
        _require(comparison_view is not None, "ATLAS_DIFF_COMPARISON_GENERATION_REQUIRED")
        result = _diff(view, comparison_view)
    record_count = sum(len(value) for value in result.values() if isinstance(value, list))
    capacity_exceeded = maximum_result_records is not None and record_count > maximum_result_records
    if capacity_exceeded:
        result = {"required_record_count": record_count, "returned_records": [], "failure": "CAPACITY_EXCEEDED"}
    body = {
        "schema": "ovc-atlas-query-result/v1",
        "family": family,
        "query": deepcopy(dict(query)),
        "graph_root_hash": view.root_hash,
        "repository_tree": view.root_manifest["repository_tree"],
        "query_policy_version": query_policy_version,
        "completeness_profile": view.root_manifest["completeness_profile"],
        "visibility_projection": list(view.allowed_partitions),
        "status": "INCOMPLETE_CAPACITY" if capacity_exceeded else "PASS",
        "exhaustive": not capacity_exceeded,
        "warnings": ["SYNTHETIC_NOT_COURT_RECORD"] if view.root_manifest["court_record_status"] != "EXACT_GIT_TREE" else [],
        "result": result,
        "authority_effect": "NONE_READ_ONLY_QUERY",
    }
    return {**body, "result_hash": canonical_sha256(body)}


def execute_reference_query(
    bundle: GenerationBundle,
    query: Mapping[str, Any],
    *,
    allowed_partitions: Iterable[str],
    query_policy_version: str = "0.1",
    comparison_bundle: GenerationBundle | None = None,
    maximum_result_records: int | None = None,
) -> dict[str, Any]:
    return _execute_view(
        _scan_view(bundle, allowed_partitions),
        query,
        query_policy_version=query_policy_version,
        comparison_view=None if comparison_bundle is None else _scan_view(comparison_bundle, allowed_partitions),
        maximum_result_records=maximum_result_records,
    )


def execute_optimized_query(
    index: AtlasQueryIndex,
    query: Mapping[str, Any],
    *,
    allowed_partitions: Iterable[str],
    query_policy_version: str = "0.1",
    comparison_index: AtlasQueryIndex | None = None,
    maximum_result_records: int | None = None,
) -> dict[str, Any]:
    return _execute_view(
        index.view(allowed_partitions),
        query,
        query_policy_version=query_policy_version,
        comparison_view=None if comparison_index is None else comparison_index.view(allowed_partitions),
        maximum_result_records=maximum_result_records,
    )


def query_equivalence_receipt(
    *,
    family: str,
    cases: Sequence[Mapping[str, Any]],
    reference_results: Sequence[Mapping[str, Any]],
    optimized_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    _require(family in QUERY_FAMILIES, "ATLAS_QUERY_FAMILY_UNKNOWN")
    _require(len(cases) == len(reference_results) == len(optimized_results), "ATLAS_QUERY_EQUIVALENCE_CASE_COUNT_MISMATCH")
    comparisons = []
    for case, reference, optimized in zip(cases, reference_results, optimized_results, strict=True):
        equal = reference == optimized
        comparisons.append({
            "case_id": str(case["case_id"]),
            "reference_result_hash": canonical_sha256(reference),
            "optimized_result_hash": canonical_sha256(optimized),
            "equal": equal,
        })
    passed = bool(comparisons) and all(row["equal"] for row in comparisons)
    body = {
        "schema": "ovc-atlas-query-equivalence-receipt/v1",
        "family": family,
        "case_comparisons": comparisons,
        "result": "PASS" if passed else "FAIL_OPTIMIZED_QUARANTINED",
        "optimized_conformance": "ADMITTED" if passed else "DENIED",
        "reference_semantics": "CONTROLLING",
        "authority_effect": "NONE_QUERY_EQUIVALENCE_ONLY",
    }
    return {**body, "receipt_hash": canonical_sha256(body)}
