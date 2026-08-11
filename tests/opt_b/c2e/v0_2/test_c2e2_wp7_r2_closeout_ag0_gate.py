import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
WP7_R2 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp7-r2"
AG0_R2 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0-r2"
RECEIPT = WP7_R2 / "C2E2_WP7_R2_TERMINAL_MERGE_RECEIPT.json"
CLOSEOUT_QA = WP7_R2 / "C2E2_WP7_R2_CLOSEOUT_QA_PACKET.json"
READINESS = WP7_R2 / "C2E2_WP7_R2_ACTIVATION_READINESS_PACKET.json"
GATE = AG0_R2 / "C2E_AG0_R2_GATE_PACKET.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_31.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
HISTORICAL_GATE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0/C2E_AG0_GATE_PACKET.json"
HISTORICAL_DECISION = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0/C2E_AG0_OPERATOR_DECISION.json"

class C2E2WP7R2CloseoutAG0GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.closeout_qa = json.loads(CLOSEOUT_QA.read_text())
        cls.readiness = json.loads(READINESS.read_text())
        cls.gate = json.loads(GATE.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.historical_gate = json.loads(HISTORICAL_GATE.read_text())
        cls.historical_decision = json.loads(HISTORICAL_DECISION.read_text())

    def test_wp7_r2_terminal_receipt_binds_exact_merge_and_assurance(self):
        self.assertEqual(self.receipt["packet_id"], "C2E2-WP7")
        self.assertEqual(self.receipt["packet_revision"], "R2_EXECUTED_REPLAY_READINESS")
        self.assertEqual(self.receipt["gate_id"], "C2E2-G7")
        self.assertEqual(self.receipt["decision"], "PASS")
        self.assertEqual(self.receipt["pr_number"], 530)
        self.assertEqual(self.receipt["pr_head"], "6bdf48e5487a679554fd98f1045ef50f6890bfca")
        self.assertEqual(self.receipt["pr_base_main"], "4adec4ab6d5f6a41e153be06d48f1cd2537fa927")
        self.assertEqual(self.receipt["merge_method"], "SQUASH")
        self.assertEqual(self.receipt["merge_commit"], "bbcfa532be25e615d4cd43eb82c5ad3fe7b51217")
        conclusions = [v["conclusion"] for k, v in self.receipt["final_assurance"].items() if isinstance(v, dict)]
        self.assertTrue(conclusions)
        self.assertTrue(all(value == "SUCCESS" for value in conclusions))
        self.assertEqual(self.receipt["final_assurance"]["unresolved_review_threads"], 0)
        self.assertEqual(self.receipt["authority_delta"], "NONE")

    def test_closeout_qa_is_zero_delta_pass_and_does_not_execute_operator_gate(self):
        self.assertEqual(self.closeout_qa["status"], "PASS")
        self.assertEqual(self.closeout_qa["recommendation"], "PASS")
        self.assertEqual(self.closeout_qa["authority_delta"], "NONE")
        self.assertEqual(self.closeout_qa["operator_gate_ready"], "C2E-AG0")
        self.assertEqual(self.closeout_qa["operator_gate_recommendation"], "PASS")
        self.assertFalse(self.closeout_qa["operator_gate_decision_executed"])
        self.assertEqual(self.closeout_qa["blocking_warnings"], [])

    def test_ag0_r2_gate_is_complete_exact_and_operator_reserved(self):
        self.assertEqual(self.gate["gate_id"], "C2E-AG0")
        self.assertEqual(self.gate["gate_classification"], "OPERATOR_RESERVED")
        self.assertEqual(self.gate["decision_status"], "PENDING_OPERATOR")
        self.assertIsNone(self.gate["operator_decision_record"])
        self.assertEqual(self.gate["allowed_decisions"], ["PASS", "DEFER", "BLOCK"])
        self.assertEqual(self.gate["candidate_commit"], self.receipt["merge_commit"])
        self.assertEqual(self.gate["recommended_decision"], "PASS")
        self.assertEqual(self.gate["next_action"], "STOP_AT_OPERATOR_GATE_C2E_AG0")

    def test_ag0_review_subject_matches_wp7_r2_empirical_candidate(self):
        subject = self.gate["review_subject"]
        ready_subject = self.readiness["candidate_boundary_pack"]
        self.assertEqual(subject["boundary_pack_id"], ready_subject["boundary_pack_id"])
        self.assertEqual(subject["logical_sha256"], ready_subject["logical_sha256"])
        self.assertEqual(subject["source_blob_sha"], ready_subject["source_blob_sha"])
        self.assertEqual(subject["version"], ready_subject["version"])
        self.assertEqual(subject["authority"], "CANDIDATE")
        self.assertFalse(subject["active"])
        self.assertFalse(subject["canonical"])
        self.assertEqual(subject["population_scope"]["target_frame_count"], 4072)

    def test_ag0_acceptance_is_pass_without_granting_activation(self):
        conditions = self.gate["acceptance_conditions"]
        self.assertTrue(all(value.startswith("PASS") for value in conditions.values()))
        delta = self.gate["proposed_delta_if_pass"]
        self.assertEqual(delta["candidate_admissibility"], "ADMIT_EXACT_NAMED_PACK_FOR_OPERATOR_GOVERNED_AG_EVALUATION_ONLY")
        self.assertEqual(delta["active_c2e"], "NONE")
        self.assertEqual(delta["active_boundary_pack"], "NONE")
        self.assertEqual(delta["selector_mutation"], "NONE")
        self.assertEqual(delta["ag1_progression"], "PREPARE_NEXT_OPERATOR_RESERVED_REPLAY_ADEQUACY_GATE_ONLY")

    def test_warnings_remain_visible_and_are_not_reclassified_as_ag0_blockers(self):
        self.assertEqual(len(self.gate["warnings"]), 3)
        self.assertIn("SRFD_CURRENT_COMPARATOR_UNAVAILABLE_DUE_EXISTING_SRFDI_WP10_V07_SEGMENTATION_BINDING_BLOCKER", self.gate["warnings"])
        self.assertIn("WP6_EQUIVALENCE_PROOF_IS_SEMANTIC_NOT_CANONICAL_RUNTIME_BYTE_STREAM_EQUIVALENCE", self.gate["warnings"])
        self.assertIn("REAL_SOURCE_RESTART_EQUIVALENCE_NOT_SEPARATELY_MATERIALIZED_IN_WP6_POSTRUN_PACKET", self.gate["warnings"])
        self.assertEqual(self.gate["unresolved_issues"], [])
        self.assertEqual(len(self.gate["external_artifact_hashes"]), 5)

    def test_historical_authoritative_state_stays_exact_while_pointer_advances_lawfully(self):
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["current_gate"], "C2E-AG0")
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(self.state["packet_record"]["status"], "COMPLETED")
        self.assertEqual(self.state["packet_record"]["merge_commit"], self.receipt["merge_commit"])
        self.assertEqual(self.state["authority"]["active_c2e"], "NONE")
        self.assertEqual(self.state["authority"]["active_boundary_pack"], "NONE")
        self.assertEqual(self.state["authority"]["c2e_activation"], "DENIED_OPERATOR_RESERVED")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        authoritative_state = self.pointer["authoritative_state"]
        if authoritative_state.endswith("OVC_C2E2_STATE_v0_31.json"):
            self.assertEqual(self.pointer["status"], "GATE_READY")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG0")
            self.assertTrue(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["next_action"], "STOP_FOR_OPERATOR_C2E_AG0_R2")
        elif authoritative_state.endswith("OVC_C2E2_STATE_v0_32.json"):
            self.assertEqual(self.pointer["status"], "READY")
            self.assertEqual(self.pointer["current_packet"], "C2E-AG1-PREP")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG1")
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertIn("C2E-AG0.OPERATOR.PASS.20260809T213300+0100", self.pointer["operator_decision_history"])
        elif authoritative_state.endswith("OVC_C2E2_STATE_v0_33.json"):
            self.assertEqual(self.pointer["status"], "GATE_READY")
            self.assertEqual(self.pointer["current_packet"], "C2E-AG1-PREP")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG1")
            self.assertTrue(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["recommended_operator_decision"], "DEFER")
            self.assertIn("C2E-AG0.OPERATOR.PASS.20260809T213300+0100", self.pointer["operator_decision_history"])
            self.assertEqual(self.pointer["ag2_progression"], "DENIED_PENDING_AG1")
        elif authoritative_state.endswith("OVC_C2E2_STATE_v0_38.json"):
            self.assertEqual(self.pointer["status"], "APPROVED")
            self.assertEqual(self.pointer["current_packet"], "C2E-AG1-DECISION")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG1")
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["operator_decision"], "PASS")
            self.assertEqual(self.pointer["ag1_replay_adequacy"], "PASS")
            self.assertEqual(self.pointer["ag2_progression"], "AUTHORIZED_FOR_GATE_PREPARATION_ONLY")
            self.assertEqual(self.pointer["next_gate"], "C2E-AG2")
        elif authoritative_state.endswith("OVC_C2E2_STATE_v0_42_AG2_COMPLETED.json"):
            self.assertEqual(self.pointer["status"], "COMPLETED")
            self.assertEqual(self.pointer["current_packet"], "C2E-AG2-CLOSEOUT")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG2")
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["operator_decision"], "PASS")
            self.assertEqual(self.pointer["ag1_replay_adequacy"], "PASS")
            self.assertEqual(self.pointer["ag2_progression"], "COMPLETED_PASS")
            self.assertEqual(self.pointer["next_gate"], "C2E-AG3")
            self.assertEqual(self.pointer["ag3"], "NOT_EXECUTED")
        else:
            self.assertEqual(authoritative_state, "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_43_AG3_GATE_READY.json")
            self.assertEqual(self.pointer["status"], "GATE_READY")
            self.assertEqual(self.pointer["current_packet"], "C2E-AG3-PREP")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG3")
            self.assertTrue(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["recommended_operator_decision"], "ACTIVATE_NAMED_PACK")
            self.assertEqual(self.pointer["ag1_replay_adequacy"], "PASS")
            self.assertEqual(self.pointer["ag2_progression"], "COMPLETED_PASS")
            self.assertEqual(self.pointer["next_gate"], "C2E-AG3")
            self.assertEqual(self.pointer["ag3"], "NOT_EXECUTED")

    def test_historical_synthetic_ag0_defer_remains_immutable_history(self):
        self.assertEqual(self.historical_gate["recommended_decision"], "DEFER")
        self.assertEqual(self.historical_gate["review_subject"]["classification"], "SYNTHETIC_SHADOW_ONLY_NONEMPIRICAL_REVIEW_SUBJECT")
        self.assertEqual(self.historical_decision["decision"], "DEFER")
        self.assertIn(self.historical_decision["decision_id"], self.state["operator_decision_history"])
        self.assertIn(self.historical_decision["decision_id"], self.pointer["operator_decision_history"])

    def test_no_reserved_authority_is_hidden_in_closeout(self):
        self.assertEqual(self.state["authority"]["selector_mutation"], "DENIED")
        self.assertEqual(self.state["authority"]["canonical_or_r2_publication"], "DENIED")
        self.assertEqual(self.state["authority"]["validation_consumption"], "DENIED")
        self.assertEqual(self.state["authority"]["family_semantic_candidate_theory_promotion"], "DENIED")
        self.assertEqual(self.state["authority"]["probability_risk_exposure_execution_agent_write"], "NONE")
        self.assertEqual(self.gate["current_authority"]["active_c2e"], "NONE")
        self.assertEqual(self.gate["current_authority"]["active_boundary_pack"], "NONE")

if __name__ == "__main__":
    unittest.main()
