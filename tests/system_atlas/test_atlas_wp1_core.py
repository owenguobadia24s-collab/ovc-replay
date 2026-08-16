from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ovc.system_atlas import AtlasContractError, build_system_graph, validate_system_graph
from ovc.system_atlas.canonical import CanonicalizationError, canonical_json_bytes, graph_logical_hash
from ovc.system_atlas.registries import load_registry_bundle


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/system_atlas/wp1/ATLAS_WP1_SYNTHETIC_GRAPH_v0_1.json"
ADVERSARIAL = ROOT / "fixtures/system_atlas/wp1/ATLAS_WP1_ADVERSARIAL_CASES_v0_1.json"
SCHEMAS = ROOT / "schemas/system_atlas"
CONTRACTS = ROOT / "contracts/system_atlas"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def graph_and_registries() -> tuple[dict, dict]:
    return load(FIXTURE), load_registry_bundle(ROOT)


def test_core_fixture_is_valid_authority_neutral_and_synthetic() -> None:
    graph, registries = graph_and_registries()
    result = validate_system_graph(graph, registries)
    assert result["status"] == "PASS"
    assert result["graph_logical_hash"] == "cd7ed95274300f431b74917cecfeca32f5c45eb101c3180306b3331bf66ac9f6"
    assert result["counts"] == {
        "entities": 4,
        "relationships": 2,
        "assertions": 2,
        "evidence_references": 2,
        "conflicts": 0,
    }
    assert graph["court_record_status"] == "SYNTHETIC_NOT_COURT_RECORD"
    assert graph["authority_effect"] == "NONE_READ_ONLY_DERIVED_GRAPH"


def test_canonical_graph_identity_ignores_input_order_and_set_order() -> None:
    graph, registries = graph_and_registries()
    shuffled = deepcopy(graph)
    for key in ("entities", "relationships", "assertions", "evidence_references"):
        shuffled[key].reverse()
    shuffled["entities"][0]["aliases"] = list(reversed(shuffled["entities"][0]["aliases"]))
    shuffled.pop("graph_logical_hash")
    rebuilt = build_system_graph(
        graph_id=shuffled["graph_id"],
        generation=shuffled["generation"],
        entities=shuffled["entities"],
        relationships=shuffled["relationships"],
        assertions=shuffled["assertions"],
        evidence_references=shuffled["evidence_references"],
        conflicts=shuffled["conflicts"],
        registry_versions=shuffled["registry_versions"],
        completeness_profile=shuffled["completeness_profile"],
        court_record_status=shuffled["court_record_status"],
        registries=registries,
    )
    assert rebuilt == graph
    assert canonical_json_bytes(rebuilt) == canonical_json_bytes(graph)


def test_all_nine_state_planes_remain_independent() -> None:
    graph, _ = graph_and_registries()
    expected = {"lifecycle", "implementation", "availability", "assurance", "authority", "activation", "canonicality", "currentness", "health"}
    for entity in graph["entities"]:
        assert set(entity["state_planes"]) == expected
    capability = next(row for row in graph["entities"] if row["entity_type"] == "CAPABILITY")
    assert capability["state_planes"]["authority"] == "RESERVED"
    assert capability["state_planes"]["activation"] == "INACTIVE"
    assert capability["state_planes"]["canonicality"] == "NONCANONICAL"


def test_high_risk_predicate_registry_is_fail_closed() -> None:
    registries = load_registry_bundle(ROOT)
    rows = {row["predicate"]: row for row in registries["predicate_authority"]["predicates"]}
    assert {"OWNS", "ACTIVE", "AUTHORISED", "CURRENT", "CANONICAL", "PUBLISHED"} <= set(rows)
    assert rows["OWNS"]["deterministic_derivation_allowed"] is False
    assert rows["OWNS"]["conflict_class"] == "OWNER_CONFLICT"
    assert rows["AUTHORISED"]["derivation_rule"] == "INTERSECTION_ONLY_NO_ADJACENCY_GRANT"
    assert rows["ACTIVE"]["default_failure_bias"] == "INACTIVE_OR_UNKNOWN_NEVER_ACTIVE"


