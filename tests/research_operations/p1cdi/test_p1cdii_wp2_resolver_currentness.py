from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ovc.research_operations.p1cdi.currentness import (
    evaluate_two_point_currentness,
    require_g2_alg_for_pointer,
)
from ovc.research_operations.p1cdi.source_resolution import (
    REQUIRED_CURRENTNESS_OWNERS,
    build_source_frontier,
    resolve_owner_predicate,
)
from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP2_RESOLVER_FIXTURES_v0_1.json").read_text()
)


def frontier(frontier_id: str, entries: list[dict]) -> dict:
    return build_source_frontier(
        frontier_id=frontier_id,
        resolved_at="2026-08-18T00:00:00Z",
        owner_entries=copy.deepcopy(entries),
    )


def test_source_resolver_is_order_independent_and_owner_exact() -> None:
    evidence = FIXTURE["owner_evidence"]
    forward = resolve_owner_predicate("SOURCE_SCIENCE", evidence)
    reverse = resolve_owner_predicate("SOURCE_SCIENCE", list(reversed(evidence)))
    assert forward == reverse
    assert forward["resolution_state"] == "RESOLVED"
    assert forward["controlling_owner"] == "ECX_DMRP_RESEARCH_OPERATIONS"
    assert forward["decision_bearing"] is False

    wrong = copy.deepcopy(evidence[0])
    wrong["owner"] = "CONVENIENT_NON_OWNER"
    conflict = resolve_owner_predicate("SOURCE_SCIENCE", [wrong])
    assert conflict["resolution_state"] == "CONFLICT"
    assert conflict["reason_codes"] == ["OWNER_SEMANTIC_CONFLICT"]

    recency_biased = copy.deepcopy(evidence[0])
    recency_biased["timestamp"] = "2099-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="exact closed field set"):
        resolve_owner_predicate("SOURCE_SCIENCE", [recency_biased])

    advanced = copy.deepcopy(evidence[0])
    advanced["generation_ref"] = "ec1:generation:999"
    advanced["source_sha256"] = "9" * 64
    generation_conflict = resolve_owner_predicate("SOURCE_SCIENCE", [evidence[0], advanced])
    assert generation_conflict["resolution_state"] == "CONFLICT"


@pytest.mark.parametrize(
    ("predicate", "reason"),
    [
        ("SOURCE_SCIENCE", "UNRESOLVED_SOURCE_GENERATION"),
        ("P1_SCIENTIFIC_DISPOSITION", "UNRESOLVED_SCIENTIFIC_DISPOSITION"),
        ("CANDIDATE_PROPOSAL_FREEZE_C_ADMISSION", "UNRESOLVED_CANDIDATE_STATE"),
        ("GAP_AND_CAPABILITY_NEED", "UNRESOLVED_RCCR_STATE"),
        ("EXPOSURE_AND_INDEPENDENCE", "INDEPENDENCE_UNKNOWN"),
        ("VALIDATION_ACCESS", "ACCESS_UNRESOLVED"),
        ("P1CDI_IDENTITY_ACTIVITY_CURRENTNESS_LINEAGE", "UNRESOLVED_CURRENTNESS"),
    ],
)
def test_missing_high_risk_predicates_fail_closed(predicate: str, reason: str) -> None:
    result = resolve_owner_predicate(predicate, [])
    assert result["resolution_state"] == "UNRESOLVED"
    assert result["reason_codes"] == [reason]
    assert result["decision_bearing"] is False


def test_frontier_identity_is_order_independent() -> None:
    before = frontier("p1:frontier:before", FIXTURE["frontier_before"])
    reverse = frontier("p1:frontier:reverse", list(reversed(FIXTURE["frontier_before"])))
    assert before["frontier_sha256"] == reverse["frontier_sha256"]
    assert before["required_owners"] == FIXTURE["required_currentness_owners"]
    assert tuple(before["required_owners"]) == REQUIRED_CURRENTNESS_OWNERS
    assert before["completeness_state"] == "COMPLETE"
    assert before["missing_required_owners"] == []
    schema = json.loads(
        (ROOT / "schemas/research_operations/p1cdi/p1cdi_lifecycle_currentness_v0_1.schema.json").read_text()
    )
    validate_contract(schema, before)


def test_incomplete_required_owner_frontier_reproduces_review_and_fails_closed() -> None:
    incomplete = frontier(
        "p1:frontier:independent-review-reproduction",
        FIXTURE["frontier_incomplete_review_reproduction"],
    )
    schema = json.loads(
        (ROOT / "schemas/research_operations/p1cdi/p1cdi_lifecycle_currentness_v0_1.schema.json").read_text()
    )
    validate_contract(schema, incomplete)
    assert incomplete["completeness_state"] == "UNRESOLVED"
    assert incomplete["missing_required_owners"] == [
        owner
        for owner in REQUIRED_CURRENTNESS_OWNERS
        if owner != "ECX_DMRP_RESEARCH_OPERATIONS"
    ]
    result = evaluate_two_point_currentness(
        generation_id="p1:gen:001",
        prebuild_frontier=incomplete,
        prepublish_frontier=copy.deepcopy(incomplete),
    )
    assert result["frontiers_equal"] is True
    assert result["currentness"] == "UNRESOLVED"
    assert result["reason_codes"] == ["UNRESOLVED_CURRENTNESS"]


