from __future__ import annotations

import pytest

from ovc.opt_b.esl.term_qualification import (
    TermQualificationError,
    build_language_candidate_binding,
    build_semantic_admission_proposal,
    build_structural_term_candidate,
    build_term_challenge,
    build_term_qualification_record,
    build_term_qualification_rule_pack,
    build_transport_candidate,
)


def _candidate():
    return build_structural_term_candidate(
        machine_symbol="STRUCTURAL_TEST_TERM",
        term_class="OBSERVABLE_PROPERTY",
        formal_definition={"predicate":"HAS_FACET","facet":"MOTION"},
        observation_unit="StructuralOccurrence",
        temporal_semantics={"mode":"AT_CUTOFF"},
        inclusion_predicates=["MOTION_AVAILABLE"],
        exclusion_predicates=["MOTION_NOT_EVALUABLE"],
        boundary_cases=["MOTION_AMBIGUOUS"],
        ambiguity_policy="PRESERVE",
        missingness_policy="ABSTAIN",
        observable_implications=["MOTION facet is observable"],
        falsifiers=["No lawful MOTION evidence resolves the definition"],
        prohibited_interpretations=["cause", "intent", "forecast"],
        scope={"instrument":"GBPUSD","side":"BID","timeframe":"15M","clock":"UTC"},
        provenance_refs=["fixture:wp9:v1"],
        research_candidate_generation_ids=["rcg:fixture:1"],
        semantic_delta="Fixture-only distinct observable property",
    )


def test_candidate_is_distinct_from_research_candidate_and_not_admitted():
    c = _candidate()
    assert c["semantic_admission_state"] == "NOT_ADMITTED"
    b = build_language_candidate_binding(research_candidate_generation_id="rcg:fixture:1", structural_term_candidate_id=c["structural_term_candidate_id"], source_mode="PATH_1", vocabulary_exposure="BLINDED")
    assert b["identity_merge"] == "FORBIDDEN"
    with pytest.raises(TermQualificationError, match="MUST_DIFFER"):
        build_language_candidate_binding(research_candidate_generation_id="same", structural_term_candidate_id="same", source_mode="PATH_2")


def test_candidate_rejects_outcome_mechanism_identity_fields():
    with pytest.raises(TermQualificationError, match="TERM_FORBIDDEN_IDENTITY_FIELD"):
        build_structural_term_candidate(machine_symbol="X", term_class="OBSERVABLE_PROPERTY", formal_definition={"mechanism":"dealer intent"}, observation_unit="x", temporal_semantics={}, inclusion_predicates=["a"], exclusion_predicates=["b"], boundary_cases=["c"], ambiguity_policy="PRESERVE", missingness_policy="ABSTAIN", observable_implications=[], falsifiers=["f"], prohibited_interpretations=["cause"], scope={"instrument":"GBPUSD"}, provenance_refs=["p"])


def test_rule_pack_must_be_frozen_before_evidence():
    with pytest.raises(TermQualificationError, match="FROZEN_BEFORE_EVIDENCE"):
        build_term_qualification_rule_pack(rule_pack_id="q1", term_class="OBSERVABLE_PROPERTY", required_stages=["DEFINED"], required_evidence_dimensions=["observability"], rule_refs=["r1"], frozen_before_evidence=False)


def test_semantically_qualified_requires_external_adjudication():
    c = _candidate()
    p = build_term_qualification_rule_pack(rule_pack_id="q1", term_class="OBSERVABLE_PROPERTY", required_stages=["DEFINED","SEMANTICALLY_QUALIFIED"], required_evidence_dimensions=["observability"], rule_refs=["r1"], frozen_before_evidence=True)
    with pytest.raises(TermQualificationError, match="EXTERNAL_ADJUDICATION"):
        build_term_qualification_record(candidate=c, rule_pack=p, stage_statuses={"DEFINED":"PASS","SEMANTICALLY_QUALIFIED":"PASS"}, evidence_refs_by_dimension={"observability":["fixture:e1"]}, disposition="PROGRESS")


def test_active_admission_has_no_wp9_path():
    c = _candidate()
    with pytest.raises(TermQualificationError, match="OPERATOR_RESERVED"):
        build_semantic_admission_proposal(term_generation_id=c["term_generation_id"], qualification_record_id="tqr:1", requested_state="ADMITTED_ACTIVE", empirical_scope=c["scope"], evidence_packet_refs=["e1"])
    shadow = build_semantic_admission_proposal(term_generation_id=c["term_generation_id"], qualification_record_id="tqr:1", requested_state="ADMITTED_SHADOW", empirical_scope=c["scope"], evidence_packet_refs=["e1"], expiry="2026-09-01T00:00:00Z")
    assert shadow["proposal_only"] is True
    assert shadow["registry_mutation"] == "FORBIDDEN"


def test_challenge_is_proposal_only_and_transport_has_zero_target_authority():
    c = _candidate()
    challenge = build_term_challenge(term_generation_id=c["term_generation_id"], target="OBSERVABILITY", evidence_refs=["counterexample:1"], recommendation="QUARANTINE", opened_at="2026-08-14T09:00:00Z")
    assert challenge["authority_action"] == "PROPOSAL_ONLY"
    transport = build_transport_candidate(term_generation_id=c["term_generation_id"], source_scope=c["scope"], target_scope={**c["scope"], "timeframe":"2H"})
    assert transport["status"] == "TRANSPORT_EVALUATION_CANDIDATE"
    assert transport["target_scope_semantic_authority"] == "NONE"