def test_adversarial_mutations_fail_with_expected_contract_codes() -> None:
    graph, registries = graph_and_registries()
    catalogue = load(ADVERSARIAL)
    expected = {row["case_id"]: row["expected_error"] for row in catalogue["cases"]}

    cases: dict[str, dict] = {}
    cases["FALSE_AUTHORITY_ALLOW"] = deepcopy(graph)
    cases["FALSE_AUTHORITY_ALLOW"]["authority_effect"] = "GRANTED"
    cases["FALSE_ACTIVE_STATE"] = deepcopy(graph)
    del cases["FALSE_ACTIVE_STATE"]["entities"][0]["state_planes"]["activation"]
    cases["GRAPH_HASH_MISMATCH"] = deepcopy(graph)
    cases["GRAPH_HASH_MISMATCH"]["graph_logical_hash"] = "f" * 64
    cases["UNKNOWN_RELATIONSHIP"] = deepcopy(graph)
    cases["UNKNOWN_RELATIONSHIP"]["relationships"][0]["predicate"] = "IMPLIES_AUTHORITY"
    cases["MISSING_EVIDENCE"] = deepcopy(graph)
    cases["MISSING_EVIDENCE"]["relationships"][0]["evidence_refs"] = []
    cases["UNCLASSIFIED_VISIBILITY"] = deepcopy(graph)
    cases["UNCLASSIFIED_VISIBILITY"]["entities"][0]["visibility_partition"] = "UNCLASSIFIED"
    cases["PROSPECTIVE_AS_COURT_RECORD"] = deepcopy(graph)
    cases["PROSPECTIVE_AS_COURT_RECORD"]["generation"]["repository_tree"] = "not-a-sha"

    for case_id, candidate in cases.items():
        with pytest.raises(AtlasContractError, match=expected[case_id]):
            validate_system_graph(candidate, registries)

    float_case = deepcopy(graph)
    float_case["assertions"][0]["value"] = 0.5
    with pytest.raises(CanonicalizationError, match=expected["FLOAT_IDENTITY_INPUT"]):
        graph_logical_hash(float_case)


def test_absolute_evidence_paths_are_rejected_from_logical_graph() -> None:
    graph, registries = graph_and_registries()
    graph["evidence_references"][0]["source_path"] = "C:/private/source.json"
    graph["graph_logical_hash"] = graph_logical_hash(graph)
    with pytest.raises(AtlasContractError, match="ATLAS_EVIDENCE_PATH_INVALID"):
        validate_system_graph(graph, registries)


def test_unknown_owner_is_preserved_as_conflict_not_selected() -> None:
    graph, registries = graph_and_registries()
    evidence_id = graph["evidence_references"][0]["evidence_id"]
    subject_id = graph["entities"][-1]["entity_id"]
    owner_assertions = [
        {
            "assertion_id": "atlas:assertion:owner-candidate-a",
            "subject_id": subject_id,
            "predicate": "OWNS",
            "value": "synthetic:owner:a",
            "scope": {"scope_id": "atlas-synthetic-global", "dimensions": {"programme": "OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1"}},
            "status": "CANDIDATE",
            "evidence_refs": [evidence_id],
            "authority_effect": "NONE",
        },
        {
            "assertion_id": "atlas:assertion:owner-candidate-b",
            "subject_id": subject_id,
            "predicate": "OWNS",
            "value": "synthetic:owner:b",
            "scope": {"scope_id": "atlas-synthetic-global", "dimensions": {"programme": "OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1"}},
            "status": "CANDIDATE",
            "evidence_refs": [evidence_id],
            "authority_effect": "NONE",
        },
    ]
    conflict = {
        "conflict_id": "atlas:conflict:synthetic-owner",
        "conflict_class": "OWNER_CONFLICT",
        "subject_id": subject_id,
        "predicate": "OWNS",
        "competing_assertion_ids": [row["assertion_id"] for row in owner_assertions],
        "status": "OPEN",
        "evidence_refs": [evidence_id],
        "authority_effect": "NONE",
    }
    candidate = build_system_graph(
        graph_id="synthetic:graph:owner-conflict.v0.1",
        generation=graph["generation"],
        entities=graph["entities"],
        relationships=graph["relationships"],
        assertions=owner_assertions,
        evidence_references=graph["evidence_references"],
        conflicts=[conflict],
        registry_versions=graph["registry_versions"],
        completeness_profile="ATLAS_WP1_OWNER_CONFLICT",
        court_record_status="SYNTHETIC_NOT_COURT_RECORD",
        registries=registries,
    )
    assert candidate["conflicts"][0]["status"] == "OPEN"
    assert all(row["status"] == "CANDIDATE" for row in candidate["assertions"])


def test_wp1_schemas_contracts_and_registries_are_machine_readable() -> None:
    schema_names = {path.name for path in SCHEMAS.glob("*.json")}
    assert {"atlas_registry_bundle_v0_1.schema.json", "ovc_system_graph_v0_1.schema.json"} <= schema_names
    for path in SCHEMAS.glob("*.json"):
        schema = load(path)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
    assert (CONTRACTS / "OVC_SYSTEM_GRAPH_CONTRACT_v0_1.md").is_file()
    assert (CONTRACTS / "ATLAS_CANONICAL_SERIALIZATION_CONTRACT_v0_1.md").is_file()
    registries = load_registry_bundle(ROOT)
    assert len(registries) == 7
    assert all(row["authority_effect"] == "NONE" for row in registries.values())
