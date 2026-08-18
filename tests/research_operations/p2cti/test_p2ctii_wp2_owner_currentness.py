from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ovc.research_operations.p2cti.currentness import (
    build_source_frontier,
    dependency_bounded_invalidation,
    evaluate_two_point_currentness,
    require_g2_alg_for_decision_bearing_pointer,
)
from ovc.research_operations.p2cti.identity import generation_id, series_id
from ovc.research_operations.p2cti.sources import resolve_owner_predicate


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/p2cti/P2CTII_WP2_OWNER_CURRENTNESS_FIXTURES_v0_1.json").read_text()
)
OWNER_REGISTRY = json.loads(
    (ROOT / "registries/research_operations/p2cti/P2CTI_OWNER_SOURCE_REGISTRY_v0_1.json").read_text()
)


def _frontier(rows: list[dict], *, unresolved: tuple[str, ...] = ()) -> dict:
    return build_source_frontier(copy.deepcopy(rows), unresolved_reasons=unresolved)


def _generation(frontier_id: str) -> tuple[str, str]:
    series = series_id()
    generation = generation_id(
        series=series,
        generation_ordinal=0,
        member_entry_ids=["p2cti:entry:" + "a" * 64],
        source_frontier=frontier_id,
    )
    return series, generation


def test_declared_owner_resolution_is_order_independent_and_advisory() -> None:
    evidence = FIXTURE["owner_evidence"]
    forward = resolve_owner_predicate(
        object_type="THEORY_RECORD",
        predicate="EVIDENCE_STATE",
        evidence=evidence,
        owner_registry=OWNER_REGISTRY,
    )
    reverse = resolve_owner_predicate(
        object_type="THEORY_RECORD",
        predicate="EVIDENCE_STATE",
        evidence=list(reversed(evidence)),
        owner_registry=OWNER_REGISTRY,
    )
    assert forward == reverse
    assert forward["resolution_state"] == "RESOLVED"
    assert forward["controlling_owner"] == "RESEARCH_OPERATIONS_DMRP_PATH2"
    assert forward["semantic_generation"] == "1"
    assert forward["visibility_state"] == "REFERENCE_ONLY"
    assert forward["decision_bearing"] is False


def test_missing_wrong_owner_and_generation_conflict_fail_closed() -> None:
    missing = resolve_owner_predicate(
        object_type="THEORY_RECORD",
        predicate="EVIDENCE_STATE",
        evidence=[],
        owner_registry=OWNER_REGISTRY,
    )
    assert missing["resolution_state"] == "UNRESOLVED"
    assert missing["warnings"] == ["OWNER_SOURCE_MISSING"]

    wrong = copy.deepcopy(FIXTURE["owner_evidence"][0])
    wrong["owner_programme"] = "CONVENIENT_NON_OWNER"
    conflict = resolve_owner_predicate(
        object_type="THEORY_RECORD",
        predicate="EVIDENCE_STATE",
        evidence=[wrong],
        owner_registry=OWNER_REGISTRY,
    )
    assert conflict["resolution_state"] == "CONFLICT"
    assert conflict["warnings"] == ["STATE_OWNER_CONFLICT"]

    advanced = copy.deepcopy(FIXTURE["owner_evidence"][0])
    advanced["semantic_generation"] = "2"
    advanced["source_sha256"] = "3" * 64
    generation_conflict = resolve_owner_predicate(
        object_type="THEORY_RECORD",
        predicate="EVIDENCE_STATE",
        evidence=[FIXTURE["owner_evidence"][0], advanced],
        owner_registry=OWNER_REGISTRY,
    )
    assert generation_conflict["resolution_state"] == "CONFLICT"


def test_recency_path_title_and_convenience_fields_are_rejected() -> None:
    recency_biased = copy.deepcopy(FIXTURE["owner_evidence"][0])
    recency_biased["observed_at"] = "2099-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="exact closed field set"):
        resolve_owner_predicate(
            object_type="THEORY_RECORD",
            predicate="EVIDENCE_STATE",
            evidence=[recency_biased],
            owner_registry=OWNER_REGISTRY,
        )


