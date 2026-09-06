from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.mcac.contracts import ComparabilityContext, MCACContractError
from ovc.research_operations.mcac.doctrine import ASSERTION_IDS, DOCTRINE_HASH, enforce_doctrine

from .conftest import context, coordinate, occurrence, registry


def test_equal_duration_is_not_identity_and_alias_is_rejected():
    tv = coordinate("TV120_NATIVE", 7200, generation="HIST", owner="TV")
    owner = coordinate("2H_A_L", 7200, generation="CURRENT", owner="C2")
    assert tv.coordinate_id != owner.coordinate_id
    with pytest.raises(MCACContractError, match="MCAC_PROTECTED_CLOCK_ALIAS_REJECTED"):
        context(tv, owner)


def test_registry_never_confers_execution_authority():
    clock = coordinate("15M", 900)
    with pytest.raises(MCACContractError, match="MCAC_REGISTRY_AUTHORITY_EFFECT_FORBIDDEN"):
        type(registry(clock))(clock, "AUTH", "OK", "r1", "2020-01-01T00:00:00Z", ("x",), "ALLOW")


def test_authority_must_resolve_before_mcac():
    base = context()
    values = dict(base.__dict__); values["authority_resolved"] = False
    with pytest.raises(MCACContractError, match="MCAC_AUTHORITY_MUST_RESOLVE_IN_IROF"):
        ComparabilityContext(**values)


def test_doctrine_complete_and_tamper_rejected():
    receipt = enforce_doctrine(ASSERTION_IDS, DOCTRINE_HASH)
    assert receipt.identity_effect == receipt.composition_effect == receipt.ontology_effect == "NONE"
    with pytest.raises(MCACContractError, match="MCAC_DOCTRINE_HASH_MISMATCH"):
        enforce_doctrine(ASSERTION_IDS, "0" * 64)
    with pytest.raises(MCACContractError, match="MCAC_NEGATIVE_DOCTRINE_MISSING"):
        enforce_doctrine(ASSERTION_IDS[:-1], DOCTRINE_HASH)


def test_machine_doctrine_matches_module():
    root = Path(__file__).resolve().parents[3]
    payload = json.loads((root / "registries/research_operations/mcac/MCAC_NEGATIVE_DOCTRINE_v0_1.json").read_text())
    assert payload["logical_hash"] == DOCTRINE_HASH
    assert tuple(payload["assertions"]) == ASSERTION_IDS


def test_json_schemas_validate_contract_examples():
    root = Path(__file__).resolve().parents[3]
    schema_root = root / "schemas/research_operations/mcac"
    clock = coordinate("15M", 900); reg = registry(clock)
    item = occurrence(clock, reg, "o", "2020-01-01T00:00:00Z", "2020-01-01T01:00:00Z")
    for name, payload in (("clock_coordinate_v0_1.schema.json", clock.semantic_dict()), ("clock_indexed_occurrence_ref_v0_1.schema.json", item.semantic_dict())):
        schema = json.loads((schema_root / name).read_text())
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object" and schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
        assert set(payload) == set(schema["required"])
    result_schema = json.loads((schema_root / "comparison_result_v0_1.schema.json").read_text())
    assert result_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert {"status", "context_id", "doctrine_hash", "identity_effect", "composition_effect", "complete"} == set(result_schema["required"])


def test_future_dependency_is_not_evaluable():
    assert context(cutoff="2019-12-31T23:59:59Z").evaluation_state == "NOT_EVALUABLE"
