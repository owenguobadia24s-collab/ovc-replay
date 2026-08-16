from __future__ import annotations

import pytest

from ovc.research_operations.prsc.contracts import (
    CHALLENGE_DIMENSIONS,
    PRSCContractError,
    adapt_ec1_record,
    build_protocol_generation,
    semantic_id,
    validate_claim_dependency_manifest,
)


def test_semantic_hash_is_order_independent() -> None:
    assert semantic_id({"b": 2, "a": 1}) == semantic_id({"a": 1, "b": 2})


def test_protocol_generation_is_outcome_blind_and_content_addressed() -> None:
    record = build_protocol_generation(
        protocol_series_id="PRSC.EC1.G1",
        generation=1,
        scientific_generation="OVC-EC1-DISCOVERY-2021_2023-G1",
        method_pack_refs=["dependence:v1", "reference:v1"],
        hypothesis_family_registry_ref="registry:hypotheses",
        claim_template_refs=["claim:recurrence"],
        reviewer_constitution_ref="reviewer:v1",
    )
    assert record["outcome_blind"] is True
    assert record["authority_effect"] == "NONE"
    identity = record.pop("protocol_generation_id")
    assert identity == semantic_id(record)


@pytest.mark.parametrize("namespace", ["OPT_C", "OPT_D", "VALIDATION", "PROBABILITY", "RISK", "EXPOSURE", "EXECUTION"])
def test_protocol_outcome_firewall(namespace: str) -> None:
    with pytest.raises(PRSCContractError, match="PRSC_OUTCOME_FIREWALL"):
        build_protocol_generation(
            protocol_series_id="PRSC.EC1.G1",
            generation=1,
            scientific_generation="OVC-EC1-DISCOVERY-2021_2023-G1",
            method_pack_refs=[],
            hypothesis_family_registry_ref="registry:h",
            claim_template_refs=[],
            reviewer_constitution_ref="reviewer:v1",
            source_namespaces=["EC1_G1", namespace],
        )


def test_ec1_adapter_is_additive_and_nonmutating() -> None:
    source = {"candidate_id": "c1", "state": "ELIGIBLE"}
    adapted = adapt_ec1_record(source, prsc_refs=["prsc:1"])
    assert source == {"candidate_id": "c1", "state": "ELIGIBLE"}
    assert adapted["candidate_id"] == "c1"
    assert adapted["state"] == "ELIGIBLE"
    assert adapted["prsc_refs"] == ["prsc:1"]


def test_claim_algebra_contract_forbids_weighted_score() -> None:
    manifest = {
        "required_dimensions": ["dependence", "reference"],
        "optional_dimensions": ["context"],
        "allowed_effects": ["REQUIRE", "ANNOTATE"],
        "aggregation": "WEIGHTED_SCORE",
    }
    with pytest.raises(PRSCContractError, match="PRSC_COMPENSATORY_AGGREGATION_FORBIDDEN"):
        validate_claim_dependency_manifest(manifest)


def test_challenge_dimension_registry_is_exact() -> None:
    assert CHALLENGE_DIMENSIONS == (
        "dependence", "reference", "representation", "temporal",
        "context", "boundary", "multiplicity", "replication",
    )
