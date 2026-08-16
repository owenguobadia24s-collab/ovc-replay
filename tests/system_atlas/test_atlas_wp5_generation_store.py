from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ovc.development.skills.registry import validate_against_schema
from ovc.system_atlas import (
    AtlasGenerationError,
    GenerationBundle,
    GraphStore,
    build_incremental_generation,
    build_reference_generation,
    build_system_graph,
    generation_equivalence_receipt,
    graph_logical_hash,
    load_generation_bundle,
    materialize_generation,
    publish_current_generation,
    retention_inventory,
    verify_generation_bundle,
)
from ovc.system_atlas.registries import load_registry_bundle


ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "fixtures/system_atlas/wp1/ATLAS_WP1_SYNTHETIC_GRAPH_v0_1.json"
CASES = ROOT / "fixtures/system_atlas/wp5/ATLAS_WP5_GENERATION_CASES_v0_1.json"
SCHEMAS = ROOT / "schemas/system_atlas"


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


def partitioned_graph() -> tuple[dict, dict]:
    source = load(GRAPH)
    registries = load_registry_bundle(ROOT)
    internal_evidence = deepcopy(source["evidence_references"][0])
    internal_evidence.update(
        evidence_id="atlas:evidence:wp5-internal",
        source_identity="WP5-INTERNAL",
        visibility_partition="ATLAS_INTERNAL",
    )
    restricted_evidence = deepcopy(source["evidence_references"][0])
    restricted_evidence.update(
        evidence_id="atlas:evidence:wp5-restricted",
        source_identity="WP5-RESTRICTED",
        visibility_partition="ATLAS_RESTRICTED",
    )
    internal_entity = deepcopy(source["entities"][0])
    internal_entity.update(
        entity_id="synthetic:entity:wp5-internal",
        label="WP5 internal entity",
        aliases=[],
        visibility_partition="ATLAS_INTERNAL",
        evidence_refs=[internal_evidence["evidence_id"]],
    )
    restricted_entity = deepcopy(source["entities"][0])
    restricted_entity.update(
        entity_id="synthetic:entity:wp5-restricted",
        label="WP5 restricted entity",
        aliases=[],
        visibility_partition="ATLAS_RESTRICTED",
        evidence_refs=[restricted_evidence["evidence_id"]],
    )
    relationship = deepcopy(source["relationships"][0])
    relationship.update(
        relationship_id="atlas:relationship:wp5-public-to-internal",
        subject_id=source["entities"][0]["entity_id"],
        object_id=internal_entity["entity_id"],
        predicate="REFERENCES",
        family="DATA",
        evidence_refs=[internal_evidence["evidence_id"]],
    )
    assertion = deepcopy(source["assertions"][0])
    assertion.update(
        assertion_id="atlas:assertion:wp5-restricted-currentness-candidate",
        subject_id=restricted_entity["entity_id"],
        predicate="CURRENT",
        value="UNKNOWN",
        status="CANDIDATE",
        evidence_refs=[restricted_evidence["evidence_id"]],
    )
    graph = build_system_graph(
        graph_id="synthetic:graph:atlas-wp5-partitions.v0.1",
        generation=source["generation"],
        entities=[*source["entities"], internal_entity, restricted_entity],
        relationships=[*source["relationships"], relationship],
        assertions=[*source["assertions"], assertion],
        evidence_references=[*source["evidence_references"], internal_evidence, restricted_evidence],
        conflicts=source["conflicts"],
        registry_versions=source["registry_versions"],
        completeness_profile="ATLAS_WP5_SYNTHETIC_PARTITION_PROOF",
        court_record_status="SYNTHETIC_NOT_COURT_RECORD",
        registries=registries,
    )
    return graph, registries


