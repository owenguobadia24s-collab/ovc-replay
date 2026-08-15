from __future__ import annotations

import pytest

from ovc.research_operations.rccr.need_review import (
    CapabilityNeedEvaluator,
    HumanReviewLedger,
    ModeVisibilityFirewall,
    OffRegisterWorkaroundDetector,
    RCCRNeedReviewError,
)
from ovc.research_operations.rccr.reference import RCCRReferenceEngine


PROFILE = {
    "requirement_profile_id": "rccr:ResearchRequirementProfile:wp5",
    "epistemic_requirements": ["R-info"],
    "evidence_requirements": ["R-evidence"],
    "population_requirements": [],
    "chronology_requirements": [],
    "inferential_requirements": [],
    "denominator_requirements": [],
    "comparability_requirements": [],
}
FRONTIER = {"capability_frontier_id": "rccr:ResearchCapabilityFrontier:wp5"}
CANDIDATE = {
    "capability_id": "C2P",
    "owner": "OVC-C2P",
    "owner_contract_ref": "contract:c2p:v0.2",
}


def info_gap():
    return RCCRReferenceEngine().assess(
        coverage_item_generation_id="coverage:wp5:g1",
        requirement_profile=PROFILE,
        capability_frontier=FRONTIER,
        requirement_evidence={
            "R-info": {
                "result": "UNSATISFIED",
                "flags": ["INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"],
                "evidence_refs": ["counterfactual:exhausted"],
            },
            "R-evidence": {"result": "SATISFIED", "flags": [], "evidence_refs": ["evidence:ok"]},
        },
        evaluation_cutoff="2026-08-15T23:20:00+01:00",
        first_valid_time="2026-08-15T23:20:00+01:00",
    )


def evaluate(**overrides):
    kwargs = {
        "coverage_assessment": info_gap(),
        "candidate_capability": CANDIDATE,
        "missing_information_claim": "persistent identity is required and absent after smaller explanations",
        "ownership_test": {
            "owner_fit": "MATCH",
            "owner_contract_current": True,
            "semantic_ownership_evidence": ["owner-contract:c2p"],
        },
        "minimality_test": {
            "smaller_route_status": "EXHAUSTED",
            "rejected_alternatives": ["method-only", "denominator-only"],
            "shadow_closure_evidence": [],
        },
        "alternative_routes": ["method-only", "denominator-only"],
        "supporting_condition": "identity remains necessary after smaller routes fail",
        "falsifying_condition": "existing information answers identity without C2P",
        "shadow_test_route": "C2P_SHADOW_ONLY",
        "next_owner_route": "C2P_OWNER_REVIEW",
        "current_support": ["owner-contract:c2p"],
        "evidence_refs": ["counterfactual:exhausted"],
        "first_valid_time": "2026-08-15T23:20:00+01:00",
    }
    kwargs.update(overrides)
    return CapabilityNeedEvaluator().evaluate(**kwargs)


def test_need_supported_requires_real_gap_owner_fit_minimality_qa_and_strong_evidence():
    result = evaluate()
    assert result["need_status"] == "NEED_SUPPORTED"
    assert result["candidate_capability"] == CANDIDATE
    assert result["authority_requested"] == "NONE"
    assert result["authority_effect"] == "NONE"


def test_existence_frequency_and_cost_have_zero_need_status_or_identity_authority():
    low = evaluate(demand_frequency=1, implementation_cost=1.0)
    high = evaluate(demand_frequency=10_000_000, implementation_cost=999_999_999.0)
    assert low == high
    assert low["need_status"] == "NEED_SUPPORTED"


def test_smaller_route_or_owner_mismatch_makes_need_not_required():
    smaller = evaluate(minimality_test={"smaller_route_status": "SMALLER_ROUTE_AVAILABLE", "rejected_alternatives": []})
    mismatch = evaluate(ownership_test={"owner_fit": "MISMATCH", "semantic_ownership_evidence": []})
    assert smaller["need_status"] == "NOT_REQUIRED"
    assert mismatch["need_status"] == "NOT_REQUIRED"


def test_missing_strong_evidence_stays_evidence_required_not_supported():
    result = evaluate(
        ownership_test={"owner_fit": "MATCH", "semantic_ownership_evidence": []},
        minimality_test={"smaller_route_status": "EXHAUSTED", "rejected_alternatives": [], "shadow_closure_evidence": []},
        current_support=[],
    )
    assert result["need_status"] == "EVIDENCE_REQUIRED"


def test_counterevidence_contradicts_need_without_authority():
    result = evaluate(current_counterevidence=["existing-route-closes-gap"])
    assert result["need_status"] == "NEED_CONTRADICTED"
    assert result["authority_effect"] == "NONE"


def test_one_need_object_names_one_exact_candidate():
    with pytest.raises(RCCRNeedReviewError):
        evaluate(candidate_capability={**CANDIDATE, "second_candidate": "C3"})


def test_av14_path2_candidate_defining_content_cannot_leak_into_path1_pre_freeze():
    result = ModeVisibilityFirewall().evaluate(
        consumer_visibility="PATH1_PRE_FREEZE",
        source_visibility="PATH2_PRE_FREEZE",
        candidate_defining=True,
    )
    assert result["disposition"] == "DENY"
    assert result["decision_use_allowed"] is False
    assert result["authority_effect"] == "NONE"


