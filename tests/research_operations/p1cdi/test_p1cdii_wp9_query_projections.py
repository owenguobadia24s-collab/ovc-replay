from __future__ import annotations

import json

import pytest

from ovc.research_operations.p1cdi.demand import (
    build_discovery_demand,
    build_discovery_work_recommendation,
)
from ovc.research_operations.p1cdi.indexes import build_search_index
from ovc.research_operations.p1cdi.projections import (
    P1CDIProjectionError,
    build_console_projection,
    build_source_admission_packet,
)
from ovc.research_operations.p1cdi.query import P1CDIReadOnlyQueryService, QUERY_FAMILIES, main
from ovc.research_operations.p1cdi.visibility import (
    build_visibility_decision,
    build_visibility_safe_index_entry,
)

FRONTIER = "p1:frontier:fixture-current"
PROFILE = "P1CDI-SEMANTIC-PROJECTION-v1"
GEN = "p1:generation:visible-001"
SERIES = "p1:series:visible-001"


def _safe(record: dict) -> dict:
    decision = build_visibility_decision(
        source_ref=f"source:{record.get('record_type')}",
        classification="PATH1_SAFE",
        classification_complete=True,
    )
    entry = build_visibility_safe_index_entry(decision=decision, record=record)
    assert entry is not None
    return entry


def _records() -> list[dict]:
    demand = build_discovery_demand(
        generation_refs=[GEN],
        demand_type="REPLICATION",
        required_information=["independent replay"],
        blockers=["REPLICATION_NOT_YET_AVAILABLE"],
    )
    recommendation = build_discovery_work_recommendation(
        demand_refs=[demand["demand_id"]],
        reason_trace=["OPEN_REPLICATION_DEMAND"],
    )
    return [
        {
            "record_type": "P1EmpiricalDistinctionGeneration",
            "schema_version": "0.1",
            "generation_id": GEN,
            "series_id": SERIES,
            "profile_id": PROFILE,
            "projection_sha256": "a" * 64,
            "source_first_valid_time": "2026-01-01T00:00:00Z",
            "source_refs": ["source:discovery:1"],
            "authority_effect": "NONE",
        },
        {
            "record_type": "P1DistinctionEvidenceStateVector",
            "schema_version": "0.1",
            "record_id": "p1:evidence:1",
            "generation_id": GEN,
            "source_refs": ["source:evidence:1"],
            "denominator": "COMPLETE_WITH_CENSORING",
            "recurrence": "PRESENT",
            "dependence": "INDEPENDENCE_UNKNOWN",
            "separation": "PRESENT",
            "integrity": "PASS",
            "other_planes": {"typed_negative_evidence": "PRESERVED"},
            "authority_effect": "NONE",
        },
        {
            "record_type": "P1DistinctionContradictionRecord",
            "schema_version": "0.1",
            "record_id": "p1:contradiction:1",
            "generation_id": GEN,
            "source_refs": ["source:contradiction:1"],
            "contradiction_type": "SOURCE_RESULT_CONTRADICTION",
            "authority_effect": "NONE",
        },
        {
            "record_type": "P1NullEvidenceBinding",
            "schema_version": "0.1",
            "record_id": "p1:null:1",
            "generation_id": GEN,
            "source_refs": ["source:null:1"],
            "null_class": "CAPACITY_INCOMPLETE",
            "authority_effect": "NONE",
        },
        {
            "record_type": "P1DistinctionCorrespondenceRecord",
            "schema_version": "0.1",
            "record_id": "p1:corr:1",
            "left_generation_id": GEN,
            "right_generation_id": "p1:generation:other",
            "semantic_relation": "REFINES",
            "adjudication_state": "REVIEW_REQUIRED",
            "authority_effect": "NONE",
        },
        demand,
        recommendation,
        {
            "record_type": "P1ProposalReadinessAssessment",
            "schema_version": "0.1",
            "assessment_id": "p1:readiness:1",
            "generation_refs": [GEN],
            "readiness": "MECHANICAL_REVIEW_READY",
            "scientific_eligibility": "NOT_GRANTED",
            "authority_effect": "NONE",
        },
        {
            "record_type": "P1HistoricalProjection",
            "schema_version": "0.1",
            "record_id": "p1:history:1",
            "logical_id": GEN,
            "generation_id": GEN,
            "first_valid_time": "2026-01-15T00:00:00Z",
            "state": "INITIAL",
            "authority_effect": "NONE",
        },
        {
            "record_type": "P1HistoricalProjection",
            "schema_version": "0.1",
            "record_id": "p1:history:2",
            "logical_id": GEN,
            "generation_id": GEN,
            "first_valid_time": "2026-03-01T00:00:00Z",
            "state": "FUTURE",
            "authority_effect": "NONE",
        },
    ]


