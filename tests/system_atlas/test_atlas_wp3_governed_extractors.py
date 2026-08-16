from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from ovc.development.skills.registry import validate_against_schema
from ovc.system_atlas.architecture import (
    architecture_manifest_observations,
    manifest_currentness_record,
    validate_architecture_manifest,
)
from ovc.system_atlas.canonical import canonical_sha256
from ovc.system_atlas.governed_extractors import AtlasGovernedExtractorError, extract_governed_sources


ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE = ROOT / "registries/system_atlas/ATLAS_ARCHITECTURE_MANIFEST_v0_1.json"
CASES = ROOT / "fixtures/system_atlas/wp3/ATLAS_MANIFEST_CURRENTNESS_CASES_v0_1.json"
GOVERNED_SCHEMA = ROOT / "schemas/system_atlas/governed_raw_observation_set_v0_1.schema.json"
MANIFEST_SCHEMA = ROOT / "schemas/system_atlas/atlas_architecture_manifest_v0_1.schema.json"
CURRENTNESS_SCHEMA = ROOT / "schemas/system_atlas/manifest_currentness_record_v0_1.schema.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def inline_local_refs(node: Any, root: dict) -> Any:
    if isinstance(node, list):
        return [inline_local_refs(item, root) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        target: Any = root
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return inline_local_refs(target, root)
    return {key: inline_local_refs(value, root) for key, value in node.items()}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def governed_fixture(root: Path) -> dict:
    records = {
        "registries/implementation/example/CURRENT_STATE.json": '{"programme_id":"OVC-EXAMPLE-v0.1","status":"CURRENT"}\n',
        "registries/authority/EXAMPLE_AUTHORITY.json": '{"authority_id":"AUTH-1","status":"DENIED"}\n',
        "contracts/example/EXAMPLE.md": "# Example Contract\nStatus: FROZEN\n",
        "schemas/example/example.schema.json": '{"$id":"https://example.invalid/schema","type":"object"}\n',
        "registries/example/EXAMPLE_REGISTRY.json": '{"registry_id":"REG-1","ratio":1.50,"status":"CURRENT"}\n',
        "docs/releases/research-example/EVIDENCE.json": '{"research_id":"RESEARCH-1","status":"OBSERVED"}\n',
    }
    for path, content in records.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "atlas@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Atlas Fixture"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True)
    commit = git(root, "rev-parse", "HEAD")
    tree = git(root, "rev-parse", "HEAD^{tree}")
    component_types = {
        "contracts": "CONTRACT",
        "schemas": "SCHEMA",
        "registries": "REGISTRY",
        "docs": "EVIDENCE_RECORD",
    }
    components = []
    for index, path in enumerate(sorted(records), 1):
        components.append(
            {
                "component_id": f"GRT.COMP.{index}",
                "path": path,
                "blob_hash_or_tree_hash": git(root, "rev-parse", f"HEAD:{path}"),
                "component_type": component_types[path.split("/", 1)[0]],
            }
        )
    return {
        "schema": "ovc-atlas-raw-observation-set/v1",
        "repository_commit": commit,
        "repository_tree": tree,
        "physical_components": components,
        "raw_observation_set_hash": "a" * 64,
        "court_record_status": "EXACT_GIT_TREE",
    }


def test_governed_extractors_cover_six_classes_without_canonical_assertions(tmp_path: Path) -> None:
    fixture = governed_fixture(tmp_path)
    result = extract_governed_sources(tmp_path, grt_observation_set=fixture)
    assert result["source_class_counts"] == {
        "AUTHORITY_RECORD": 1,
        "CONTRACT": 1,
        "PROGRAMME_RECORD": 1,
        "REGISTRY": 1,
        "RESEARCH_RECORD": 1,
        "SCHEMA": 1,
    }
    assert result["canonical_assertions"] == []
    assert {row["evidence_class"] for row in result["raw_observations"]} == {"SOURCE_EXPLICIT"}
    assert all(row["canonical_promotion"].startswith("DENIED_") for row in result["raw_observations"])
    ratio = next(row for row in result["raw_observations"] if row["raw_predicate"] == "ratio")
    assert ratio["raw_object"] == {"json_number": "1.50"}


