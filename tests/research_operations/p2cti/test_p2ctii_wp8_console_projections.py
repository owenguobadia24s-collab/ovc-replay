from __future__ import annotations

import copy

import pytest

from ovc.research_operations.p2cti.projections import (
    ProjectionValidationError,
    build_console_projection,
    build_source_admission_packet,
)

FRONTIER = "p2cti:frontier:" + "a" * 64


def _query_result() -> dict:
    return {
        "generation_id": "p2cti:generation:" + "b" * 64,
        "source_frontier_id": FRONTIER,
        "currentness_state": "CURRENT",
        "visibility_state": "REFERENCE_ONLY",
        "completeness_state": "COMPLETE",
        "warnings": ["NEGATIVE_EVIDENCE_PRESERVED"],
        "result": {"subject_id": "TH-001", "summary": "reference-only"},
        "read_only": True,
        "decision_bearing": False,
        "semantic_promotion": False,
        "authority_effect": "NONE",
    }


def test_console_projection_preserves_full_envelope_and_no_write_controls() -> None:
    result = build_console_projection(
        query_family="GET_THEORY",
        query_result=_query_result(),
        evidence_passport_refs=["evidence:2", "evidence:1"],
        system_atlas_deep_link="atlas://p2cti/TH-001",
    )
    assert result["generation_id"] == _query_result()["generation_id"]
    assert result["source_frontier_id"] == FRONTIER
    assert result["currentness_state"] == "CURRENT"
    assert result["visibility_state"] == "REFERENCE_ONLY"
    assert result["completeness_state"] == "COMPLETE"
    assert result["warnings"] == ["NEGATIVE_EVIDENCE_PRESERVED"]
    assert result["evidence_passport_refs"] == ["evidence:1", "evidence:2"]
    assert result["read_only"] is True
    assert result["write_controls_present"] is False
    assert result["consumer_admission_granted"] is False
    assert result["operational_reliance"] is False
    assert result["authority_effect"] == "NONE"


def test_projection_rejects_missing_envelope_or_write_like_source() -> None:
    missing = _query_result()
    missing.pop("completeness_state")
    with pytest.raises(ProjectionValidationError, match="missing projection envelope"):
        build_console_projection(query_family="GET_THEORY", query_result=missing, evidence_passport_refs=[])
    writable = _query_result()
    writable["read_only"] = False
    with pytest.raises(ProjectionValidationError, match="read-only"):
        build_console_projection(query_family="GET_THEORY", query_result=writable, evidence_passport_refs=[])


def test_projection_is_deterministic_and_does_not_alias_query_result() -> None:
    source = _query_result()
    first = build_console_projection(query_family="SEARCH", query_result=source, evidence_passport_refs=["evidence:b", "evidence:a"])
    second = build_console_projection(query_family="SEARCH", query_result=copy.deepcopy(source), evidence_passport_refs=["evidence:a", "evidence:b"])
    assert first == second
    first["result"]["summary"] = "mutated projection"
    assert source["result"]["summary"] == "reference-only"


def test_source_admission_packet_is_producer_evidence_not_consumer_authority() -> None:
    packet = build_source_admission_packet(
        source_frontier_id=FRONTIER,
        projection_evidence_sha256="c" * 64,
        producer_authority_refs=["P2CTII-G7-PASS", "P2CTII-G0"],
    )
    assert packet["source_id"] == "P2CTI"
    assert packet["producer_recommendation"] == "READY_FOR_CONSUMER_OWNER_ADMISSION_REVIEW"
    assert packet["consumer_owner"] == "RESEARCH_CONSOLE"
    assert packet["consumer_admission"] == "NOT_GRANTED_BY_P2CTI"
    assert packet["source_presentation_authority"] == "NON_TRANSITIVE"
    assert packet["operational_reliance"] is False
    assert packet["authority_effect"] == "NONE"


def test_source_admission_fails_closed_without_exact_frontier_or_authority_refs() -> None:
    with pytest.raises(ProjectionValidationError):
        build_source_admission_packet(source_frontier_id="latest", projection_evidence_sha256="c" * 64, producer_authority_refs=["P2CTII-G7-PASS"])
    with pytest.raises(ProjectionValidationError):
        build_source_admission_packet(source_frontier_id=FRONTIER, projection_evidence_sha256="c" * 64, producer_authority_refs=[])
