import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag2-r2"
GATE = BASE / "C2E_AG2_GATE_PACKET_REFRESHED.json"
QA = BASE / "C2E_AG2_GAP_001_QA_PACKET.json"
EVIDENCE = BASE / "C2E_AG2_GAP_001_COMPARATOR_EVIDENCE.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_40_AG2_GATE_READY.json"


def load(path):
    return json.loads(path.read_text())


class C2EAG2Gap001GateReadyTests(unittest.TestCase):
    def test_ag2_gap001_is_resolved_with_exact_declared_comparators(self):
        gate = load(GATE)
        conditions = gate["acceptance_conditions"]
        self.assertEqual(gate["gate_id"], "C2E-AG2")
        self.assertEqual(gate["gate_classification"], "OPERATOR_RESERVED")
        self.assertEqual(gate["decision_status"], "PENDING_OPERATOR")
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertEqual(gate["resolved_gap"]["id"], "C2E-AG2-GAP-001")
        self.assertEqual(gate["resolved_gap"]["current_state"], "RESOLVED")
        self.assertTrue(conditions["declared_causal_comparator_identities"].startswith("PASS_"))
        self.assertTrue(conditions["declared_retrospective_control_identity"].startswith("PASS_"))
        self.assertEqual(
            conditions["srfd_boundary_disagreement_ledger"],
            "PASS_3980_TRANSITIONS_509_DISAGREEMENTS",
        )
        self.assertEqual(gate["unresolved_issues"], [])

    def test_comparison_denominator_and_disagreement_counts_reconcile(self):
        evidence = load(EVIDENCE)
        comparison = evidence["boundary_comparison"]
        counts = comparison["counts"]
        self.assertEqual(comparison["denominator"], 3980)
        self.assertEqual(sum(counts.values()), 3980)
        self.assertEqual(
            counts,
            {"BOTH_BOUNDARY": 3329, "C2E_ONLY": 509, "NEITHER_BOUNDARY": 142, "SRFD_ONLY": 0},
        )
        self.assertEqual(comparison["disagreement_count"], 509)
        common = evidence["common_population"]
        self.assertEqual(common["c2e_frame_count"], 4072)
        self.assertEqual(common["srfd_target_eligible_local_15m_count"], 4072)
        self.assertTrue(common["exact_key_set_equality"])
        self.assertEqual(common["stream_start_count_c2e"], 92)
        self.assertEqual(common["stream_start_count_srfd"], 92)
        self.assertTrue(common["stream_start_set_equality"])

    def test_counterexamples_and_negative_evidence_are_preserved(self):
        evidence = load(EVIDENCE)
        self.assertEqual(evidence["counterexamples"]["count"], 12)
        negative = evidence["negative_and_ambiguity_evidence"]
        self.assertEqual(negative["c2e_not_evaluable_candidates"], 34)
        self.assertEqual(negative["c2e_resolver_conflicts"], 0)
        self.assertEqual(negative["c2e_ambiguous_boundary_sets"], 0)
        legacy = evidence["comparator_identities"]["historical_legacy_comparator"]
        self.assertEqual(legacy["disagreement_count"], 3524)
        self.assertEqual(legacy["denominator"], 4072)

    def test_no_hidden_winner_and_no_activation_authority(self):
        gate = load(GATE)
        evidence = load(EVIDENCE)
        hidden = evidence["no_hidden_winner"]
        self.assertFalse(hidden["family_fields_consumed"])
        self.assertFalse(hidden["outcome_fields_consumed"])
        self.assertFalse(hidden["threshold_tuning_performed"])
        self.assertFalse(hidden["family_or_method_selection_performed"])
        self.assertFalse(hidden["selector_mutation"])
        self.assertFalse(hidden["validation_consumed"])
        self.assertEqual(hidden["promotion_effect"], "NONE")
        current = gate["current_authority"]
        self.assertEqual(current["active_c2e"], "NONE")
        self.assertEqual(current["active_boundary_pack"], "NONE")
        self.assertEqual(evidence["ag3"], "NOT_EXECUTED")

    def test_qa_and_programme_state_stop_at_operator_reserved_ag2(self):
        qa = load(QA)
        state = load(STATE)
        self.assertEqual(qa["qa_disposition"], "PASS_TO_PRESENT_OPERATOR_AG2")
        self.assertEqual(qa["recommended_gate_decision"], "PASS")
        self.assertEqual(qa["authority_effect"], "NONE_COMPARATOR_EVIDENCE_ONLY")
        self.assertEqual(state["status"], "GATE_READY")
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual(state["recommended_operator_decision"], "PASS")
        self.assertEqual(state["active_c2e"], "NONE")
        self.assertEqual(state["active_boundary_pack"], "NONE")
        self.assertEqual(state["ag3"], "NOT_EXECUTED")
        self.assertEqual(state["next_action"], "STOP_AT_OPERATOR_RESERVED_C2E_AG2")


if __name__ == "__main__":
    unittest.main()
