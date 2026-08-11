from __future__ import annotations

from typing import Any, Iterable, Mapping

from ovc.development.identity import canonical_sha256


class KnowledgePackError(ValueError):
    """Raised when Knowledge Pack identity or dependency evidence is incomplete."""


def compile_knowledge_pack(
    *,
    knowledge_pack_id: str,
    source_requirements: Iterable[Mapping[str, Any]],
    source_records: Mapping[str, Mapping[str, Any]],
    compiled_content: Mapping[str, Any],
) -> dict[str, Any]:
    resolved_sources: list[dict[str, Any]] = []
    for requirement in sorted(source_requirements, key=lambda row: str(row["artifact_id"])):
        artifact_id = str(requirement["artifact_id"])
        record = source_records.get(artifact_id)
        if record is None:
            raise KnowledgePackError(f"missing source record {artifact_id}")
        sha256 = record.get("sha256")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise KnowledgePackError(f"invalid source identity {artifact_id}")
        fragments = record.get("fragments", {})
        selected: list[dict[str, str]] = []
        for selector in sorted(str(value) for value in requirement.get("fragment_selectors", [])):
            fragment_hash = fragments.get(selector)
            if not isinstance(fragment_hash, str) or len(fragment_hash) != 64:
                raise KnowledgePackError(f"missing fragment {artifact_id}#{selector}")
            selected.append({"selector": selector, "fragment_hash": fragment_hash})
        resolved_sources.append({"artifact_id": artifact_id, "sha256": sha256, "fragments": selected})
    if not resolved_sources:
        raise KnowledgePackError("at least one source is required")
    source_set_hash = canonical_sha256(resolved_sources, role="KNOWLEDGE_PACK_SOURCE_SET")
    compiled_pack_hash = canonical_sha256(
        {"knowledge_pack_id": knowledge_pack_id, "source_set_hash": source_set_hash, "compiled_content": compiled_content},
        role="KNOWLEDGE_PACK_COMPILED",
    )
    return {
        "schema": "ovc-dsai-knowledge-pack-manifest/v1",
        "knowledge_pack_id": knowledge_pack_id,
        "source_set_hash": source_set_hash,
        "compiled_pack_hash": compiled_pack_hash,
        "sources": resolved_sources,
        "authority_effect": "NONE",
    }


def build_dependency_graph(*, knowledge_pack_id: str, edges: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    for raw in edges:
        row = {
            "source_artifact_id": str(raw["source_artifact_id"]),
            "fragment_selector": str(raw["fragment_selector"]),
            "fragment_hash": str(raw["fragment_hash"]),
            "dependent_capability_id": str(raw["dependent_capability_id"]),
            "dependent_release_id": str(raw["dependent_release_id"]),
        }
        row["edge_id"] = canonical_sha256(row, role="KNOWLEDGE_DEPENDENCY_EDGE")
        normalized.append(row)
    normalized.sort(key=lambda row: row["edge_id"])
    logical = {"knowledge_pack_id": knowledge_pack_id, "edges": normalized}
    return {
        "schema": "ovc-dsai-knowledge-dependency-graph/v1",
        "graph_id": canonical_sha256(logical, role="KNOWLEDGE_DEPENDENCY_GRAPH"),
        **logical,
        "authority_effect": "NONE",
    }


def propagate_knowledge_staleness(
    *,
    graph: Mapping[str, Any],
    current_source_records: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    stale_releases: set[str] = set()
    stale_capabilities: set[str] = set()
    whole_pack = False
    reasons: set[str] = set()
    for edge in graph.get("edges", []):
        artifact_id = edge["source_artifact_id"]
        selector = edge["fragment_selector"]
        source = current_source_records.get(artifact_id)
        if source is None:
            whole_pack = True
            reasons.add("SOURCE_MISSING_WHOLE_PACK")
            continue
        if source.get("selectors_valid", True) is not True:
            whole_pack = True
            reasons.add("SELECTOR_MAPPING_AMBIGUOUS_WHOLE_PACK")
            continue
        fragments = source.get("fragments", {})
        if selector not in fragments:
            whole_pack = True
            reasons.add("SELECTOR_MISSING_OR_REMAPPED_WHOLE_PACK")
            continue
        if fragments[selector] != edge["fragment_hash"]:
            stale_releases.add(edge["dependent_release_id"])
            stale_capabilities.add(edge["dependent_capability_id"])
            reasons.add("MAPPED_FRAGMENT_DRIFT_SELECTIVE")
    if whole_pack:
        stale_releases = {edge["dependent_release_id"] for edge in graph.get("edges", [])}
        stale_capabilities = {edge["dependent_capability_id"] for edge in graph.get("edges", [])}
    return {
        "status": "STALE" if whole_pack or stale_releases else "CURRENT",
        "whole_pack_stale": whole_pack,
        "stale_release_ids": sorted(stale_releases),
        "stale_capability_ids": sorted(stale_capabilities),
        "reason_codes": sorted(reasons),
        "authority_effect": "NONE",
    }