def test_reference_generation_is_deterministic_partitioned_and_schema_valid() -> None:
    graph, registries = partitioned_graph()
    first = build_reference_generation(graph, registries)
    second = build_reference_generation(deepcopy(graph), registries)
    assert first.root_hash == second.root_hash
    assert first.files == second.files
    assert verify_generation_bundle(first)["status"] == "PASS"
    root_schema = load(SCHEMAS / "atlas_generation_root_manifest_v0_1.schema.json")
    partition_schema = load(SCHEMAS / "atlas_generation_partition_manifest_v0_1.schema.json")
    validate_against_schema(first.root_manifest, inline_local_refs(root_schema, root_schema))
    for partition in first.root_manifest["partitions"]:
        manifest = json.loads(first.files[f"partitions/{partition}/manifest.json"])
        validate_against_schema(manifest, inline_local_refs(partition_schema, partition_schema))
    assert first.root_manifest["partitions"]["ATLAS_RESTRICTED"]["counts"]["entities"] == 1
    assert b"wp5-restricted" not in first.files["partitions/ATLAS_PUBLIC_METADATA/entities.jsonl"]
    assert b"wp5-restricted" in first.files["partitions/ATLAS_RESTRICTED/entities.jsonl"]


def test_reference_incremental_generation_bytes_are_equivalent() -> None:
    base = load(GRAPH)
    graph, registries = partitioned_graph()
    predecessor = build_reference_generation(base, registries)
    reference = build_reference_generation(graph, registries, predecessor_root_hash=predecessor.root_hash)
    incremental = build_incremental_generation(graph, registries, previous_bundle=predecessor)
    receipt = generation_equivalence_receipt(reference, incremental)
    assert receipt["result"] == "PASS"
    assert reference.root_hash == incremental.root_hash
    assert reference.files == incremental.files


def test_visibility_downgrade_and_partition_tamper_fail_closed() -> None:
    graph, registries = partitioned_graph()
    restricted_evidence = "atlas:evidence:wp5-restricted"
    graph["entities"][0]["evidence_refs"].append(restricted_evidence)
    graph["graph_logical_hash"] = graph_logical_hash(graph)
    with pytest.raises(AtlasGenerationError, match="ATLAS_VISIBILITY_DOWNGRADE_ENTITY"):
        build_reference_generation(graph, registries)

    clean, registries = partitioned_graph()
    bundle = build_reference_generation(clean, registries)
    files = dict(bundle.files)
    path = "partitions/ATLAS_INTERNAL/entities.jsonl"
    files[path] += b"{}\n"
    tampered = GenerationBundle(bundle.root_hash, bundle.root_manifest, files)
    with pytest.raises(AtlasGenerationError, match="ATLAS_PARTITION_FILE_HASH_MISMATCH"):
        verify_generation_bundle(tampered)


def test_graph_store_rebuild_restart_and_partition_intersection(tmp_path: Path) -> None:
    graph, registries = partitioned_graph()
    bundle = build_reference_generation(graph, registries)
    store = GraphStore(tmp_path / "atlas.sqlite3")
    result = store.rebuild(bundle)
    assert result["root_hash"] == bundle.root_hash
    restarted = GraphStore(tmp_path / "atlas.sqlite3")
    assert restarted.root_hash() == bundle.root_hash
    restricted_id = "synthetic:entity:wp5-restricted"
    assert restarted.object_by_id("entities", restricted_id, allowed_partitions=["ATLAS_PUBLIC_METADATA"]) is None
    assert restarted.object_by_id("entities", restricted_id, allowed_partitions=["ATLAS_RESTRICTED"])["entity_id"] == restricted_id
    public_id = graph["entities"][0]["entity_id"]
    assert restarted.adjacent(public_id, allowed_partitions=["ATLAS_PUBLIC_METADATA"])
    assert any(row["relationship_id"] == "atlas:relationship:wp5-public-to-internal" for row in restarted.adjacent(public_id, allowed_partitions=["ATLAS_INTERNAL"]))


