from __future__ import annotations

import pytest

from ovc.research_operations.p1cdi.candidate_firewall import (
    assert_candidate_firewall,
    assert_no_outcome_repair,
    bind_source_disposition,
    build_candidate_derivation_manifest,
    build_proposal_readiness_assessment,
    preserve_frozen_candidate,
    project_freeze_disposition,
)


def test_mechanical_readiness_is_derivative_only() -> None:
    record = build_proposal_readiness_assessment(
        generation_id="p1:generation:g1",
        source_completeness_refs=["evidence:a", "evidence:b"],
    )
    assert record["result"] == "MECHANICAL_REVIEW_READY"
    assert record["candidate_write"] == "DENIED"
    assert record["authority_effect"] == "NONE"
    assert_candidate_firewall(record)


def test_mechanical_readiness_requires_completeness() -> None:
    with pytest.raises(ValueError):
        build_proposal_readiness_assessment(
            generation_id="p1:generation:g1",
            source_completeness_refs=[],
            result="MECHANICAL_REVIEW_READY",
        )


def test_many_to_many_ancestry_does_not_collapse_identity() -> None:
    one = build_candidate_derivation_manifest(
        distinction_generation_refs=["p1:generation:g1", "p1:generation:g2"],
        candidate_ref="dmrp:candidate:c1",
        relation="COMBINES_DISTINCTIONS",
    )
    two = build_candidate_derivation_manifest(
        distinction_generation_refs=["p1:generation:g1"],
        candidate_ref="dmrp:candidate:c2",
        relation="REFINES_DISTINCTION",
    )
    assert one["candidate_ref"] != two["candidate_ref"]
    assert one["record_id"] != two["record_id"]
    assert one["distinction_generation_refs"] == ["p1:generation:g1", "p1:generation:g2"]
    assert_candidate_firewall(one)
    assert_candidate_firewall(two)


def test_freeze_disposition_is_projection_not_actuation() -> None:
    binding = bind_source_disposition(
        candidate_ref="dmrp:candidate:c1",
        source_disposition_ref="dmrp:disposition:d1",
        projected_value="FREEZE_CANDIDATE",
    )
    projection = project_freeze_disposition(binding)
    assert projection["candidate_generation_creation"] == "DENIED"
    assert projection["freeze_actuation"] == "DENIED"
    assert projection["authority_effect"] == "NONE"


def test_candidate_generation_creation_never_implies_c_admission() -> None:
    with pytest.raises(PermissionError):
        assert_candidate_firewall(
            {
                "record_type": "ResearchCandidateGeneration",
                "authority_effect": "NONE",
                "candidate_write": "DENIED",
            }
        )
    with pytest.raises(PermissionError):
        assert_candidate_firewall(
            {
                "record_type": "CandidateEvaluationAdmission",
                "authority_effect": "NONE",
                "candidate_write": "DENIED",
            }
        )


def test_post_freeze_evidence_requires_successor_lineage() -> None:
    binding = preserve_frozen_candidate(
        frozen_candidate_ref="dmrp:candidate:c1",
        frozen_semantic_sha256="a" * 64,
        later_evidence_refs=["p1:evidence:new"],
    )
    assert binding["semantic_mutation"] == "DENIED"
    assert binding["required_route"] == "SUCCESSOR_LINEAGE_ONLY"


@pytest.mark.parametrize("source", ["OPT-C", "OPT-D", "VALIDATION"])
def test_downstream_outcomes_cannot_repair_discovery_or_candidate(source: str) -> None:
    denial = assert_no_outcome_repair(source_class=source, target_generation_ref="p1:generation:g1")
    assert denial["result"] == "DENIED"
    assert denial["authority_effect"] == "NONE"


def test_candidate_firewall_rejects_hidden_write_fields() -> None:
    with pytest.raises(PermissionError):
        assert_candidate_firewall(
            {
                "record_type": "P1CandidateDerivationManifest",
                "authority_effect": "NONE",
                "candidate_write": "DENIED",
                "candidate_payload": {"hidden": True},
            }
        )