def _service(*, optimized: bool = True) -> P1CDIReadOnlyQueryService:
    entries = [_safe(record) for record in _records()]
    return P1CDIReadOnlyQueryService(
        visibility_safe_entries=entries,
        source_frontier_id=FRONTIER,
        assessment_profile_generation=PROFILE,
        currentness_state="CURRENT",
        visibility_state="PATH1_SAFE",
        completeness_state="COMPLETE",
        warnings=["NEGATIVE_EVIDENCE_PRESERVED"],
        optimized_index=build_search_index(entries) if optimized else None,
    )


def test_all_wp9_query_families_are_read_only_complete_and_non_operational() -> None:
    service = _service()
    results = [
        service.search("visible-001"),
        service.get_distinction(GEN),
        service.why_here(GEN),
        service.history(GEN),
        service.as_of(GEN, "2026-02-01T00:00:00Z"),
        service.evidence(GEN),
        service.contradictions(GEN),
        service.nulls(GEN),
        service.correspondence(GEN),
        service.demand(GEN),
        service.why_blocked(GEN),
        service.unblock_path(GEN),
        service.candidate_progression(GEN),
        service.portfolio_state(),
        service.next_discovery_work(),
    ]
    assert {result["query_family"] for result in results} == set(QUERY_FAMILIES)
    for result in results:
        assert result["source_frontier_id"] == FRONTIER
        assert result["assessment_profile_generation"] == PROFILE
        assert result["visibility_state"] == "PATH1_SAFE"
        assert result["currentness_state"] == "CURRENT"
        assert result["completeness_state"] == "COMPLETE"
        assert result["warnings"] == ["NEGATIVE_EVIDENCE_PRESERVED"]
        assert result["read_only"] is True
        assert result["silent_truncation"] == "FORBIDDEN"
        assert result["write_controls_present"] is False
        assert result["operational_reliance"] is False
        assert result["authority_effect"] == "NONE"
        assert len(result["content_sha256"]) == 64


def test_as_of_excludes_future_visible_evidence_without_hindsight_rewrite() -> None:
    result = _service().as_of(GEN, "2026-02-01T00:00:00Z")
    ids = {record.get("record_id") for record in result["result"]}
    assert "p1:history:1" in ids
    assert "p1:history:2" not in ids


def test_evidence_contradictions_and_nulls_remain_distinct_without_scalar_score() -> None:
    evidence = _service().evidence(GEN)
    contradictions = _service().contradictions(GEN)
    nulls = _service().nulls(GEN)
    assert {record["record_type"] for record in evidence["result"]} == {"P1DistinctionEvidenceStateVector"}
    assert {record["record_type"] for record in contradictions["result"]} == {"P1DistinctionContradictionRecord"}
    assert {record["record_type"] for record in nulls["result"]} == {"P1NullEvidenceBinding"}
    assert all("score" not in record for result in (evidence, contradictions, nulls) for record in result["result"])


def test_next_discovery_work_remains_advisory_and_has_no_actuation_fields() -> None:
    result = _service().next_discovery_work()
    assert result["reason_trace"] == ["ADVISORY_ONLY", "NO_ACTUATOR_REACHABILITY"]
    assert result["result"][0]["route_class"] == "ADVISORY_ONLY"
    assert result["result"][0]["actuation"] == "DENIED"
    assert result["result"][0]["write_capability"] == "NONE"


