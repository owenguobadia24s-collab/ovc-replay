from __future__ import annotations

import pytest

from ovc.research_operations.rccr.reference import RCCRReferenceEngine

PROFILE = {
    "requirement_profile_id": "rccr:ResearchRequirementProfile:golden",
    "epistemic_requirements": ["R1"],
    "evidence_requirements": [],
    "population_requirements": [],
    "chronology_requirements": [],
    "inferential_requirements": [],
    "denominator_requirements": [],
    "comparability_requirements": [],
}
FRONTIER = {"capability_frontier_id": "rccr:ResearchCapabilityFrontier:golden"}


@pytest.mark.parametrize(
    "case_id,result_state,flags,protocol_state,expected_gap,expected_coverage,expected_logical_class",
    [
        ("G01", "SATISFIED", [], "VALID", "NONE", "FULL", "CURRENT_STACK_SUFFICIENT"),
        ("G02", "UNSATISFIED", ["METHOD_GAP"], "VALID", "METHOD_GAP", "NONE", "METHOD_GAP"),
        ("G03", "UNSATISFIED", ["DENOMINATOR_GAP"], "VALID", "DENOMINATOR_GAP", "NONE", "DENOMINATOR_GAP"),
        ("G04", "UNSATISFIED", ["DATA_GAP"], "VALID", "DATA_GAP", "NONE", "DATA_GAP"),
        ("G05", "UNSATISFIED", ["OWNER_SEMANTICS_GAP"], "VALID", "OWNER_SEMANTICS_GAP", "NONE", "OWNER_SEMANTICS_GAP"),
        ("G06", "UNSATISFIED", ["IMPLEMENTATION_GAP"], "VALID", "IMPLEMENTATION_GAP", "NONE", "IMPLEMENTATION_GAP"),
        ("G07", "UNSATISFIED", ["AUTHORITY_GAP"], "VALID", "AUTHORITY_GAP", "NONE", "AUTHORITY_GAP"),
        ("G08", "SATISFIED", [], "EXCLUDED", "PROTOCOL_EXCLUSION", "NONE", "PROTOCOL_EXCLUSION"),
        ("G09", "UNSATISFIED", ["INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"], "VALID", "INFORMATION_GAP", "NONE", "GENUINE_INFORMATION_GAP"),
        ("G10", "NOT_EVALUABLE", ["METHOD_INFORMATION_ENTANGLED"], "VALID", "UNRESOLVED_GAP", "UNRESOLVED", "UNRESOLVED_GAP"),
    ],
)
def test_golden_reference_cases(case_id, result_state, flags, protocol_state, expected_gap, expected_coverage, expected_logical_class):
    assessment = RCCRReferenceEngine().assess(
        coverage_item_generation_id=f"coverage:{case_id}",
        requirement_profile=PROFILE,
        capability_frontier=FRONTIER,
        requirement_evidence={"R1": {"result": result_state, "flags": flags, "evidence_refs": [case_id]}},
        evaluation_cutoff="2026-08-15T21:00:00+01:00",
        protocol_state=protocol_state,
        first_valid_time="2026-08-15T21:00:00+01:00",
    )
    row = assessment["requirement_results"][0]
    assert row["gap_class"] == expected_gap
    assert assessment["coverage_status"] == expected_coverage
    assert assessment["authority_effect"] == "NONE"
    if expected_logical_class == "CURRENT_STACK_SUFFICIENT":
        assert row["result"] == "SATISFIED"
    elif expected_logical_class == "GENUINE_INFORMATION_GAP":
        assert row["gap_class"] == "INFORMATION_GAP"
    else:
        assert expected_logical_class in {row["gap_class"], "PROTOCOL_EXCLUSION", "UNRESOLVED_GAP"}
