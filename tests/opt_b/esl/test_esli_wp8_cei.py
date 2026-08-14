from __future__ import annotations

import pytest

from ovc.opt_b.esl.cei import (
    CEIError,
    build_condition,
    build_constraint_evidence,
    build_contrast_spec,
    build_population_manifest,
    render_condition,
    validate_constraint_ast,
)


def _field(path: str = "session") -> dict:
    return {"type": "FIELD_REF", "source_namespace": "OccurrenceContext", "field_path": path, "source_authority": "LAWFUL_UPSTREAM"}


def _condition(name: str, role: str = "PRE_EXISTING", value: str = "LONDON") -> dict:
    return build_condition(
        name=name,
        condition_type="TEMPORAL",
        temporal_role=role,
        source_ref="ctx:fixture:v1",
        first_valid_time="2026-06-10T07:00:00Z" if role != "POST_TARGET" else "2026-06-10T10:00:00Z",
        target_anchor_time="2026-06-10T08:00:00Z",
        ast={"type": "ENUM_MATCH", "children": [_field(), {"type": "CONST", "value": value}]},
    )


def test_closed_ast_rejects_causal_predicate() -> None:
    with pytest.raises(CEIError, match="CEI_AST_NODE_TYPE_NOT_REGISTERED"):
        validate_constraint_ast({"type": "CAUSES", "children": [_field(), {"type": "CONST", "value": "X"}]})


def test_ast_rejects_mechanism_or_outcome_tokens() -> None:
    with pytest.raises(CEIError, match="CEI_FORBIDDEN_CAUSAL_OR_OUTCOME"):
        validate_constraint_ast({"type": "ENUM_MATCH", "children": [_field("mechanism"), {"type": "CONST", "value": "dealer intent"}]})


def test_condition_requires_lawful_source_and_no_backdating() -> None:
    with pytest.raises(CEIError, match="CEI_RETROSPECTIVE_PRECONDITION_FORBIDDEN"):
        build_condition(name="late", condition_type="AUXILIARY", temporal_role="PRE_EXISTING", source_ref="x", first_valid_time="2026-06-10T09:00:00Z", target_anchor_time="2026-06-10T08:00:00Z", ast=_field())


def test_concurrent_and_post_target_cannot_render_as_preconditions() -> None:
    for role in ("CONCURRENT", "TIME_VARYING_DURING_TARGET", "POST_TARGET"):
        condition = _condition("observed condition", role=role)
        assert condition["render_as_precondition"] is False
        with pytest.raises(CEIError, match="CEI_RETROSPECTIVE_PRECONDITION_RENDER_FORBIDDEN"):
            render_condition(condition, as_precondition=True)


def test_population_reconciles_every_eligible_occurrence() -> None:
    with pytest.raises(CEIError, match="CEI_POPULATION_RECONCILIATION_INCOMPLETE"):
        build_population_manifest(population_id="p1", eligible_occurrence_ids=["o1", "o2"], states={"o1": "CONDITION_A"}, sample_unit="StructuralOccurrence", chronology_partition="JUNE", comparability_domain_id="cmp1")
    population = build_population_manifest(population_id="p1", eligible_occurrence_ids=["o1", "o2"], states={"o1": "CONDITION_A", "o2": "COMPARATOR_B"}, sample_unit="StructuralOccurrence", chronology_partition="JUNE", comparability_domain_id="cmp1")
    assert population["counts"]["CONDITION_A"] == 1
    assert population["counts"]["COMPARATOR_B"] == 1


def test_comparator_is_exact_and_method_neutral_without_threshold_selection() -> None:
    a = _condition("London", value="LONDON")
    b = _condition("New York", value="NEW_YORK")
    contrast = build_contrast_spec(condition_a=a, comparator_b=b, comparison_design="STRATIFIED", denominator_name="eligible occurrences", metric_ids=["incidence_rate"], confounding_fields=["month"])
    assert contrast["method_neutral"] is True
    assert contrast["matching_or_support_threshold"] is None
    assert contrast["causal_adjustment_claim"] == "FORBIDDEN"


def test_constraint_evidence_is_descriptive_only() -> None:
    a = _condition("London", value="LONDON")
    b = _condition("New York", value="NEW_YORK")
    pop = build_population_manifest(population_id="p1", eligible_occurrence_ids=["o1", "o2"], states={"o1": "CONDITION_A", "o2": "COMPARATOR_B"}, sample_unit="StructuralOccurrence", chronology_partition="JUNE", comparability_domain_id="cmp1")
    contrast = build_contrast_spec(condition_a=a, comparator_b=b, comparison_design="CHRONOLOGICAL", denominator_name="eligible occurrences", metric_ids=["incidence_rate"])
    evidence = build_constraint_evidence(target="EMERGENCE", condition_a=a, comparator_b=b, population=pop, contrast=contrast, metrics=[{"metric_id": "incidence_rate", "condition_a_numerator": 1, "condition_a_denominator": 1, "comparator_b_numerator": 0, "comparator_b_denominator": 1}])
    assert evidence["interpretation_class"] == "DESCRIPTIVE_CONDITIONAL_ASSOCIATION_ONLY"
    assert evidence["mechanism_handoff"] == "RESEARCH_OPERATIONS_ONLY"
    assert evidence["authority"]["authority_effect"] == "NONE"


def test_constraint_evidence_rejects_outcome_fields() -> None:
    a = _condition("London", value="LONDON")
    b = _condition("New York", value="NEW_YORK")
    pop = build_population_manifest(population_id="p1", eligible_occurrence_ids=["o1", "o2"], states={"o1": "CONDITION_A", "o2": "COMPARATOR_B"}, sample_unit="StructuralOccurrence", chronology_partition="JUNE", comparability_domain_id="cmp1")
    contrast = build_contrast_spec(condition_a=a, comparator_b=b, comparison_design="STRATIFIED", denominator_name="eligible occurrences", metric_ids=["incidence_rate"])
    with pytest.raises(CEIError, match="CEI_FORBIDDEN_CAUSAL_OR_OUTCOME"):
        build_constraint_evidence(target="EMERGENCE", condition_a=a, comparator_b=b, population=pop, contrast=contrast, metrics=[{"metric_id": "incidence_rate", "expected_return": "0.1"}])
