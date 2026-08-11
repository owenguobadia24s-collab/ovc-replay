import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag2-r2"
GATE = BASE / "C2E_AG2_GATE_PACKET_REFRESHED.json"
QA = BASE / "C2E_AG2_GAP_001_QA_PACKET.json"
EVIDENCE = BASE / "C2E_AG2_GAP_001_COMPARATOR_EVIDENCE.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_40_AG2_GATE_READY.json"


def load(path):
    return json.loads(path.read_text())


def test_ag2_gap001_is_resolved_with_exact_declared_comparators():
    gate = load(GATE)
    conditions = gate["acceptance_conditions"]
    assert gate["gate_id"] == "C2E-AG2"
    assert gate["gate_classification"] == "OPERATOR_RESERVED"
    assert gate["decision_status"] == "PENDING_OPERATOR"
    assert gate["recommended_decision"] == "PASS"
    assert gate["resolved_gap"]["id"] == "C2E-AG2-GAP-001"
    assert gate["resolved_gap"]["current_state"] == "RESOLVED"
    assert conditions["declared_causal_comparator_identities"].startswith("PASS_")
    assert conditions["declared_retrospective_control_identity"].startswith("PASS_")
    assert conditions["srfd_boundary_disagreement_ledger"] == "PASS_3980_TRANSITIONS_509_DISAGREEMENTS"
    assert gate["unresolved_issues"] == []


def test_comparison_denominator_and_disagreement_counts_reconcile():
    evidence = load(EVIDENCE)
    comparison = evidence["boundary_comparison"]
    counts = comparison["counts"]
    assert comparison["denominator"] == 3980
    assert sum(counts.values()) == 3980
    assert counts == {"BOTH_BOUNDARY": 3329, "C2E_ONLY": 509, "NEITHER_BOUNDARY": 142, "SRFD_ONLY": 0}
    assert comparison["disagreement_count"] == 509
    common = evidence["common_population"]
    assert common["c2e_frame_count"] == 4072
    assert common["srfd_target_eligible_local_15m_count"] == 4072
    assert common["exact_key_set_equality"] is True
    assert common["stream_start_count_c2e"] == 92
    assert common["stream_start_count_srfd"] == 92
    assert common["stream_start_set_equality"] is True


def test_counterexamples_and_negative_evidence_are_preserved():
    evidence = load(EVIDENCE)
    assert evidence["counterexamples"]["count"] == 12
    negative = evidence["negative_and_ambiguity_evidence"]
    assert negative["c2e_not_evaluable_candidates"] == 34
    assert negative["c2e_resolver_conflicts"] == 0
    assert negative["c2e_ambiguous_boundary_sets"] == 0
    legacy = evidence["comparator_identities"]["historical_legacy_comparator"]
    assert legacy["disagreement_count"] == 3524
    assert legacy["denominator"] == 4072


def test_no_hidden_winner_and_no_activation_authority():
    gate = load(GATE)
    evidence = load(EVIDENCE)
    hidden = evidence["no_hidden_winner"]
    assert hidden["family_fields_consumed"] is False
    assert hidden["outcome_fields_consumed"] is False
    assert hidden["threshold_tuning_performed"] is False
    assert hidden["family_or_method_selection_performed"] is False
    assert hidden["selector_mutation"] is False
    assert hidden["validation_consumed"] is False
    assert hidden["promotion_effect"] == "NONE"
    current = gate["current_authority"]
    assert current["active_c2e"] == "NONE"
    assert current["active_boundary_pack"] == "NONE"
    assert evidence["ag3"] == "NOT_EXECUTED"


def test_qa_and_programme_state_stop_at_operator_reserved_ag2():
    qa = load(QA)
    state = load(STATE)
    assert qa["qa_disposition"] == "PASS_TO_PRESENT_OPERATOR_AG2"
    assert qa["recommended_gate_decision"] == "PASS"
    assert qa["authority_effect"] == "NONE_COMPARATOR_EVIDENCE_ONLY"
    assert state["status"] == "GATE_READY"
    assert state["operator_decision_required"] is True
    assert state["recommended_operator_decision"] == "PASS"
    assert state["active_c2e"] == "NONE"
    assert state["active_boundary_pack"] == "NONE"
    assert state["ag3"] == "NOT_EXECUTED"
    assert state["next_action"] == "STOP_AT_OPERATOR_RESERVED_C2E_AG2"
