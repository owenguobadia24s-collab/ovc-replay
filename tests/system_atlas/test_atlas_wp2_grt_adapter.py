from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest

from ovc.system_atlas.canonical import canonical_sha256
from ovc.system_atlas.grt_adapter import (
    AtlasGRTAdapterError,
    GRT_EVIDENCE_CLASSES,
    adapt_grt_topology,
    scan_grt_exact_tree,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/system_atlas/wp2/GRT_EVIDENCE_CLASS_CASES_v0_1.json"
SCHEMA = ROOT / "schemas/system_atlas/raw_observation_set_v0_1.schema.json"
TREE = "2222222222222222222222222222222222222222"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_grt_adapter_preserves_every_evidence_class_and_emits_no_assertions() -> None:
    result = adapt_grt_topology(read_model=load(FIXTURE), repository_tree=TREE)
    relationship_observations = [row for row in result["raw_observations"] if row["observation_type"] == "COMPONENT_RELATIONSHIP"]
    assert {row["evidence_class"] for row in relationship_observations} == GRT_EVIDENCE_CLASSES
    assert result["canonical_assertions"] == []
    assert result["authority_effect"] == "NONE_RAW_OBSERVATION_SET_ONLY"
    assert result["completeness"] == {
        "grt_component_count": 3,
        "adapted_component_count": 3,
        "grt_component_edge_count": 8,
        "adapted_component_edge_count": 8,
    }


def test_high_risk_owner_and_governance_edges_never_promote() -> None:
    result = adapt_grt_topology(read_model=load(FIXTURE), repository_tree=TREE)
    high_risk = [row for row in result["component_edges"] if row["grt_predicate"] in {"OWNED_BY", "GOVERNED_BY"}]
    assert len(high_risk) == 4
    assert {row["high_risk_semantic_promotion"] for row in high_risk} == {"DENIED"}
    assert all(row["resolution_status"] == "OBSERVED_ONLY" for row in high_risk)


def test_adapter_is_input_order_independent_and_content_addressed() -> None:
    fixture = load(FIXTURE)
    first = adapt_grt_topology(read_model=fixture, repository_tree=TREE)
    reversed_fixture = deepcopy(fixture)
    reversed_fixture["components"].reverse()
    reversed_fixture["component_dependencies"].reverse()
    second = adapt_grt_topology(read_model=reversed_fixture, repository_tree=TREE)
    assert second == first
    body = dict(first)
    observed_hash = body.pop("raw_observation_set_hash")
    assert canonical_sha256(body) == observed_hash


def test_raw_observation_set_validates_against_draft_2020_12_schema() -> None:
    validator = jsonschema.Draft202012Validator(load(SCHEMA))
    errors = sorted(validator.iter_errors(adapt_grt_topology(read_model=load(FIXTURE), repository_tree=TREE)), key=lambda error: list(error.path))
    assert errors == []


def test_unknown_evidence_class_fails_closed() -> None:
    fixture = load(FIXTURE)
    fixture["component_dependencies"][0]["evidence_class"] = "OWNER_ASSUMED"
    with pytest.raises(AtlasGRTAdapterError, match="ATLAS_GRT_EVIDENCE_CLASS_INVALID"):
        adapt_grt_topology(read_model=fixture, repository_tree=TREE)


def test_edge_source_must_be_an_exact_tree_component() -> None:
    fixture = load(FIXTURE)
    fixture["component_dependencies"][0]["source_ref"] = "missing/source.json"
    with pytest.raises(AtlasGRTAdapterError, match="ATLAS_GRT_EDGE_SOURCE_NOT_IN_EXACT_TREE"):
        adapt_grt_topology(read_model=fixture, repository_tree=TREE)


def test_only_declared_programme_endpoints_are_admitted() -> None:
    fixture = load(FIXTURE)
    result = adapt_grt_topology(read_model=fixture, repository_tree=TREE)
    assert result["component_edges"][0]["to_id"] == "programme:OVC-SYNTHETIC-v0.1"
    fixture["component_dependencies"][0]["to_id"] = "programme:OVC-UNDECLARED-v0.1"
    with pytest.raises(AtlasGRTAdapterError, match="ATLAS_GRT_EDGE_ENDPOINT_INVALID"):
        adapt_grt_topology(read_model=fixture, repository_tree=TREE)


def test_scan_entrypoint_resolves_exact_commit_and_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "atlas@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Atlas Fixture"], check=True)
    (tmp_path / "record.txt").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "record.txt"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "fixture"], check=True)
    commit = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD^{tree}"], text=True).strip()
    fixture = load(FIXTURE)
    fixture["portfolio"]["source_commit"] = commit
    fixture["build_metadata"]["source_commit"] = commit
    monkeypatch.setattr("ovc.system_atlas.grt_adapter.build_repository_topology", lambda *args, **kwargs: fixture)
    result = scan_grt_exact_tree(tmp_path, commit=commit)
    assert result["repository_commit"] == commit
    assert result["repository_tree"] == tree


def test_scan_entrypoint_rejects_dirty_head(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "atlas@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Atlas Fixture"], check=True)
    record = tmp_path / "record.txt"
    record.write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "record.txt"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "fixture"], check=True)
    record.write_text("dirty\n", encoding="utf-8")
    with pytest.raises(AtlasGRTAdapterError, match="ATLAS_GRT_EXACT_TREE_WORKTREE_DIRTY"):
        scan_grt_exact_tree(tmp_path)
