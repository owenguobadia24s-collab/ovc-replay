import pytest

from ovc.opt_b.esl.read_model import ESLReadModelError, assert_projection_fidelity, build_esl_read_model, build_read_model_section


def _section(payload=None, denominator=None):
    return build_read_model_section(
        section_type="STRUCTURAL_OCCURRENCE",
        source_ref="so1:fixture",
        source_owner="ESL",
        source_generation="ESL.GEN.v1",
        evaluation_cutoff="2026-06-01T00:15:00Z",
        first_valid_time="2026-06-01T00:15:00Z",
        evidence_state="AVAILABLE",
        authority_state="INACTIVE_CONFORMANCE_ONLY",
        lineage_refs=["c2:1", "ef:1"],
        payload=payload or {"location":"ABOVE_REFERENCE","motion":"DISPLACEMENT"},
        denominator=denominator,
    )


def test_wp12_read_model_is_read_only_source_bound_and_fidelity_preserving():
    section = _section(denominator={"eligible_universe":100,"denominator":90,"excluded":10})
    model = build_esl_read_model(sections=[section], source_frontier_ref="ef:1", console_authority="READ_ONLY")
    assert model["mutation_routes"] == []
    assert model["frontend_scientific_calculation"] == "FORBIDDEN"
    assert model["sections"][0]["denominator"]["denominator"] == 90
    assert_projection_fidelity(read_model=model, source_sections=[section])


def test_wp12_rejects_frontend_scientific_computation_fields():
    with pytest.raises(ESLReadModelError, match="FRONTEND_SCIENCE_FORBIDDEN"):
        _section(payload={"candidate_strength_score":0.9})
    with pytest.raises(ESLReadModelError, match="FRONTEND_SCIENCE_FORBIDDEN"):
        _section(payload={"best_profile":"FULL_RESEARCH"})


def test_wp12_rejects_non_read_only_console_authority():
    section = _section()
    with pytest.raises(ESLReadModelError, match="CONSOLE_AUTHORITY_NOT_READ_ONLY"):
        build_esl_read_model(sections=[section], source_frontier_ref="ef:1", console_authority="WRITE")


def test_wp12_requires_explicit_denominator_shape_when_present():
    with pytest.raises(ESLReadModelError, match="DENOMINATOR_EXPLICIT_REQUIRED"):
        _section(denominator={"rate":0.5})