@pytest.mark.parametrize(
    ("state", "expected_currentness", "expected_reason"),
    [
        (
            case["resolution_state"],
            case["expected_currentness"],
            case["expected_reason"],
        )
        for case in FIXTURE["frontier_state_neighbors"]
    ],
)
def test_required_owner_non_current_states_fail_closed(
    state: str, expected_currentness: str, expected_reason: str
) -> None:
    rows = copy.deepcopy(FIXTURE["frontier_before"])
    rows[0]["resolution_state"] = state
    non_current = frontier(f"p1:frontier:{state.lower()}", rows)
    result = evaluate_two_point_currentness(
        generation_id="p1:gen:001",
        prebuild_frontier=non_current,
        prepublish_frontier=copy.deepcopy(non_current),
    )
    assert result["currentness"] == expected_currentness
    assert result["reason_codes"] == [expected_reason]


def test_duplicate_required_owner_conflicts_and_resolved_optional_owner_is_safe() -> None:
    duplicated_rows = copy.deepcopy(FIXTURE["frontier_before"])
    duplicated_rows.append(copy.deepcopy(duplicated_rows[0]))
    duplicated = frontier("p1:frontier:duplicate-owner", duplicated_rows)
    conflict = evaluate_two_point_currentness(
        generation_id="p1:gen:001",
        prebuild_frontier=duplicated,
        prepublish_frontier=copy.deepcopy(duplicated),
    )
    assert conflict["currentness"] == "CONFLICT"
    assert duplicated["duplicate_required_owners"] == ["ECX_DMRP_RESEARCH_OPERATIONS"]

    optional_rows = copy.deepcopy(FIXTURE["frontier_before"])
    optional_rows.append(copy.deepcopy(FIXTURE["frontier_resolved_optional_owner_neighbor"]))
    optional = frontier("p1:frontier:optional-owner", optional_rows)
    current = evaluate_two_point_currentness(
        generation_id="p1:gen:001",
        prebuild_frontier=optional,
        prepublish_frontier=copy.deepcopy(optional),
    )
    assert optional["completeness_state"] == "COMPLETE"
    assert current["currentness"] == "CURRENT"


def test_two_point_currentness_accepts_unchanged_and_stales_moved_frontier() -> None:
    before = frontier("p1:frontier:before", FIXTURE["frontier_before"])
    same = frontier("p1:frontier:same", list(reversed(FIXTURE["frontier_before"])))
    current = evaluate_two_point_currentness(
        generation_id="p1:gen:001", prebuild_frontier=before, prepublish_frontier=same
    )
    assert current["frontiers_equal"] is True
    assert current["currentness"] == "CURRENT"
    assert current["decision_bearing"] is False
    schema = json.loads(
        (ROOT / "schemas/research_operations/p1cdi/p1cdi_lifecycle_currentness_v0_1.schema.json").read_text()
    )
    validate_contract(schema, current)

    moved = frontier("p1:frontier:moved", FIXTURE["frontier_moved"])
    stale = evaluate_two_point_currentness(
        generation_id="p1:gen:001", prebuild_frontier=before, prepublish_frontier=moved
    )
    assert stale["frontiers_equal"] is False
    assert stale["currentness"] == "STALE"
    assert stale["reason_codes"] == ["SOURCE_FRONTIER_MOVED"]


def test_tampered_frontier_is_rejected_before_currentness() -> None:
    before = frontier("p1:frontier:before", FIXTURE["frontier_before"])
    tampered = copy.deepcopy(before)
    tampered["owner_entries"][0]["generation_ref"] = "ec1:generation:tampered"
    with pytest.raises(ValueError, match="hash does not bind"):
        evaluate_two_point_currentness(
            generation_id="p1:gen:001", prebuild_frontier=before, prepublish_frontier=tampered
        )


def test_unresolved_frontier_never_falls_back_to_historical_currentness() -> None:
    unresolved_entries = copy.deepcopy(FIXTURE["frontier_before"])
    unresolved_entries[0]["resolution_state"] = "UNRESOLVED"
    unresolved = frontier("p1:frontier:unresolved", unresolved_entries)
    result = evaluate_two_point_currentness(
        generation_id="p1:gen:001", prebuild_frontier=unresolved, prepublish_frontier=unresolved
    )
    assert result["currentness"] == "UNRESOLVED"
    assert result["decision_bearing"] is False


def test_generation_zero_pointer_is_denied_at_the_g2_boundary() -> None:
    with pytest.raises(PermissionError, match="P1CDII-G2-ALG"):
        require_g2_alg_for_pointer(g2_alg_status="NOT_TAKEN")
    require_g2_alg_for_pointer(g2_alg_status="PASS")