def test_protected_record_never_enters_query_service_or_search_counts() -> None:
    protected = {
        "record_type": "ProtectedPath2CandidateDefinition",
        "schema_version": "0.1",
        "generation_id": "hidden-generation",
        "title": "do not leak",
        "authority_effect": "NONE",
    }
    decision = build_visibility_decision(
        source_ref="source:protected",
        classification="PROTECTED",
        classification_complete=True,
    )
    assert build_visibility_safe_index_entry(decision=decision, record=protected) is None
    portfolio = _service().portfolio_state()["result"]
    assert "ProtectedPath2CandidateDefinition" not in portfolio["record_type_counts"]


def test_corrupt_optimized_index_fails_closed_instead_of_changing_answer() -> None:
    entries = [_safe(record) for record in _records()]
    index = build_search_index(entries)
    index["search_text"] = dict(index["search_text"])
    index["search_text"][next(iter(index["search_text"]))] = "tampered"
    service = P1CDIReadOnlyQueryService(
        visibility_safe_entries=entries,
        source_frontier_id=FRONTIER,
        assessment_profile_generation=PROFILE,
        currentness_state="CURRENT",
        visibility_state="PATH1_SAFE",
        completeness_state="COMPLETE",
        optimized_index=index,
    )
    with pytest.raises(Exception):
        service.search("visible-001")


def test_console_projection_and_source_packet_do_not_self_admit_or_grant_reliance() -> None:
    query_result = _service().get_distinction(GEN)
    projection = build_console_projection(
        query_result=query_result,
        evidence_refs=["evidence:wp8", "evidence:wp7"],
        system_atlas_refs=["atlas:topology:p1cdi"],
    )
    assert projection["consumer_admission_granted"] is False
    assert projection["system_atlas_mutation"] == "DENIED"
    assert projection["write_controls_present"] is False
    assert projection["operational_reliance"] is False
    assert projection["authority_effect"] == "NONE"

    packet = build_source_admission_packet(
        source_frontier_id=FRONTIER,
        assessment_profile_generation=PROFILE,
        projection_evidence_sha256=projection["content_sha256"],
        producer_authority_refs=["P1CDII-G0", "P1CDII-G8-PASS"],
        query_families=QUERY_FAMILIES,
        system_atlas_refs=["atlas:topology:p1cdi"],
    )
    assert packet["consumer_admission"] == "NOT_GRANTED_BY_P1CDI"
    assert packet["source_presentation_authority"] == "NON_TRANSITIVE"
    assert packet["write_controls"] == "ABSENT"
    assert packet["operational_reliance"] is False
    assert packet["authority_effect"] == "NONE"


def test_source_packet_rejects_unknown_query_family_and_console_rejects_write_like_result() -> None:
    query_result = _service().get_distinction(GEN)
    writable = dict(query_result)
    writable["write_controls_present"] = True
    with pytest.raises(P1CDIProjectionError):
        build_console_projection(query_result=writable)
    with pytest.raises(P1CDIProjectionError):
        build_source_admission_packet(
            source_frontier_id=FRONTIER,
            assessment_profile_generation=PROFILE,
            projection_evidence_sha256="a" * 64,
            producer_authority_refs=["P1CDII-G0"],
            query_families=["UNKNOWN"],
        )


def test_read_only_cli_returns_query_without_any_write_surface(tmp_path, capsys) -> None:
    entries = [_safe(record) for record in _records()]
    bundle = {
        "visibility_safe_entries": entries,
        "source_frontier_id": FRONTIER,
        "assessment_profile_generation": PROFILE,
        "currentness_state": "CURRENT",
        "visibility_state": "PATH1_SAFE",
        "completeness_state": "COMPLETE",
        "warnings": [],
        "optimized_index": build_search_index(entries),
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    assert main(["--bundle", str(path), "--family", "GET_DISTINCTION", "--target", GEN]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["read_only"] is True
    assert output["write_controls_present"] is False
    assert output["operational_reliance"] is False