def test_av15_path1_emergent_content_cannot_leak_into_path2_without_exposure():
    result = ModeVisibilityFirewall().evaluate(
        consumer_visibility="PATH2_PRE_FREEZE",
        source_visibility="PATH1_PRE_FREEZE",
        candidate_defining=True,
        exposure_recorded=False,
    )
    assert result["disposition"] == "DENY"


def test_av16_independence_defaults_unknown_and_is_never_inferred_from_silence():
    result = ModeVisibilityFirewall().evaluate(
        consumer_visibility="PATH1_PRE_FREEZE",
        source_visibility="GENERAL_RESEARCH",
        candidate_defining=False,
    )
    assert result["origin_convergence"] == "UNKNOWN"


def test_av17_operator_material_influence_requires_explicit_influence_record():
    result = ModeVisibilityFirewall().evaluate(
        consumer_visibility="OPERATOR_RESTRICTED",
        source_visibility="PATH2_PRE_FREEZE",
        operator=True,
        decision_bearing=True,
        influence_recorded=False,
    )
    assert result["disposition"] == "INSPECT_ONLY"
    assert result["inspection_allowed"] is True
    assert result["decision_use_allowed"] is False


def test_human_review_conflict_is_unresolved_not_majority_vote():
    ledger = HumanReviewLedger()
    for review_id, reviewer, decision in [
        ("R1", "reviewer-a", "MATCH"),
        ("R2", "reviewer-b", "MISMATCH"),
        ("R3", "reviewer-c", "MATCH"),
    ]:
        ledger.enqueue(
            review_id=review_id,
            review_role="OWNER_FIT_REVIEWER",
            subject_id="need:c2p",
            reviewer_id=reviewer,
            input_refs=["owner-contract:c2p"],
            queued_at="2026-08-15T22:00:00+01:00",
        )
        ledger.complete(
            review_id=review_id,
            decision=decision,
            rationale="bounded fixture review",
            reviewed_at="2026-08-15T22:10:00+01:00",
            resolution_authority="C2P_OWNER_OR_OPERATOR",
            first_valid_time="2026-08-15T22:10:00+01:00",
        )
    disposition = ledger.subject_disposition(subject_id="need:c2p", review_role="OWNER_FIT_REVIEWER")
    assert disposition["status"] == "UNRESOLVED"
    assert disposition["reason"] == "REVIEWER_CONFLICT_NO_MAJORITY_VOTE"
    assert disposition["escalation_required"] is True


def test_human_review_telemetry_is_denominator_complete_and_descriptive_only():
    ledger = HumanReviewLedger()
    ledger.enqueue(
        review_id="R1",
        review_role="MINIMALITY_REVIEWER",
        subject_id="need:c2p",
        reviewer_id="reviewer-a",
        input_refs=["alternative:method"],
        queued_at="2026-08-15T22:00:00+01:00",
    )
    ledger.complete(
        review_id="R1",
        decision="EXHAUSTED",
        rationale="smaller routes rejected",
        reviewed_at="2026-08-15T22:05:00+01:00",
        resolution_authority="RCCR_REVIEW_ONLY",
        first_valid_time="2026-08-15T22:05:00+01:00",
    )
    ledger.enqueue(
        review_id="R2",
        review_role="MODE_FIREWALL_REVIEWER",
        subject_id="mode:edge",
        reviewer_id="reviewer-b",
        input_refs=["exposure:ledger"],
        queued_at="2026-08-15T22:10:00+01:00",
    )
    metrics = ledger.telemetry(cutoff="2026-08-15T22:20:00+01:00")
    assert metrics["review_route_count"] == 2
    assert metrics["completed_count"] == 1
    assert metrics["pending_count"] == 1
    assert metrics["latency_denominator"] == 1
    assert metrics["pending_queue_age_denominator"] == 1
    assert metrics["reopen_rate_denominator"] == 2
    assert metrics["metric_use"] == "DESCRIPTIVE_DIAGNOSTIC_ONLY"


def test_workaround_detector_exists_before_console_and_requires_provenance_for_decision_bearing_rationale():
    detector = OffRegisterWorkaroundDetector()
    detector.record_route_attempt()
    detector.record_route_attempt()
    detector.record_workaround(
        workaround_id="WA-1",
        attempted_route="READ_ONLY_REVIEW",
        blocked_cause="NO_GOVERNED_WRITE_ROUTE",
        workaround_class="EXTERNAL_NOTE",
        burden="LOW",
        resolution="IMPORT_IF_DECISION_BEARING",
        escalation="NONE",
        first_valid_time="2026-08-15T22:30:00+01:00",
    )
    summary = detector.summary()
    assert summary["route_attempt_denominator"] == 2
    assert summary["workaround_count"] == 1
    assert summary["workaround_rate"] == 0.5
    assert summary["metric_use"] == "OPERATIONAL_DIAGNOSTIC_ONLY"
    with pytest.raises(RCCRNeedReviewError):
        detector.record_workaround(
            workaround_id="WA-2",
            attempted_route="READ_ONLY_REVIEW",
            blocked_cause="NO_GOVERNED_WRITE_ROUTE",
            workaround_class="EXTERNAL_NOTE",
            burden="LOW",
            resolution="USE_EXTERNAL_RATIONALE",
            escalation="OWNER",
            first_valid_time="2026-08-15T22:31:00+01:00",
            decision_bearing_external_rationale=True,
        )
