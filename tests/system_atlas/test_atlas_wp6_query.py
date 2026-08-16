from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ovc.development.skills.registry import validate_against_schema
from ovc.system_atlas import (
    AtlasQueryError,
    AtlasQueryIndex,
    QUERY_FAMILIES,
    build_reference_generation,
    build_system_graph,
    execute_optimized_query,
    execute_reference_query,
    query_equivalence_receipt,
)
from ovc.system_atlas.registries import load_registry_bundle


ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "fixtures/system_atlas/wp1/ATLAS_WP1_SYNTHETIC_GRAPH_v0_1.json"
CASES = ROOT / "fixtures/system_atlas/wp6/ATLAS_WP6_QUERY_CASES_v0_1.json"
SCHEMAS = ROOT / "schemas/system_atlas"
PUBLIC = ["ATLAS_PUBLIC_METADATA"]
ALL = ["ATLAS_PUBLIC_METADATA", "ATLAS_INTERNAL", "ATLAS_RESTRICTED"]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def inline_local_refs(node, root):
    if isinstance(node, list):
        return [inline_local_refs(item, root) for item in node]
    if not isinstance(node, dict):
        return node
    if set(node) == {"$ref"} and node["$ref"].startswith("#/"):
        target = root
        for part in node["$ref"][2:].split("/"):
            target = target[part]
        return inline_local_refs(target, root)
    return {key: inline_local_refs(value, root) for key, value in node.items()}


def query_graph() -> tuple[dict, dict]:
    source = load(GRAPH)
    registries = load_registry_bundle(ROOT)
    owner = deepcopy(source["entities"][0])
    owner.update(
        entity_id="synthetic:programme:atlas-owner",
        entity_type="PROGRAMME",
        label="Atlas synthetic owner",
        aliases=["Atlas Owner"],
    )
    restricted_evidence = deepcopy(source["evidence_references"][0])
    restricted_evidence.update(
        evidence_id="atlas:evidence:wp6-restricted",
        source_identity="WP6-RESTRICTED",
        visibility_partition="ATLAS_RESTRICTED",
    )
    restricted = deepcopy(source["entities"][0])
    restricted.update(
        entity_id="synthetic:service:wp6-restricted",
        entity_type="SERVICE",
        label="WP6 restricted service",
        aliases=["Hidden Atlas Service"],
        evidence_refs=[restricted_evidence["evidence_id"]],
        visibility_partition="ATLAS_RESTRICTED",
    )
    owns = deepcopy(source["relationships"][0])
    owns.update(
        relationship_id="atlas:relationship:wp6-owner",
        subject_id="ovc:programme:system-atlas-conformance.v0.1",
        predicate="OWNS",
        object_id=owner["entity_id"],
        family="OWNERSHIP",
        resolution_status="DECLARED_ONLY",
    )
    owner_assertion = deepcopy(source["assertions"][0])
    owner_assertion.update(
        assertion_id="atlas:assertion:wp6-owner-candidate",
        subject_id="ovc:programme:system-atlas-conformance.v0.1",
        predicate="OWNS",
        value=owner["entity_id"],
        status="CANDIDATE",
        scope={
            "scope_id": "atlas-wp6-owner",
            "dimensions": {
                "programme": "OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1",
                "owner_role": "PROGRAMME_OWNER",
            },
        },
    )
    graph = build_system_graph(
        graph_id="synthetic:graph:atlas-wp6-query.v0.1",
        generation=source["generation"],
        entities=[*source["entities"], owner, restricted],
        relationships=[*source["relationships"], owns],
        assertions=[*source["assertions"], owner_assertion],
        evidence_references=[*source["evidence_references"], restricted_evidence],
        conflicts=source["conflicts"],
        registry_versions=source["registry_versions"],
        completeness_profile="ATLAS_WP6_SYNTHETIC_QUERY_PROOF",
        court_record_status="SYNTHETIC_NOT_COURT_RECORD",
        registries=registries,
    )
    return graph, registries


def generations():
    graph, registries = query_graph()
    predecessor = build_reference_generation(graph, registries)
    successor_graph = deepcopy(graph)
    successor_graph["entities"][0]["label"] = "Atlas operational reliance changed"
    successor_graph = build_system_graph(
        graph_id=successor_graph["graph_id"],
        generation=successor_graph["generation"],
        entities=successor_graph["entities"],
        relationships=successor_graph["relationships"],
        assertions=successor_graph["assertions"],
        evidence_references=successor_graph["evidence_references"],
        conflicts=successor_graph["conflicts"],
        registry_versions=successor_graph["registry_versions"],
        completeness_profile=successor_graph["completeness_profile"],
        court_record_status=successor_graph["court_record_status"],
        registries=registries,
    )
    successor = build_reference_generation(
        successor_graph,
        registries,
        predecessor_root_hash=predecessor.root_hash,
    )
    return predecessor, successor


def run_pair(bundle, query, *, comparison=None, allowed=ALL, maximum=None):
    reference = execute_reference_query(
        bundle,
        query,
        allowed_partitions=allowed,
        comparison_bundle=comparison,
        maximum_result_records=maximum,
    )
    optimized = execute_optimized_query(
        AtlasQueryIndex(bundle),
        query,
        allowed_partitions=allowed,
        comparison_index=None if comparison is None else AtlasQueryIndex(comparison),
        maximum_result_records=maximum,
    )
    return reference, optimized


