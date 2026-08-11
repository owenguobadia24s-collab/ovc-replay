import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag2-r2"
DECISION = BASE / "C2E_AG2_OPERATOR_PASS_DECISION.json"
GATE = BASE / "C2E_AG2_GATE_PACKET_REFRESHED.json"
CORRECTION = BASE / "C2E_AG2_TECHNICAL_CONFORMANCE_CORRECTION.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_41_AG2_APPROVED.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"

DECISION_ID = "C2E-AG2.OPERATOR.PASS.20260811T191400+0100"
PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
PACK_HASH = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"


def load(path):
    return json.loads(path.read_text())


class C2EAG2OperatorPassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = load(DECISION)
        cls.gate = load(GATE)
        cls.correction = load(CORRECTION)
        cls.state = load(STATE)
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

    def test_pass_accepts_evidence_only_and_never_activates(self):
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

    def test_approved_state_is_premerge_and_moving_pointer_stays_last_merged_state(self):
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertEqual(self.state["operator_decision_id"], DECISION_ID)
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.state["active_c2e"], "NONE")
        self.assertEqual(self.state["active_boundary_pack"], "NONE")
        self.assertEqual(self.state["ag3"], "NOT_EXECUTED")
        self.assertEqual(self.state["next_gate"], "C2E-AG3")
        self.assertIn("PROPOSAL", self.state["ag3_progression"])
        self.assertIsNone(self.state["merge_commit"])

        # Until the operator-approved AG2 packet is actually merged, the moving pointer
        # remains the last merged effective state. This preserves all historical
        # pointer-dependent conformance and prevents unmerged branch state from acting
        # as repository authority.
        self.assertEqual(
            self.pointer["authoritative_state"],
            "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_38.json",
        )
        self.assertEqual(self.pointer["current_gate"], "C2E-AG1")
        self.assertEqual(self.pointer["current_packet"], "C2E-AG1-DECISION")
        self.assertEqual(self.pointer["ag2_progression"], "AUTHORIZED_FOR_GATE_PREPARATION_ONLY")
        self.assertEqual(self.pointer["next_gate"], "C2E-AG2")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertNotIn(DECISION_ID, self.pointer["operator_decision_history"])


if __name__ == "__main__":
    unittest.main()
