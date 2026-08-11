import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag2-r2"
DECISION = BASE / "C2E_AG2_OPERATOR_PASS_DECISION.json"
GATE = BASE / "C2E_AG2_GATE_PACKET_REFRESHED.json"
CORRECTION = BASE / "C2E_AG2_TECHNICAL_CONFORMANCE_CORRECTION.json"
RECEIPT = BASE / "C2E_AG2_MERGE_RECEIPT.json"
PREMERGE_STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_41_AG2_APPROVED.json"
POSTMERGE_STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_42_AG2_COMPLETED.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"

DECISION_ID = "C2E-AG2.OPERATOR.PASS.20260811T191400+0100"
PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
PACK_HASH = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
MERGE_SHA = "a61b0e23b2c3d981af1b228eb9f5f56546dbf349"


def load(path):
    return json.loads(path.read_text())


class C2EAG2OperatorPassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = load(DECISION)
        cls.gate = load(GATE)
        cls.correction = load(CORRECTION)
        cls.receipt = load(RECEIPT)
        cls.premerge_state = load(PREMERGE_STATE)
        cls.postmerge_state = load(POSTMERGE_STATE)
        cls.pointer = load(POINTER)

    def test_operator_pass_is_exact_and_gate_subject_is_preserved(self):
        self.assertEqual(self.decision["decision_id"], DECISION_ID)
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE C2E-AG2 PASS")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR_EXPLICIT")
        subject = self.decision["review_subject"]
        self.assertEqual(subject["boundary_pack_id"], PACK_ID)
        self.assertEqual(subject["logical_sha256"], PACK_HASH)
        self.assertEqual(subject["target_frame_count"], 4072)
        self.assertFalse(subject["active"])
        self.assertFalse(subject["canonical"])
        self.assertEqual(self.gate["gate_id"], "C2E-AG2")
        self.assertEqual(self.gate["decision_status"], "PENDING_OPERATOR")

    def test_pass_accepts_evidence_only_and_never_activates_at_ag2(self):
        delta = self.decision["authority_delta"]
        self.assertEqual(delta["ag2_comparative_review"], "PASS_FOR_EXACT_AG0_AG1_ADMITTED_PACK_AND_SCOPE_ONLY")
        self.assertEqual(delta["ag3_progression"], "AUTHORIZED_FOR_OPERATOR_RESERVED_PROPOSAL_PREPARATION_ONLY")
        self.assertEqual(delta["active_c2e"], "NONE")
        self.assertEqual(delta["active_boundary_pack"], "NONE")
        self.assertEqual(delta["selector_mutation"], "NONE")
        self.assertEqual(delta["canonical_or_r2_publication"], "NONE")
        self.assertEqual(delta["validation_consumption"], "NONE")
        self.assertEqual(delta["family_semantic_candidate_theory_promotion"], "NONE")
        self.assertEqual(delta["probability_risk_exposure_execution_agent_write"], "NONE")

    def test_comparator_evidence_is_the_exact_accepted_denominator(self):
        evidence = self.decision["comparator_evidence"]
        self.assertEqual(evidence["common_frame_count"], 4072)
        self.assertEqual(evidence["stream_start_count"], 92)
        self.assertEqual(evidence["transition_denominator"], 3980)
        self.assertEqual(evidence["both_boundary"], 3329)
        self.assertEqual(evidence["c2e_only"], 509)
        self.assertEqual(evidence["srfd_only"], 0)
        self.assertEqual(evidence["neither_boundary"], 142)
        self.assertEqual(evidence["disagreement_count"], 509)
        self.assertEqual(evidence["counterexample_count"], 12)

    def test_technical_correction_is_non_scientific_and_predecision_ci_passed(self):
        self.assertEqual(self.correction["authority_effect"], "NONE_TEST_HARNESS_CONFORMANCE_ONLY")
        invariants = self.correction["scientific_and_authority_invariants"]
        self.assertFalse(invariants["comparator_result_changed"])
        self.assertFalse(invariants["srfd_science_changed"])
        self.assertFalse(invariants["c2e_boundary_pack_changed"])
        self.assertEqual(invariants["active_c2e"], "NONE")
        self.assertEqual(invariants["active_boundary_pack"], "NONE")
        self.assertEqual(invariants["ag3"], "NOT_EXECUTED")
        bindings = self.decision["evidence_bindings"]
        self.assertEqual(bindings["predecision_tests_run_id"], 31522204774)
        self.assertEqual(bindings["predecision_tests_conclusion"], "SUCCESS")
        self.assertEqual(bindings["predecision_ovc_assurance_run_id"], 31522204812)
        self.assertEqual(bindings["predecision_ovc_assurance_conclusion"], "SUCCESS")

    def test_postmerge_closeout_preserves_ag2_and_pointer_may_advance_only_by_later_ag3(self):
        self.assertEqual(self.premerge_state["status"], "APPROVED")
        self.assertEqual(self.premerge_state["operator_decision_id"], DECISION_ID)
        self.assertIsNone(self.premerge_state["merge_commit"])

        self.assertEqual(self.receipt["merge_commit"], MERGE_SHA)
        self.assertEqual(self.receipt["operator_decision_id"], DECISION_ID)
        self.assertEqual(self.receipt["final_assurance"]["complete_repository_suite"]["conclusion"], "SUCCESS")
        self.assertEqual(self.receipt["final_assurance"]["ovc_final_head_and_tiered"]["conclusion"], "SUCCESS")
        self.assertEqual(self.receipt["active_c2e"], "NONE")
        self.assertEqual(self.receipt["active_boundary_pack"], "NONE")
        self.assertEqual(self.receipt["ag3"], "NOT_EXECUTED")

        self.assertEqual(self.postmerge_state["status"], "COMPLETED")
        self.assertEqual(self.postmerge_state["merge_commit"], MERGE_SHA)
        self.assertEqual(self.postmerge_state["operator_decision_id"], DECISION_ID)
        self.assertEqual(self.postmerge_state["active_c2e"], "NONE")
        self.assertEqual(self.postmerge_state["active_boundary_pack"], "NONE")
        self.assertEqual(self.postmerge_state["ag3"], "NOT_EXECUTED")
        self.assertEqual(self.postmerge_state["next_gate"], "C2E-AG3")
        self.assertIn("PROPOSAL", self.postmerge_state["ag3_progression"])

        authoritative_state = self.pointer["authoritative_state"]
        self.assertIn(
            authoritative_state,
            {
                "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_42_AG2_COMPLETED.json",
                "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_43_AG3_GATE_READY.json",
                "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_44_AG3_COMPLETED.json",
            },
        )
        self.assertEqual(self.pointer["ag2_progression"], "COMPLETED_PASS")
        self.assertIn(DECISION_ID, self.pointer["operator_decision_history"])
        if authoritative_state.endswith("OVC_C2E2_STATE_v0_42_AG2_COMPLETED.json"):
            self.assertEqual(self.pointer["next_gate"], "C2E-AG3")
            self.assertEqual(self.pointer["active_c2e"], "NONE")
            self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
            self.assertEqual(self.pointer["ag3"], "NOT_EXECUTED")
            self.assertEqual(self.pointer["status"], "COMPLETED")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG2")
            self.assertEqual(self.pointer["current_packet"], "C2E-AG2-CLOSEOUT")
            self.assertTrue(self.pointer["next_gate_operator_decision_required"])
        elif authoritative_state.endswith("OVC_C2E2_STATE_v0_43_AG3_GATE_READY.json"):
            self.assertEqual(self.pointer["next_gate"], "C2E-AG3")
            self.assertEqual(self.pointer["active_c2e"], "NONE")
            self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
            self.assertEqual(self.pointer["ag3"], "NOT_EXECUTED")
            self.assertEqual(self.pointer["status"], "GATE_READY")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG3")
            self.assertEqual(self.pointer["current_packet"], "C2E-AG3-PREP")
            self.assertTrue(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["recommended_operator_decision"], "ACTIVATE_NAMED_PACK")
            self.assertEqual(self.pointer["next_action"], "STOP_FOR_OPERATOR_C2E_AG3")
        else:
            self.assertIsNone(self.pointer["next_gate"])
            self.assertEqual(self.pointer["status"], "COMPLETED")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG3")
            self.assertEqual(self.pointer["current_packet"], "C2E-AG3-DECISION")
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["operator_decision"], "ACTIVATE_NAMED_PACK")
            self.assertEqual(self.pointer["ag3"], "EXECUTED_PASS_ACTIVATE_NAMED_PACK")
            self.assertEqual(self.pointer["active_c2e"], "ACTIVE_EXACT_NAMED_PACK_SCOPE_BOUND")
            self.assertEqual(self.pointer["active_boundary_pack"], PACK_ID)


if __name__ == "__main__":
    unittest.main()