def test_two_point_publication_retains_stale_and_switches_only_exact_main(tmp_path: Path) -> None:
    graph, registries = partitioned_graph()
    bundle = build_reference_generation(graph, registries)
    observed = {"commit": graph["generation"]["repository_commit"], "tree": graph["generation"]["repository_tree"]}
    moved = {"commit": "f" * 40, "tree": "e" * 40}
    stale = publish_current_generation(bundle, tmp_path, pre_publish_main=observed, rechecked_main=moved)
    assert stale["result"] == "STALE_MAIN_MOVED_POINTER_NOT_SWITCHED"
    assert not (tmp_path / "generations/CURRENT.json").exists()
    assert (tmp_path / "generations" / bundle.root_hash / "manifest.json").is_file()
    current = publish_current_generation(bundle, tmp_path, pre_publish_main=observed, rechecked_main=observed)
    assert current["result"] == "PASS_CURRENT_POINTER_SWITCHED"
    pointer = load(tmp_path / "generations/CURRENT.json")
    assert pointer["root_hash"] == bundle.root_hash
    receipt_schema = load(SCHEMAS / "atlas_pre_publish_currentness_receipt_v0_1.schema.json")
    validate_against_schema(current, inline_local_refs(receipt_schema, receipt_schema))
    assert retention_inventory(tmp_path)["retained_generation_roots"] == [bundle.root_hash]


def test_generation_materialisation_round_trip_is_content_addressed(tmp_path: Path) -> None:
    graph, registries = partitioned_graph()
    bundle = build_reference_generation(graph, registries)
    path = materialize_generation(bundle, tmp_path)
    assert path.name == bundle.root_hash
    assert load_generation_bundle(path) == bundle
    assert materialize_generation(bundle, tmp_path) == path


def test_g4_followups_block_ambiguous_owner_role_and_caller_authored_currentness() -> None:
    graph, registries = partitioned_graph()
    source = graph["evidence_references"][0]
    assertion = {
        "assertion_id": "atlas:assertion:wp5-canonical-owner",
        "subject_id": graph["entities"][0]["entity_id"],
        "predicate": "OWNS",
        "value": "synthetic:owner:wp5",
        "scope": {"scope_id": "atlas-wp5-owner", "dimensions": {"programme": "OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1"}},
        "status": "CANONICAL",
        "evidence_refs": [source["evidence_id"]],
        "authority_effect": "NONE",
    }
    candidate = deepcopy(graph)
    candidate["assertions"].append(assertion)
    candidate = build_system_graph(
        graph_id=candidate["graph_id"], generation=candidate["generation"], entities=candidate["entities"],
        relationships=candidate["relationships"], assertions=candidate["assertions"],
        evidence_references=candidate["evidence_references"], conflicts=candidate["conflicts"],
        registry_versions=candidate["registry_versions"], completeness_profile=candidate["completeness_profile"],
        court_record_status=candidate["court_record_status"], registries=registries,
    )
    with pytest.raises(AtlasGenerationError, match="ATLAS_OWNER_ROLE_REQUIRED"):
        build_reference_generation(candidate, registries)
    assertion["scope"]["dimensions"]["owner_role"] = "PROGRAMME_OWNER"
    candidate = build_system_graph(
        graph_id=graph["graph_id"], generation=graph["generation"], entities=graph["entities"],
        relationships=graph["relationships"], assertions=[*graph["assertions"], assertion],
        evidence_references=graph["evidence_references"], conflicts=graph["conflicts"],
        registry_versions=graph["registry_versions"], completeness_profile=graph["completeness_profile"],
        court_record_status=graph["court_record_status"], registries=registries,
    )
    with pytest.raises(AtlasGenerationError, match="ATLAS_SOURCE_CURRENTNESS_REPOSITORY_REQUIRED"):
        build_reference_generation(candidate, registries)
    forged = deepcopy(candidate)
    forged["evidence_references"][0]["source_blob_sha"] = "f" * 40
    forged["graph_logical_hash"] = graph_logical_hash(forged)
    with pytest.raises(AtlasGenerationError, match="ATLAS_SOURCE_BLOB_MISMATCH"):
        build_reference_generation(forged, registries, repository_root=ROOT)
    assert build_reference_generation(candidate, registries, repository_root=ROOT).root_hash


def test_atlas_core_capacity_fails_typed_without_sampling() -> None:
    graph, registries = partitioned_graph()
    with pytest.raises(AtlasGenerationError, match="CAPACITY_EXCEEDED"):
        build_reference_generation(graph, registries, maximum_records=1)
    cases = load(CASES)
    assert len(cases["cases"]) == 7
    assert cases["retention"] == "PROVISIONAL_RETAIN_ALL"
