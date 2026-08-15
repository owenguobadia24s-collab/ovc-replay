from __future__ import annotations

from copy import deepcopy

from ovc.research_operations.rccr.reference import RCCRReferenceEngine, reference_replay_digest


PROFILE = {
    "requirement_profile_id": "rccr:ResearchRequirementProfile:test",
    "epistemic_requirements": ["R-epistemic"],
    "evidence_requirements": ["R-evidence"],
    "population_requirements": [],
    "chronology_requirements": [],
    "inferential_requirements": [],
    "denominator_requirements": [],
    "comparability_requirements": [],
}
FRONTIER = {"capability_frontier_id": "rccr:ResearchCapabilityFrontier:test"}


def assess(evidence, **kwargs):
    return RCCRReferenceEngine().assess(
        coverage_item_generation_id="coverage:test:g1",
        requirement_profile=PROFILE,
        capability_frontier=FRONTIER,
        requirement_evidence=evidence,
        evaluation_cutoff="2026-08-15T21:00:00+01:00",
        first_valid_time="2026-08-15T21:00:00+01:00",
        **kwargs,
    )


def satisfied(ref):
    return {"result": "SATISFIED", "flags": [], "evidence_refs": [ref]}


def test_full_coverage_is_requirement_vector_not_scalar_score():
    result = assess({"R-epistemic": satisfied("e1"), "R-evidence": satisfied("e2")})
    assert result["answerability_state"] == "FULLY_ANSWERABLE"
    assert result["coverage_status"] == "FULL"
    assert all(row["result"] == "SATISFIED" for row in result["requirement_results"])
    assert result["gap_assessments"] == []
    assert "score" not in result
    assert "coverage_score" not in result
    assert result["authority_effect"] == "NONE"


def test_diagnostic_precedence_method_beats_information_absence():
    result = assess(
        {
            "R-epistemic": {
                "result": "UNSATISFIED",
                "flags": ["INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED", "METHOD_GAP"],
                "evidence_refs": ["x"],
            },
            "R-evidence": satisfied("e2"),
        }
    )
    gap = result["gap_assessments"][0]
    assert gap["gap_class"] == "METHOD_GAP"
    assert gap["reason"] == "METHOD_GAP"


def test_method_information_entanglement_remains_unresolved():
    result = assess(
        {
            "R-epistemic": {
                "result": "NOT_EVALUABLE",
                "flags": ["METHOD_INFORMATION_ENTANGLED", "INFORMATION_GAP"],
            },
            "R-evidence": satisfied("e2"),
        }
    )
    gap = result["gap_assessments"][0]
    assert gap["gap_class"] == "UNRESOLVED_GAP"
    assert gap["reason"] == "METHOD_INFORMATION_ENTANGLED"
    assert result["QA_state"] == "WARN"


def test_information_gap_is_last_resort_and_requires_counterfactual_exhaustion():
    result = assess(
        {
            "R-epistemic": {"result": "UNSATISFIED", "flags": ["INFORMATION_GAP"]},
            "R-evidence": satisfied("e2"),
        }
    )
    gap = result["gap_assessments"][0]
    assert gap["gap_class"] == "UNRESOLVED_GAP"
    assert gap["reason"] == "INFORMATION_GAP_COUNTERFACTUAL_NOT_EXHAUSTED"
    assert result["counterfactual_sufficiency_review"]["information_absence_is_last_resort"] is True


def test_counterfactual_exhausted_information_gap_can_only_request_more_evidence_not_activation():
    result = assess(
        {
            "R-epistemic": {
                "result": "UNSATISFIED",
                "flags": ["INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"],
                "evidence_refs": ["owner-proof"],
            },
            "R-evidence": satisfied("e2"),
        }
    )
    gap = result["gap_assessments"][0]
    assert gap["gap_class"] == "INFORMATION_GAP"
    need = RCCRReferenceEngine().capability_need(
        coverage_assessment=result,
        candidate_capability={
            "capability_id": "C2P",
            "owner": "OVC-C2P",
            "owner_contract_ref": "contract:c2p:v0.2",
        },
        missing_information_claim="persistent identity is absent",
        alternative_routes=["owner-semantic clarification", "method-only challenge"],
        supporting_condition="same-object identity remains required after smaller explanations fail",
        falsifying_condition="existing owner evidence answers identity without C2P",
        shadow_test_route="C2P_SHADOW_ONLY",
        next_owner_route="C2P_OWNER_REVIEW",
        current_support=["owner-proof"],
        first_valid_time="2026-08-15T21:00:00+01:00",
    )
    assert need["need_status"] == "EVIDENCE_REQUIRED"
    assert need["authority_requested"] == "NONE"
    assert need["authority_effect"] == "NONE"
    assert need["candidate_capability"]["capability_id"] == "C2P"