def test_governed_extraction_is_order_independent_and_schema_valid(tmp_path: Path) -> None:
    fixture = governed_fixture(tmp_path)
    first = extract_governed_sources(tmp_path, grt_observation_set=fixture)
    reversed_fixture = deepcopy(fixture)
    reversed_fixture["physical_components"].reverse()
    assert extract_governed_sources(tmp_path, grt_observation_set=reversed_fixture) == first
    body = dict(first)
    observed_hash = body.pop("governed_observation_set_hash")
    assert canonical_sha256(body) == observed_hash
    schema = load(GOVERNED_SCHEMA)
    validate_against_schema(first, inline_local_refs(schema, schema))


def test_governed_extractor_fails_on_grt_blob_mismatch(tmp_path: Path) -> None:
    fixture = governed_fixture(tmp_path)
    fixture["physical_components"][0]["blob_hash_or_tree_hash"] = "f" * 40
    with pytest.raises(AtlasGovernedExtractorError, match="ATLAS_GOVERNED_BLOB_MISMATCH"):
        extract_governed_sources(tmp_path, grt_observation_set=fixture)


def test_architecture_manifest_and_all_currentness_states_are_exact() -> None:
    manifest = load(ARCHITECTURE)
    validate_architecture_manifest(manifest)
    schema = load(MANIFEST_SCHEMA)
    validate_against_schema(manifest, inline_local_refs(schema, schema))
    fixture = load(CASES)
    renamed = {
        "design": manifest["source_bindings"][0]["locator"],
        "plan": manifest["source_bindings"][1]["locator"],
    }
    for case in fixture["cases"]:
        observed = {renamed[key]: value for key, value in case["observed_source_hashes"].items()}
        record = manifest_currentness_record(
            manifest,
            observed_source_hashes=observed,
            repository_commit="1" * 40,
            repository_tree="2" * 40,
            superseded_manifest_ids=case["superseded_manifest_ids"],
        )
        assert record["status"] == case["expected_status"]
        assert record["current_declarative_eligibility"] is (case["expected_status"] == "CURRENT")
        body = dict(record)
        observed_hash = body.pop("record_hash")
        assert canonical_sha256(body) == observed_hash
        currentness_schema = load(CURRENTNESS_SCHEMA)
        validate_against_schema(record, inline_local_refs(currentness_schema, currentness_schema))


def test_stale_architecture_declarations_remain_historical_and_noncanonical() -> None:
    manifest = load(ARCHITECTURE)
    currentness = manifest_currentness_record(
        manifest,
        observed_source_hashes={},
        repository_commit="1" * 40,
        repository_tree="2" * 40,
    )
    result = architecture_manifest_observations(manifest, currentness)
    assert result["canonical_assertions"] == []
    assert all(row["current_declarative_eligibility"] is False for row in result["declarations"])
    assert all(row["authority_effect"] == "NONE_DESIGN_CANON_DECLARATION_ONLY" for row in result["declarations"])


def test_wp3_extractor_registry_is_frozen_and_complete() -> None:
    registry = load(ROOT / "registries/system_atlas/ATLAS_EXTRACTOR_REGISTRY_v0_1.json")
    assert registry["status"] == "FROZEN_ATLAS_G3"
    source_classes = {row["source_class"] for row in registry["registered_extractors"]}
    assert {
        "PROGRAMME_RECORD",
        "AUTHORITY_RECORD",
        "CONTRACT",
        "SCHEMA",
        "REGISTRY",
        "RESEARCH_RECORD",
        "SOURCE_BOUND_ARCHITECTURE_MANIFEST",
    } <= source_classes