def test_all_query_families_have_exact_equivalence_receipts_and_valid_schemas() -> None:
    predecessor, successor = generations()
    fixture = load(CASES)
    result_schema = load(SCHEMAS / "atlas_query_result_v0_1.schema.json")
    receipt_schema = load(SCHEMAS / "atlas_query_equivalence_receipt_v0_1.schema.json")
    receipts = []
    for case in fixture["cases"]:
        comparison = predecessor if case["query"]["family"] == "DIFF" else None
        reference, optimized = run_pair(successor, case["query"], comparison=comparison)
        assert reference == optimized
        validate_against_schema(reference, inline_local_refs(result_schema, result_schema))
        receipt = query_equivalence_receipt(
            family=case["query"]["family"],
            cases=[case],
            reference_results=[reference],
            optimized_results=[optimized],
        )
        validate_against_schema(receipt, inline_local_refs(receipt_schema, receipt_schema))
        assert receipt["result"] == "PASS"
        receipts.append(receipt)
    assert {receipt["family"] for receipt in receipts} == set(QUERY_FAMILIES)


def test_search_ranking_visibility_and_explain_do_not_leak_restricted_records() -> None:
    _, bundle = generations()
    public, optimized = run_pair(bundle, {"family": "SEARCH", "term": "Atlas"}, allowed=PUBLIC)
    assert public == optimized
    assert public["result"]["matches"][0]["match_class"] in {"EXACT_LABEL", "EXACT_ALIAS"}
    hidden, _ = run_pair(bundle, {"family": "SEARCH", "term": "Hidden Atlas Service"}, allowed=PUBLIC)
    assert hidden["result"]["matches"] == []
    visible, _ = run_pair(bundle, {"family": "SEARCH", "term": "Hidden Atlas Service"}, allowed=ALL)
    assert visible["result"]["matches"][0]["entity"]["entity_id"] == "synthetic:service:wp6-restricted"
    with pytest.raises(AtlasQueryError, match="ATLAS_EXPLAIN_OBJECT_NOT_VISIBLE"):
        execute_reference_query(
            bundle,
            {"family": "EXPLAIN", "object_id": "synthetic:service:wp6-restricted"},
            allowed_partitions=PUBLIC,
        )


def test_trace_dependency_impact_and_blocker_semantics_are_bounded() -> None:
    _, bundle = generations()
    trace, _ = run_pair(
        bundle,
        {"family": "TRACE", "start_id": "ovc:capability:system-atlas.operational-reliance", "max_depth": 4},
    )
    assert trace["result"]["bounded_depth"] == 4
    assert trace["result"]["paths"]
    dependency, _ = run_pair(
        bundle,
        {"family": "DEPENDENCY", "entity_id": "ovc:capability:system-atlas.operational-reliance"},
    )
    assert {row["dependency_class"] for row in dependency["result"]["dependencies"]} >= {"REQUIRED"}
    impact, _ = run_pair(
        bundle,
        {"family": "IMPACT", "changed_entity_ids": ["ovc:gate:atlas-g-observability-activate"], "max_depth": 3},
    )
    assert impact["result"]["impacts"]
    blocked, _ = run_pair(
        bundle,
        {"family": "WHY_BLOCKED", "entity_id": "ovc:capability:system-atlas.operational-reliance"},
    )
    assert blocked["result"]["minimal_current_frontier"][0]["blocker_id"] == "ovc:gate:atlas-g-observability-activate"
    with pytest.raises(AtlasQueryError, match="ATLAS_TRACE_DEPTH_INVALID"):
        execute_reference_query(
            bundle,
            {"family": "TRACE", "start_id": "ovc:capability:system-atlas.operational-reliance"},
            allowed_partitions=ALL,
        )


def test_history_diff_authority_ownership_and_capacity_are_typed() -> None:
    predecessor, successor = generations()
    history, _ = run_pair(successor, {"family": "HISTORY"})
    assert history["result"]["predecessor_root_hash"] == predecessor.root_hash
    diff, _ = run_pair(successor, {"family": "DIFF"}, comparison=predecessor)
    assert diff["result"]["changes"]["entities"]["changed"]
    authority, _ = run_pair(successor, {"family": "AUTHORITY"})
    assert authority["result"]["assertions"]
    ownership, _ = run_pair(successor, {"family": "OWNERSHIP"})
    assert ownership["result"]["relationships"][0]["predicate"] == "OWNS"
    capacity, optimized = run_pair(successor, {"family": "SEARCH", "term": "Atlas"}, maximum=1)
    assert capacity == optimized
    assert capacity["status"] == "INCOMPLETE_CAPACITY"
    assert capacity["exhaustive"] is False
    assert capacity["result"]["returned_records"] == []


def test_invalid_visibility_and_equivalence_divergence_fail_closed() -> None:
    _, bundle = generations()
    with pytest.raises(AtlasQueryError, match="ATLAS_QUERY_VISIBILITY_REQUIRED"):
        execute_reference_query(bundle, {"family": "HISTORY"}, allowed_partitions=[])
    reference, optimized = run_pair(bundle, {"family": "SEARCH", "term": "Atlas"})
    divergent = deepcopy(optimized)
    divergent["status"] = "INCOMPLETE_CAPACITY"
    receipt = query_equivalence_receipt(
        family="SEARCH",
        cases=[{"case_id": "DIVERGENT"}],
        reference_results=[reference],
        optimized_results=[divergent],
    )
    assert receipt["result"] == "FAIL_OPTIMIZED_QUARANTINED"
    assert receipt["optimized_conformance"] == "DENIED"
