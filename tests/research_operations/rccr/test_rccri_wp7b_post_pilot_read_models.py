from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.rccr.post_pilot_read_models import (
    RCCRReadModelError,
    build_ec1_rv_review_projection,
    build_gap_queues,
    build_next_research_routes,
    build_path_correspondence,
    build_post_pilot_read_models,
    build_research_coverage_matrix,
)

ROOT = Path(__file__).resolve().parents[3]


def rows():
    return [
        {
            "item_id": "P1-001",
            "requirement_id": "REQ-1",
            "path": "PATH_1",
            "answerability": "PARTIAL",
            "primary_gap": "METHOD_GAP",
            "secondary_gaps": ["DATA_GAP"],
            "need_status": "EVIDENCE_REQUIRED",
            "source_ref": "source:p1:1",
            "independence_state": "INDEPENDENT",
            "exposure_state": "UNEXPOSED",
            "authority_effect": "NONE",
        },
        {
            "item_id": "P2-001",
            "requirement_id": "REQ-2",
            "path": "PATH_2",
            "answerability": "PARTIAL",
            "primary_gap": "IMPLEMENTATION_GAP",
            "secondary_gaps": [],
            "need_status": "POSSIBLY_REQUIRED",
            "capability_id": "C3",
            "source_ref": "source:p2:1",
            "independence_state": "PARTIALLY_INDEPENDENT",
            "exposure_state": "PRE_OUTCOME_EXPOSED",
            "authority_effect": "NONE",
        },
        {
            "item_id": "EXT-001",
            "requirement_id": "REQ-3",
            "path": "PATH_2",
            "answerability": "NOT_ANSWERABLE",
            "primary_gap": "INFORMATION_GAP",
            "secondary_gaps": [],
            "need_status": "UNRESOLVED",
            "source_ref": "source:external:1",
            "independence_state": "INDEPENDENT",
            "exposure_state": "UNEXPOSED",
            "authority_effect": "NONE",
        },
    ]


def common():
    return {
        "evaluation_cutoff": "2026-08-16T22:30:00Z",
        "source_universe_id": "RCCR-BROAD-WAVE-1",
    }


def test_coverage_matrix_is_source_native_deterministic_and_denominator_bound():
    a = build_research_coverage_matrix(assessments=rows(), **common())
    b = build_research_coverage_matrix(assessments=list(reversed(rows())), **common())
    assert a == b
    assert a["model_type"] == "RESEARCH_COVERAGE_MATRIX"
    assert a["eligible_item_denominator"] == 3
    assert all(row["source_ref"] for row in a["rows"])
    assert a["authority_effect"] == "NONE"
    assert "completeness_score" not in json.dumps(a).lower()


def test_gap_queues_enforce_method_first_and_strict_architecture_pressure():
    model = build_gap_queues(assessments=rows(), **common())
    assert [row["item_id"] for row in model["method_first"]] == ["P1-001"]
    assert [row["item_id"] for row in model["architecture_pressure"]] == ["P2-001"]
    assert model["queues"]["INFORMATION_GAP"][0]["item_id"] == "EXT-001"
    assert model["authority_effect"] == "NONE"


def test_correspondence_preserves_path_independence_and_exposure_without_ranking():
    model = build_path_correspondence(assessments=rows(), **common())
    assert {row["path"] for row in model["rows"]} == {"PATH_1", "PATH_2"}
    p1 = next(row for row in model["rows"] if row["item_id"] == "P1-001")
    assert p1["independence_state"] == "INDEPENDENT"
    assert p1["exposure_state"] == "UNEXPOSED"
    assert model["cross_path_ranking"] == "FORBIDDEN_WITHOUT_SEPARATE_PROTOCOL"


def test_next_route_is_descriptive_and_does_not_effectuate_priority_or_owner_action():
    model = build_next_research_routes(assessments=rows(), **common())
    by_id = {row["item_id"]: row for row in model["rows"]}
    assert by_id["P1-001"]["next_route"] == "METHOD_FIRST"
    assert by_id["EXT-001"]["next_route"] == "EXTERNAL_RESEARCH_DELTA"
    assert by_id["P2-001"]["next_route"] == "OWNER_IMPLEMENTATION_REVIEW"
    assert all(row["priority_score"] is None for row in model["rows"])
    assert all(row["effectuation_authority"] == "NONE" for row in model["rows"])


def test_ec1_rv_projection_fails_closed_before_lawfully_assured_e1_r1():
    deferred = build_ec1_rv_review_projection(evidence_records=[], e1_r1_assured=False, **common())
    assert deferred["availability"] == "DEFERRED_PENDING_LAWFULLY_ASSURED_E1_R1"
    assert deferred["rows"] == []
    with pytest.raises(RCCRReadModelError):
        build_ec1_rv_review_projection(
            evidence_records=[{"review_id": "RV-1", "source_ref": "e1:r1:1", "authority_effect": "NONE"}],
            e1_r1_assured=False,
            **common(),
        )


def test_ec1_rv_projection_only_projects_owner_evidence_after_assurance():
    model = build_ec1_rv_review_projection(
        evidence_records=[
            {
                "review_id": "RV-1",
                "question_id": "EC1-Q01",
                "review_state": "READY_FOR_REVIEW",
                "source_ref": "owner-evidence:e1-r1:1",
                "authority_effect": "NONE",
            }
        ],
        e1_r1_assured=True,
        **common(),
    )
    assert model["availability"] == "SOURCE_BOUND_E1_R1_ASSURED"
    assert model["rows"][0]["source_ref"] == "owner-evidence:e1-r1:1"
    assert model["scientific_claims"] == "NONE_RCCR_ONLY_PROJECTS_OWNER_EVIDENCE"


def test_bundle_is_rebuild_equivalent_and_console_writes_remain_denied():
    a = build_post_pilot_read_models(
        assessments=rows(),
        ec1_rv_records=[],
        e1_r1_assured=False,
        **common(),
    )
    b = build_post_pilot_read_models(
        assessments=list(reversed(rows())),
        ec1_rv_records=[],
        e1_r1_assured=False,
        **common(),
    )
    assert a == b
    assert a["console_get_adapter"] == "DEFERRED_OPTIONAL_NOT_CORRECTNESS_PREREQUISITE"
    assert a["write_routes"] == "DENIED"
    assert a["authority_effect"] == "NONE"


def test_wp7b_follows_integrated_wp6b_without_consuming_owner_authority():
    pointer = json.loads((ROOT / "registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json").read_text())
    assert pointer["current_packet"] == "RCCRI-WP7B"
    assert pointer["current_gate"] == "RCCRI-G7B"
    assert pointer["last_completed_packet"] == "RCCRI-WP6B"
    assert pointer["last_merge_commit"] == "34d08c26061f8548346bdec101e2af6f3138f9bc"
    assert pointer["owner_authority_frontier"]["ec1"]["state"] == "AUTHORISED_BOUNDED"
    assert pointer["rccr_consumption_boundary"]["real_source_ec1_consumption"] == "DENIED_BY_RCCRI_WP6B_SCOPE"
    assert pointer["rccr_consumption_boundary"]["path2_real_source_consumption"] == "DENIED_BY_RCCRI_WP6B_SCOPE"
    assert pointer["rccr_consumption_boundary"]["owner_capability_activation"] == "DENIED"
    assert pointer["rccr_consumption_boundary"]["validation_consumption"] == "DENIED"
    assert pointer["authority_effect"] == "NONE"