def test_missing_requirement_evidence_is_explicit_unresolved_no_silent_sampling():
    result = assess({"R-epistemic": satisfied("e1")})
    rows = {row["requirement_id"]: row for row in result["requirement_results"]}
    assert set(rows) == {"R-epistemic", "R-evidence"}
    assert rows["R-evidence"]["result"] == "NOT_EVALUABLE"
    assert rows["R-evidence"]["gap_class"] == "UNRESOLVED_GAP"
    assert rows["R-evidence"]["reason"] == "MISSING_REQUIREMENT_EVIDENCE"


def test_protocol_invalid_and_out_of_scope_precede_lower_gap_signals():
    invalid = assess(
        {"R-epistemic": satisfied("e1"), "R-evidence": satisfied("e2")},
        protocol_state="INVALID",
    )
    assert invalid["answerability_state"] == "INVALID_QUESTION_CURRENT_PROTOCOL"
    assert invalid["coverage_status"] == "NOT_APPLICABLE"
    assert all(row["gap_class"] == "PROTOCOL_EXCLUSION" for row in invalid["requirement_results"])
    out = assess(
        {"R-epistemic": satisfied("e1"), "R-evidence": satisfied("e2")},
        protocol_state="OUT_OF_SCOPE",
    )
    assert out["answerability_state"] == "OUT_OF_SCOPE_CURRENT_PROTOCOL"
    assert all(row["gap_class"] == "OUT_OF_SCOPE" for row in out["requirement_results"])


def test_requirement_and_evidence_input_order_does_not_change_assessment_identity():
    left = assess({"R-evidence": satisfied("e2"), "R-epistemic": satisfied("e1")})
    right = assess({"R-epistemic": satisfied("e1"), "R-evidence": satisfied("e2")})
    assert left == right
    assert left["coverage_assessment_id"] == right["coverage_assessment_id"]


def test_reference_replay_digest_is_order_invariant_and_never_top_n():
    a = assess({"R-epistemic": satisfied("e1"), "R-evidence": satisfied("e2")})
    b = deepcopy(a)
    b["coverage_item_generation_id"] = "coverage:test:g2"
    b["coverage_assessment_id"] = "different-id-for-digest-test"
    assert reference_replay_digest([a, b]) == reference_replay_digest([b, a])


def test_counterevidence_can_contradict_need_without_granting_authority():
    result = assess(
        {
            "R-epistemic": {
                "result": "UNSATISFIED",
                "flags": ["INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"],
            },
            "R-evidence": satisfied("e2"),
        }
    )
    need = RCCRReferenceEngine().capability_need(
        coverage_assessment=result,
        candidate_capability={
            "capability_id": "C2P",
            "owner": "OVC-C2P",
            "owner_contract_ref": "contract:c2p:v0.2",
        },
        missing_information_claim="persistent identity is absent",
        alternative_routes=["existing-owner-route"],
        supporting_condition="owner cannot answer",
        falsifying_condition="owner can answer",
        shadow_test_route="C2P_SHADOW_ONLY",
        next_owner_route="C2P_OWNER_REVIEW",
        current_counterevidence=["existing-owner-answer"],
        first_valid_time="2026-08-15T21:00:00+01:00",
    )
    assert need["need_status"] == "NEED_CONTRADICTED"
    assert need["authority_effect"] == "NONE"


def test_every_requirement_row_carries_decision_trace_for_independent_review():
    result = assess({"R-epistemic": satisfied("e1"), "R-evidence": satisfied("e2")})
    for row in result["requirement_results"]:
        steps = [step["step"] for step in row["decision_trace"]]
        assert steps == ["RESULT", "FLAGS", "DIAGNOSTIC_PRECEDENCE", "SELECTED_GAP", "REASON"]
