from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.rccr.read_models import (
    RCCRReadModelError,
    assess_rate_comparison,
    build_capability_without_demand,
    build_pilot_exit_evidence_packet,
    build_portfolio_posture,
    query_read_model,
)


ROOT = Path(__file__).resolve().parents[3]


def frontier():
    return {
        "capability_frontier_id": "frontier:test",
        "evaluation_cutoff": "2026-08-16T00:52:04Z",
        "capability_bindings": [
            {
                "capability_id": "C2P",
                "owner_programme": "OVC-C2P-PERSISTENT-STRUCTURAL-OBJECTS-CONFORMANCE-v0.2",
                "responsibility": "persistent structural identity",
                "design": "YES",
                "implementation": "YES",
                "availability": "YES",
                "qualification": "QUALIFIED_FOR_DECLARED_USE",
                "authority": "NOT_AUTHORISED",
                "activation": "INACTIVE",
                "active_stack_classification": "NON_EVALUABLE",
            },
            {
                "capability_id": "C3",
                "owner_programme": "OVC-C3",
                "responsibility": "declarative semantics",
                "design": "YES",
                "implementation": "NO",
                "availability": "NO",
                "qualification": "NOT_QUALIFIED",
                "authority": "NOT_AUTHORISED",
                "activation": "INACTIVE",
                "active_stack_classification": "NON_EVALUABLE",
            },
        ],
        "authority_effect": "NONE",
    }


def need(capability_id: str, status: str, suffix: str):
    return {
        "capability_need_assessment_id": f"need:{suffix}",
        "candidate_capability": {"capability_id": capability_id},
        "need_status": status,
        "authority_effect": "NONE",
    }


def test_capability_without_demand_preserves_implemented_vs_active_and_negative_evidence():
    model = build_capability_without_demand(
        capability_frontier=frontier(),
        need_assessments=[
            need("C2P", "NEED_CONTRADICTED", "1"),
            need("C2P", "NOT_REQUIRED", "2"),
            need("C3", "NEED_SUPPORTED", "3"),
        ],
        source_refs=["owner:C2P", "owner:C3"],
    )
    assert model["model_type"] == "CAPABILITY_WITHOUT_DEMAND"
    assert model["eligible_capability_denominator"] == 2
    assert model["zero_supported_demand_count"] == 1
    row = model["rows"][0]
    assert row["capability_id"] == "C2P"
    assert row["maturity"]["implementation"] == "YES"
    assert row["maturity"]["authority"] == "NOT_AUTHORISED"
    assert row["maturity"]["activation"] == "INACTIVE"
    assert row["need_counts"]["NEED_CONTRADICTED"] == 1
    assert row["need_counts"]["NOT_REQUIRED"] == 1
    assert row["need_counts"]["NEED_SUPPORTED"] == 0
    assert row["retirement_authority"] == "NONE"
    assert model["authority_effect"] == "NONE"


def test_capability_without_demand_rebuild_is_input_order_invariant():
    needs = [
        need("C2P", "EVIDENCE_REQUIRED", "a"),
        need("C2P", "POSSIBLY_REQUIRED", "b"),
    ]
    a = build_capability_without_demand(
        capability_frontier=frontier(),
        need_assessments=needs,
        source_refs=["b", "a"],
    )
    reversed_frontier = frontier()
    reversed_frontier["capability_bindings"].reverse()
    b = build_capability_without_demand(
        capability_frontier=reversed_frontier,
        need_assessments=list(reversed(needs)),
        source_refs=["a", "b"],
    )
    assert a == b


def test_portfolio_posture_names_denominators_and_rejects_scalar_scores():
    model = build_portfolio_posture(
        admitted_items=[
            {
                "item_id": "EC1-Q01",
                "answerability": "NOT_EVALUATED_PRE_EVIDENTIARY",
                "primary_gap": "UNASSESSED_PRE_EVIDENTIARY",
                "need_status": "UNRESOLVED",
            },
            {
                "item_id": "EC1-Q02",
                "answerability": "NOT_EVALUATED_PRE_EVIDENTIARY",
                "primary_gap": "UNASSESSED_PRE_EVIDENTIARY",
                "need_status": "NOT_REQUIRED",
            },
        ],
        evaluation_cutoff="2026-08-16T00:52:04Z",
        source_universe_id="EC1-Q01-Q10-PILOT",
    )
    assert model["eligible_item_denominator"] == 2
    assert all(row["denominator"] == 2 for row in model["answerability"])
    assert all(row["denominator"] == 2 for row in model["primary_gap"])
    assert all(row["denominator"] == 2 for row in model["need_status"])
    assert model["synthetic_completeness_score"] == "FORBIDDEN"
    assert "83%" not in json.dumps(model)

    with pytest.raises(RCCRReadModelError):
        build_portfolio_posture(
            admitted_items=[
                {
                    "item_id": "bad",
                    "answerability": "FULLY_ANSWERABLE",
                    "primary_gap": "NONE",
                    "need_status": "NOT_REQUIRED",
                    "completeness_score": 0.83,
                }
            ],
            evaluation_cutoff="2026-08-16T00:52:04Z",
            source_universe_id="bad",
        )


def test_cross_context_rate_target_and_ranking_are_denied_without_protocol():
    left = {
        "period": "2026-08-15",
        "programme_id": "RCCR",
        "population_id": "P1",
        "frontier_id": "F1",
    }
    right = {
        "period": "2026-08-16",
        "programme_id": "RCCR",
        "population_id": "P1",
        "frontier_id": "F2",
    }
    with pytest.raises(RCCRReadModelError):
        assess_rate_comparison(left_context=left, right_context=right, purpose="RANKING")
    allowed = assess_rate_comparison(
        left_context=left,
        right_context=right,
        purpose="RANKING",
        comparability_protocol_id="PROTO-COMP-1",
    )
    assert allowed["disposition"] == "ALLOW_DESCRIPTIVE"
    assert allowed["authority_effect"] == "NONE"


def test_query_surface_is_deterministic_and_read_only():
    model = build_capability_without_demand(
        capability_frontier=frontier(),
        need_assessments=[need("C2P", "NOT_REQUIRED", "1")],
    )
    result = query_read_model(model, capability_id="C2P")
    assert result["query"] == {"capability_id": "C2P"}
    assert result["rows"][0]["capability_id"] == "C2P"
    assert result["authority_effect"] == "NONE"


def test_pilot_exit_evidence_requires_complete_refs_and_preserves_denials():
    packet = build_pilot_exit_evidence_packet(
        baseline_commit="a" * 40,
        wp7a_candidate_commit="b" * 40,
        source_frontier_id="frontier:1",
        q01_q10_ref="q",
        assurance_ref="a",
        historical_validation_ref="h",
        review_load_ref="r",
        workaround_ref="w",
        capability_without_demand_ref="c",
        portfolio_posture_ref="p",
        g4_algorithmic_review_ref="g4",
        adversarial_review_ref="adv",
        fixture_currentness_ref="fx",
        fixture_resource_actuals_ref="fr",
        rollback="forward-revert WP7A only",
    )
    assert packet["scaleout_authority"] == "DENIED_UNTIL_CLASSIFIED_AND_LAWFULLY_DECIDED"
    assert packet["real_source_ec1_claims"] == "NONE"
    assert packet["authority_effect"] == "NONE"
    assert packet["evidence_packet_hash"]


def test_wp7a_plan_binding_stays_non_authoritative():
    pointer = json.loads((ROOT / "registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json").read_text())
    assert pointer["real_source_ec1_authority"] == "NONE"
    assert pointer["validation"] == "LOCKED_UNCONSUMED"
