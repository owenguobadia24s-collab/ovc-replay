from __future__ import annotations

import pytest

from ovc.opt_b.esl.c3_language import (
    C3ESLConformanceError,
    assert_no_explanation_in_canonical_path,
    build_c3_esl_dependency_manifest,
    build_c3_esl_proposition,
    build_c3_esl_statement_ast,
    build_c3_explanation_record,
    render_c3_esl_statement,
    request_bridge_maturity,
)


def _manifest():
    return build_c3_esl_dependency_manifest(
        manifest_id="C3.ESL.TEST.MANIFEST.v1",
        template_id="C3.ESL.TEST.TEMPLATE.v1",
        dependencies=[
            {"clause_type":"STRUCTURAL_STATE","role":"REQUIRED","source_owner":"ESL","source_type":"STRUCTURAL_OCCURRENCE"},
            {"clause_type":"ORGANISATION","role":"OPTIONAL","source_owner":"SOI","source_type":"ORGANISATION_EVIDENCE"},
            {"clause_type":"CONSTRAINT","role":"OPTIONAL","source_owner":"CEI","source_type":"CONSTRAINT_EVIDENCE"},
        ],
    )


def _p(ptype, ref):
    return build_c3_esl_proposition(
        proposition_type=ptype,
        source_ref=ref,
        source_owner="ESL" if ptype == "STRUCTURAL_OCCURRENCE" else "SOI",
        resolution_state="RESOLVED",
        first_valid_time="2026-06-01T00:15:00Z",
        evaluation_cutoff="2026-06-01T00:15:00Z",
        generation_refs=["GEN.v1"],
        dependency_manifest_id="C3.ESL.TEST.MANIFEST.v1",
    )


def test_wp10_optional_organisation_and_constraint_are_omitted_not_fabricated():
    manifest = _manifest()
    structural = _p("STRUCTURAL_OCCURRENCE", "so1:test")
    ast = build_c3_esl_statement_ast(anchor_ref="so1:test", propositions=[structural], dependency_manifest=manifest, template_id="C3.ESL.TEST.TEMPLATE.v1")
    decisions = {x["clause_type"]: x for x in ast["clause_decisions"]}
    assert decisions["STRUCTURAL_STATE"]["decision"] == "INCLUDE"
    assert decisions["ORGANISATION"]["decision"] == "OMIT"
    assert decisions["CONSTRAINT"]["decision"] == "OMIT"
    text, trace = render_c3_esl_statement(ast)
    assert "inactive reference AST" in text
    assert trace["llm_nodes"] == []


def test_wp10_required_missing_is_unresolved_not_negative_truth():
    ast = build_c3_esl_statement_ast(anchor_ref="so1:test", propositions=[], dependency_manifest=_manifest(), template_id="C3.ESL.TEST.TEMPLATE.v1")
    structural = next(x for x in ast["clause_decisions"] if x["clause_type"] == "STRUCTURAL_STATE")
    assert structural["decision"] == "UNRESOLVED"
    assert structural["reason_code"] == "REQUIRED_CLAUSE_SOURCE_UNAVAILABLE"


def test_wp10_active_term_or_bridge_activation_remains_operator_reserved():
    with pytest.raises(C3ESLConformanceError, match="ACTIVE_TERM_OPERATOR_RESERVED"):
        build_c3_esl_proposition(
            proposition_type="EPISTEMIC_STATUS", source_ref="stg1:x", source_owner="ESL", resolution_state="RESOLVED",
            first_valid_time="2026-06-01T00:15:00Z", evaluation_cutoff="2026-06-01T00:15:00Z", generation_refs=["GEN.v1"],
            dependency_manifest_id="m", term_generation_id="stg1:x", term_admission_state="ADMITTED_ACTIVE",
        )
    with pytest.raises(C3ESLConformanceError, match="ACTIVATION_RECORD_MISSING"):
        request_bridge_maturity("SHADOW_EVALUATION")
    with pytest.raises(C3ESLConformanceError, match="OPERATOR_RESERVED"):
        request_bridge_maturity("PRODUCTION_GRAMMAR", authority_record_id="decision:x", vocabulary_binding_id="vocab:x")


def test_wp10_explanation_is_noncanonical_and_cannot_enter_render_trace():
    p = _p("STRUCTURAL_OCCURRENCE", "so1:test")
    ast = build_c3_esl_statement_ast(anchor_ref="so1:test", propositions=[p], dependency_manifest=_manifest(), template_id="C3.ESL.TEST.TEMPLATE.v1")
    _, trace = render_c3_esl_statement(ast)
    explanation = build_c3_explanation_record(statement_ref=ast["statement_id"], generated_text="non-canonical explanation", generator_metadata={"model":"test"}, provenance_refs=[trace["render_trace_id"]])
    assert explanation["authority"] == "NON_CANONICAL"
    assert explanation["identity_projection"] == "EXCLUDED"
    assert_no_explanation_in_canonical_path(render_trace=trace, explanation=explanation)
    poisoned = dict(trace)
    poisoned["llm_nodes"] = [explanation["explanation_id"]]
    with pytest.raises(C3ESLConformanceError, match="LLM_CANONICAL_PATH_FORBIDDEN"):
        assert_no_explanation_in_canonical_path(render_trace=poisoned)


def test_wp10_history_creates_new_statement_generation_without_mutating_predecessor():
    manifest = _manifest()
    p = _p("STRUCTURAL_OCCURRENCE", "so1:test")
    first = build_c3_esl_statement_ast(anchor_ref="so1:test", propositions=[p], dependency_manifest=manifest, template_id="C3.ESL.TEST.TEMPLATE.v1")
    org = _p("ORGANISATION_EVIDENCE", "org:test")
    second = build_c3_esl_statement_ast(anchor_ref="so1:test", propositions=[p, org], dependency_manifest=manifest, template_id="C3.ESL.TEST.TEMPLATE.v1", predecessor_statement_id=first["statement_id"])
    assert first["statement_id"] != second["statement_id"]
    assert second["predecessor_statement_id"] == first["statement_id"]
    assert second["generation_policy"] == "APPEND_ONLY_NEW_GENERATION"