def test_source_frontier_is_order_independent_and_schema_conformant() -> None:
    before = _frontier(FIXTURE["frontier_before"])
    reverse = _frontier(list(reversed(FIXTURE["frontier_before"])))
    assert before["frontier_id"] == reverse["frontier_id"]
    assert before["content_sha256"] == reverse["content_sha256"]
    schema = json.loads(
        (ROOT / "schemas/research_operations/p2cti/p2cti_source_frontier_v0_1.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(before)


def test_two_point_equal_frontier_is_current_but_not_decision_bearing() -> None:
    before = _frontier(FIXTURE["frontier_before"])
    same = _frontier(list(reversed(FIXTURE["frontier_before"])))
    series, generation = _generation(before["frontier_id"])
    result = evaluate_two_point_currentness(
        series_id=series,
        generation_id=generation,
        prebuild_frontier=before,
        prepublish_frontier=same,
    )
    assert result["currentness_state"] == "CURRENT"
    assert result["frontiers_equal"] is True
    assert result["decision_bearing"] is False
    assert result["operational_pointer_switched"] is False
    assert result["historical_generation_disposition"] == "RETAINED_ADDRESSABLE"
    schema = json.loads(
        (ROOT / "schemas/research_operations/p2cti/p2cti_current_pointer_v0_1.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(result["advisory_pointer"])


def test_generation_advance_and_incomplete_frontier_never_fall_back() -> None:
    before = _frontier(FIXTURE["frontier_before"])
    advanced = _frontier(FIXTURE["frontier_generation_advanced"])
    series, generation = _generation(before["frontier_id"])
    moved = evaluate_two_point_currentness(
        series_id=series,
        generation_id=generation,
        prebuild_frontier=before,
        prepublish_frontier=advanced,
    )
    assert moved["currentness_state"] == "SOURCE_GENERATION_ADVANCED"
    assert moved["decision_bearing"] is False

    incomplete = _frontier(
        FIXTURE["frontier_generation_advanced"], unresolved=("OWNER_SOURCE_MISSING",)
    )
    unresolved = evaluate_two_point_currentness(
        series_id=series,
        generation_id=generation,
        prebuild_frontier=before,
        prepublish_frontier=incomplete,
    )
    assert unresolved["currentness_state"] == "UNRESOLVED"
    assert unresolved["warnings"] == ["CURRENTNESS_UNRESOLVED"]


def test_dependency_invalidation_is_exact_and_preserves_history() -> None:
    before = _frontier(FIXTURE["frontier_before"])
    advanced = _frontier(FIXTURE["frontier_generation_advanced"])
    result = dependency_bounded_invalidation(
        previous_frontier=before,
        current_frontier=advanced,
        generation_dependencies={
            "p2cti:generation:affected": [
                "RESEARCH_OPERATIONS_DMRP_PATH2|records/research_operations/path2/theory-001.json"
            ],
            "p2cti:generation:unaffected": [
                "RCCR|records/research_operations/rccr/assessment-001.json"
            ],
        },
    )
    assert result["affected_generation_ids"] == ["p2cti:generation:affected"]
    assert result["unaffected_generation_ids"] == ["p2cti:generation:unaffected"]
    assert result["historical_generations_preserved"] is True
    assert result["invalidation_scope"] == "EXACT_DEPENDENCIES_ONLY"


def test_g2_alg_is_a_hard_decision_bearing_pointer_boundary() -> None:
    with pytest.raises(PermissionError, match="P2CTII-G2-ALG"):
        require_g2_alg_for_decision_bearing_pointer(g2_alg_status="NOT_TAKEN")


def test_consolidated_review_packet_stops_at_independent_boundary() -> None:
    review = json.loads(
        (ROOT / "docs/programmes/p2cti-v0-1/wp2/P2CTII_G2_ALG_CONSOLIDATED_REVIEW_PACKET_v0_1.json").read_text()
    )
    state = json.loads(
        (ROOT / "records/research_operations/p2cti/P2CTII_PROGRAMME_STATE_v0_1.json").read_text()
    )
    assert review["gate_class"] == "INDEPENDENT_NON_OPERATOR_BLOCKING"
    assert review["reviewer_binding"] == "UNBOUND"
    assert review["gate_decision"] == "NOT_TAKEN"
    assert review["decision_bearing_before_pass"] is False
    assert review["operational_pointer_switch"] == "DENIED"
    assert state["packet_id"] == "P2CTII-WP2"
    assert state["next_packet"] == "P2CTII-G2-ALG"
    assert state["blockers"] == ["P2CTII_G2_ALG_INDEPENDENT_REVIEW_REQUIRED"]
