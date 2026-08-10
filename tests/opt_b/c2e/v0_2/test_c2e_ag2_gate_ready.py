import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "registries/implementation/c2e_v0_2"
AG2 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag2"
GATE = AG2 / "C2E_AG2_GATE_PACKET.json"
QA = AG2 / "C2E_AG2_GATE_PREP_QA_PACKET.json"
STATE = BASE / "OVC_C2E2_STATE_v0_39.json"
POINTER = BASE / "CURRENT_STATE_POINTER.json"

PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
PACK_HASH = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"

class C2EAG2GateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = json.loads(GATE.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_exact_subject_and_gate_classification(self):
        self.assertEqual(self.gate["gate_id"], "C2E-AG2")
        self.assertEqual(self.gate["gate_classification"], "OPERATOR_RESERVED")
        self.assertEqual(self.gate["allowed_decisions"], ["PASS", "DEFER", "BLOCK"])
        self.assertEqual(self.gate["decision_status"], "PENDING_OPERATOR")
        self.assertEqual(self.gate["review_subject"]["boundary_pack_id"], PACK_ID)
        self.assertEqual(self.gate["review_subject"]["logical_sha256"], PACK_HASH)
        self.assertEqual(self.gate["review_subject"]["population_scope"]["target_frame_count"], 4072)
        self.assertFalse(self.gate["review_subject"]["active"])
        self.assertFalse(self.gate["review_subject"]["canonical"])

    def test_historical_comparator_counterexamples_and_conflict_pressure_are_present(self):
        a = self.gate["acceptance_conditions"]
        self.assertEqual(a["historical_comparator_identity_and_disagreement"], "PASS_4072_FRAMES_3524_DISAGREEMENTS")
        self.assertEqual(a["counterexamples"], "PASS_12_DETERMINISTIC_EXAMPLES")
        self.assertTrue(a["conflict_pressure"].startswith("PASS_"))
        self.assertTrue(a["ambiguity_residual_evidence"].startswith("PASS_"))
        self.assertTrue(a["no_hidden_winner"].startswith("PASS_"))
        self.assertEqual(self.gate["evidence"]["conflict_pressure"]["resolver_conflicts"], 0)
        self.assertEqual(self.gate["evidence"]["conflict_pressure"]["matched_candidate_boundaries"], 8490)
        self.assertEqual(self.gate["evidence"]["ambiguity_and_residual"]["not_evaluable_candidates"], 34)

    def test_srfd_comparator_gap_is_explicit_and_branch_only_evidence_is_rejected(self):
        a = self.gate["acceptance_conditions"]
        self.assertTrue(a["srfd_retrospective_comparator_identity_and_disagreement"].startswith("NOT_MET_"))
        self.assertEqual(len(self.gate["required_evidence_gaps"]), 1)
        gap = self.gate["required_evidence_gaps"][0]
        self.assertEqual(gap["id"], "C2E-AG2-GAP-001")
        self.assertTrue(gap["must_not_infer"])
        srfd = self.gate["evidence"]["srfd_retrospective_comparator"]
        self.assertEqual(srfd["status"], "NOT_MATERIALIZED_ON_CURRENT_LAWFUL_MAIN")
        self.assertEqual(srfd["open_unmerged_evidence"]["pr_number"], 551)
        self.assertIn("NOT_COURT_RECORD", srfd["open_unmerged_evidence"]["authority_status"])

    def test_gate_recommends_defer_and_umbrella_cannot_manufacture_missing_evidence(self):
        self.assertEqual(self.gate["recommended_decision"], "DEFER")
        self.assertEqual(self.gate["operator_umbrella_effect"], "NO_AUTOMATIC_PASS_WHILE_REQUIRED_EVIDENCE_CONDITION_IS_NOT_MET")
        self.assertEqual(self.qa["qa_disposition"], "PASS_FOR_OPERATOR_REVIEW")
        self.assertEqual(self.qa["operator_gate_recommendation"], "DEFER")
        self.assertEqual(self.qa["blockers_to_gate_preparation"], [])
        self.assertEqual(self.qa["blockers_to_recommended_ag2_pass"], ["C2E-AG2-GAP-001_SRFD_COMPARATOR_DISAGREEMENT"])

    def test_no_activation_or_downstream_authority_is_granted(self):
        delta = self.gate["proposed_delta_if_pass"]
        self.assertEqual(delta["active_c2e"], "NONE")
        self.assertEqual(delta["active_boundary_pack"], "NONE")
        self.assertEqual(delta["selector_mutation"], "NONE")
        self.assertEqual(delta["canonical_or_r2_publication"], "NONE")
        self.assertEqual(delta["validation_consumption"], "NONE")
        self.assertEqual(delta["ag3_progression"], "PREPARE_EXACT_OPERATOR_RESERVED_AG3_ACTIVATION_PROPOSAL_ONLY")
        self.assertEqual(self.gate["evidence"]["no_hidden_winner"]["outcome_or_family_tuning"], False)

    def test_programme_state_stops_at_ag2(self):
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["current_packet"], "C2E-AG2-PREP")
        self.assertEqual(self.state["current_gate"], "C2E-AG2")
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(self.state["recommended_operator_decision"], "DEFER")
        self.assertEqual(self.state["authority"]["active_c2e"], "NONE")
        self.assertEqual(self.state["authority"]["ag3_progression"], "DENIED_PENDING_AG2")
        self.assertEqual(self.pointer["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_39.json")
        self.assertEqual(self.pointer["status"], "GATE_READY")
        self.assertEqual(self.pointer["current_gate"], "C2E-AG2")
        self.assertTrue(self.pointer["operator_decision_required"])
        self.assertEqual(self.pointer["recommended_operator_decision"], "DEFER")
        self.assertEqual(self.pointer["next_action"], "STOP_FOR_OPERATOR_C2E_AG2")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")

if __name__ == "__main__":
    unittest.main()