def test_wp2_packet_stops_at_independent_g2_alg_boundary() -> None:
    packet = json.loads(
        (ROOT / "docs/programmes/p1cdi-v0-1/wp2/P1CDII_WP2_IMPLEMENTATION_PACKET_v0_1.json").read_text()
    )
    review = json.loads(
        (ROOT / "docs/programmes/p1cdi-v0-1/wp2/P1CDII_G2_ALG_REVIEW_PACKET_v0_1.json").read_text()
    )
    fresh_review = json.loads(
        (
            ROOT
            / "docs/programmes/p1cdi-v0-1/wp2/P1CDII_G2_ALG_FRESH_INDEPENDENT_REVIEW_PACKET_v0_2.json"
        ).read_text()
    )
    qa = json.loads(
        (ROOT / "docs/programmes/p1cdi-v0-1/wp2/P1CDII_WP2_QA_PACKET_v0_1.json").read_text()
    )
    completion = json.loads(
        (ROOT / "docs/programmes/p1cdi-v0-1/wp2/P1CDII_WP2_COMPLETION_RECORD_v0_1.json").read_text()
    )
    state = json.loads(
        (ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json").read_text()
    )
    remediation_qa = json.loads(
        (ROOT / "docs/programmes/p1cdi-v0-1/wp2/P1CDII_WP2_REMEDIATION_QA_PACKET_v0_1.json").read_text()
    )
    remediation_decision = json.loads(
        (ROOT / "docs/programmes/p1cdi-v0-1/wp2/P1CDII_WP2_REMEDIATION_DECISION_v0_1.json").read_text()
    )
    assert packet["authority_delta"] == "NONE"
    assert packet["status"] == "GATE_READY"
    assert packet["next_packet"] == "P1CDII-G2-ALG"
    assert qa["qa_result"] == "PASS"
    assert all(result == "PASS" or result.startswith("PASS_") for result in qa["checks"].values())
    assert review["gate_class"] == "INDEPENDENT_BLOCKING"
    assert review["status"] == "REVIEW_COMPLETE_BLOCKED"
    assert review["reviewer_binding"]["status"] == "BOUND"
    assert review["reviewer_independence"]["status"] == "DECLARED"
    assert review["gate_decision"] == "BLOCK"
    assert review["authority_delta"] == "NONE"
    assert review["decision_bearing_outputs"] == "DENIED"
    assert review["blockers"] == [
        "P1CDII_G2_ALG_BLOCK_001_PROJECTION_TYPE_COERCION",
        "P1CDII_G2_ALG_BLOCK_002_INCOMPLETE_FRONTIER_FALSE_CURRENT",
    ]
    assert fresh_review["status"] == "FRESH_REVIEW_COMPLETE_BLOCKED"
    assert fresh_review["reviewer_binding"]["status"] == "BOUND"
    assert fresh_review["reviewer_independence"]["status"] == "DECLARED"
    assert fresh_review["former_blocker_disposition"] == {
        "P1CDII_G2_ALG_BLOCK_001_PROJECTION_TYPE_COERCION": "REMEDIATED_AND_INDEPENDENTLY_REPRODUCED_PASS",
        "P1CDII_G2_ALG_BLOCK_002_INCOMPLETE_FRONTIER_FALSE_CURRENT": "REMEDIATED_AND_INDEPENDENTLY_REPRODUCED_PASS",
    }
    assert fresh_review["gate_decision"] == "BLOCK"
    assert fresh_review["authority_delta"] == "NONE"
    assert fresh_review["blockers"] == [
        "P1CDII_G2_ALG_BLOCK_003_SCHEMA_INVALID_RESOLVED_SOURCE_IDENTITY_FALSE_CURRENT"
    ]
    assert fresh_review["wp3_authorised"] is False
    assert completion["implementation_result"] == "PASS"
    assert completion["gate_decision"] == "NOT_TAKEN"
    assert completion["decision_bearing_outputs"] == "DENIED"
    assert remediation_qa["status"] == "PASS_EXACT_FINAL"
    assert remediation_qa["authority_delta"] == "NONE"
    assert remediation_qa["g2_alg_decision"] == "UNRESOLVED_REQUIRES_FRESH_INDEPENDENT_REVIEW"
    assert remediation_decision["decision"] == "PASS_REMEDIATION"
    assert remediation_decision["p1cdii_g2_alg"]["status"] == "UNRESOLVED"
    assert remediation_decision["p1cdii_g2_alg"]["remediation_author_eligible_to_issue_pass"] is False
    assert remediation_decision["wp3_authorised"] is False
    assert state["current_packet"] == "P1CDII-WP2"
    assert state["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP2"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP2-REMEDIATION"]["status"] == "COMPLETED"
    assert state["blockers"] == [
        "P1CDII_G2_ALG_BLOCK_003_SCHEMA_INVALID_RESOLVED_SOURCE_IDENTITY_FALSE_CURRENT"
    ]
    assert state["next_packet"] == "P1CDII-WP2-REMEDIATION-2"
