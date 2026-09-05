from __future__ import annotations

from pathlib import Path

from ovc.research_operations.lsiac.pass2_gen0002 import (
    AUTHORITY_EFFECT,
    EXPECTED_PASS1_VIRTUAL_VIEW_ID,
    OPERATOR_AUTHORITY_DECISION_ID,
    adjudicate_subject,
    build_pass2_adjudication_view,
    build_virtual_view_identity,
)

ROOT = Path(__file__).resolve().parents[3]


def test_gen0002_pass2_accounts_for_exact_effective_frontier():
    view = build_pass2_adjudication_view(ROOT)
    assert view["subject_count"] == 431
    assert view["passport_count"] == 434
    assert len(view["decisions"]) == 431
    assert len(view["counterevidence_manifests"]) == 431
    subjects = [decision["source_subject_ids"][0] for decision in view["decisions"]]
    assert len(subjects) == len(set(subjects)) == 431
    assert view["operator_authority_decision_id"] == OPERATOR_AUTHORITY_DECISION_ID
    assert view["pass1_virtual_view_id"] == EXPECTED_PASS1_VIRTUAL_VIEW_ID


def test_gen0002_pass2_fails_closed_without_role_specific_admissibility_evidence():
    view = build_pass2_adjudication_view(ROOT)
    assert view["non_none_role_count"] == 0
    assert view["retain_forward_count"] == 0
    assert view["high_impact_review_trigger_count"] == 0
    assert view["destination_binding_count"] == 0
    assert view["architecture_execution_count"] == 0
    for decision in view["decisions"]:
        assert decision["inheritance_roles"] == ["NONE"]
        assert decision["lifecycle_state"] in {"DEFERRED_UNRESOLVED", "QUARANTINED"}
        assert decision["architecture_effect_set"]["primary_effect"] == "NO_FORWARD_IMPLEMENTATION"
        assert decision["destination_binding_set"] == {
            "controlling_destination": None,
            "consumer_destinations": [],
        }
        assert decision["review_declarations"] == []
        assert decision["authority_effect"] == AUTHORITY_EFFECT


def test_pending_source_bindings_are_not_evaluable_and_quarantined():
    view = build_pass2_adjudication_view(ROOT)
    pending = [
        decision
        for decision in view["decisions"]
        if decision["source_standing"] == "PENDING_SOURCE_BINDING"
    ]
    assert len(pending) == 2
    for decision in pending:
        assert decision["claim_strength"] == "NOT_EVALUABLE"
        assert decision["inheritance_roles"] == ["NONE"]
        assert decision["lifecycle_state"] == "QUARANTINED"
        assert decision["docket_status"] == "SOURCE_BINDING_REQUIRED"


def test_source_binding_debt_does_not_become_forward_scientific_role():
    view = build_pass2_adjudication_view(ROOT)
    by_subject = {decision["source_subject_ids"][0]: decision for decision in view["decisions"]}
    for subject in (
        "OVC-REPRESENTATION-ROBUSTNESS-0001-SOURCE-BINDING",
        "OVC-RRSCG-OBSERVER-STATE-GEOMETRY-0001-SOURCE-BINDING",
    ):
        decision = by_subject[subject]
        assert decision["claim_strength"] == "NOT_EVALUABLE"
        assert decision["inheritance_roles"] == ["NONE"]


def test_post_v05_negative_results_are_preserved_without_promotion():
    view = build_pass2_adjudication_view(ROOT)
    by_subject = {decision["source_subject_ids"][0]: decision for decision in view["decisions"]}
    for subject in (
        "OVC-MULTICLOCK-NONLINEAR-DYNAMICS-0005",
        "OVC-MULTICLOCK-PERSISTENCE-DWELL-0006",
        "OVC-MULTICLOCK-SUCCESSOR-SEQUENCE-0005-0006-FINAL-SYNTHESIS",
    ):
        decision = by_subject[subject]
        assert decision["scientific_disposition"] == "NEGATIVE_SUPPORTED"
        assert decision["inheritance_roles"] == ["NONE"]
        assert decision["claim_strength"] == "HISTORICAL_CONTEXT_ONLY"
        assert decision["lifecycle_state"] == "DEFERRED_UNRESOLVED"


def test_counterevidence_manifests_are_complete_but_not_false_evidence_mass():
    view = build_pass2_adjudication_view(ROOT)
    assert len({m["manifest_sha256"] for m in view["counterevidence_manifests"]}) == 431
    for manifest in view["counterevidence_manifests"]:
        assert manifest["complete"] is True
        assert manifest["supporting_load_bearing_subjects"] == []
        assert manifest["protocol_exceptions"] == []
        assert "GEN0002_PASS1_DOES_NOT_SUPPLY_ROLE_SPECIFIC_ADMISSIBILITY_EVIDENCE" in manifest["warnings"]


def test_subject_adjudication_is_deterministic():
    classification = {
        "subject_id": "SYNTHETIC-FAIL-CLOSED",
        "source_standing": "SOURCE_EXACT",
        "scientific_disposition": "UNRESOLVED",
        "exposure_state": "UNKNOWN",
        "source_relation_state": "CONSISTENT",
        "dependence_refs": [],
        "source_blockers": [],
    }
    first = adjudicate_subject(classification)
    second = adjudicate_subject(classification)
    assert first == second


def test_virtual_identity_is_algorithm_bound_and_deterministic():
    a = build_virtual_view_identity(algorithm_git_blob_sha="a" * 40)
    b = build_virtual_view_identity(algorithm_git_blob_sha="a" * 40)
    c = build_virtual_view_identity(algorithm_git_blob_sha="b" * 40)
    assert a == b
    assert a != c
    assert len(a) == 64
