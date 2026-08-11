import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "registries/implementation/c2e_v0_2"
DECISION = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0-r2/C2E_AG0_R2_OPERATOR_DECISION.json"
QA = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0-r2/C2E_AG0_R2_DECISION_QA_PACKET.json"
HISTORICAL_DEFER = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0/C2E_AG0_OPERATOR_DECISION.json"
STATE = BASE / "OVC_C2E2_STATE_v0_32.json"
POINTER = BASE / "CURRENT_STATE_POINTER.json"

PASS_ID = "C2E-AG0.OPERATOR.PASS.20260809T213300+0100"
DEFER_ID = "C2E-AG0.OPERATOR.DEFER.20260808T205200+0100"
PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
PACK_HASH = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"

class C2EAG0R2OperatorPassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.historical_defer = json.loads(HISTORICAL_DEFER.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_pass_is_exact_and_named(self):
        self.assertEqual(self.decision["decision_id"], PASS_ID)
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE C2E-AG0 PASS")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        subject = self.decision["review_subject"]
        self.assertEqual(subject["boundary_pack_id"], PACK_ID)
        self.assertEqual(subject["logical_sha256"], PACK_HASH)
        self.assertEqual(subject["target_frame_count"], 4072)
        self.assertFalse(subject["active"])
        self.assertFalse(subject["canonical"])

    def test_historical_ag0_defer_is_preserved_append_only(self):
        self.assertEqual(self.historical_defer["decision_id"], DEFER_ID)
        history = self.pointer["operator_decision_history"]
        self.assertIn(DEFER_ID, history)
        self.assertIn(PASS_ID, history)
        self.assertLess(history.index(DEFER_ID), history.index(PASS_ID))

    def test_pass_admits_only_evaluation_and_never_activation(self):
        effects = self.decision["effects"]
        self.assertEqual(effects["candidate_admissibility"], "ADMITTED_EXACT_NAMED_PACK_FOR_OPERATOR_GOVERNED_AG_EVALUATION_ONLY")
        self.assertEqual(effects["active_c2e"], "NONE")
        self.assertEqual(effects["active_boundary_pack"], "NONE")
        self.assertEqual(effects["selector_mutation"], "NONE")
        self.assertEqual(effects["canonical_or_r2_publication"], "NONE")
        self.assertEqual(effects["validation_consumption"], "NONE")
        self.assertEqual(effects["ag2_progression"], "DENIED_PENDING_EXPLICIT_AG1_DECISION")
        self.assertEqual(effects["ag3_activation_or_replacement"], "DENIED_OPERATOR_RESERVED_OUTSIDE_AUTOMATIC_EXECUTION")

    def test_state_and_pointer_route_only_to_ag1_preparation_or_later_lawful_ag_progression(self):
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertEqual(self.state["authority"]["ag0_admissibility"], "PASS")
        self.assertEqual(self.state["authority"]["ag1_gate_preparation"], "AUTHORIZED")
        self.assertEqual(self.state["authority"]["ag2_progression"], "DENIED_PENDING_AG1")
        self.assertEqual(self.state["authority"]["active_c2e"], "NONE")
        self.assertIn(self.pointer["status"], {"READY", "GATE_READY", "APPROVED", "COMPLETED"})
        self.assertEqual(self.pointer["candidate_boundary_pack_id"], PACK_ID)
        self.assertEqual(self.pointer["candidate_boundary_pack_status"], "ADMITTED_FOR_AG_EVALUATION_ONLY_INACTIVE_NONCANONICAL")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertIn(PASS_ID, self.pointer["operator_decision_history"])
        if self.pointer["status"] in {"READY", "GATE_READY"}:
            self.assertEqual(self.pointer["current_packet"], "C2E-AG1-PREP")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG1")
            if self.pointer["status"] == "READY":
                self.assertFalse(self.pointer["operator_decision_required"])
            else:
                self.assertTrue(self.pointer["operator_decision_required"])
                self.assertEqual(self.pointer["recommended_operator_decision"], "DEFER")
                self.assertEqual(self.pointer["ag2_progression"], "DENIED_PENDING_AG1")
        elif self.pointer["status"] == "APPROVED":
            self.assertEqual(self.pointer["current_packet"], "C2E-AG1-DECISION")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG1")
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["operator_decision"], "PASS")
            self.assertEqual(self.pointer["ag1_replay_adequacy"], "PASS")
            self.assertEqual(self.pointer["ag2_progression"], "AUTHORIZED_FOR_GATE_PREPARATION_ONLY")
            self.assertEqual(self.pointer["next_gate"], "C2E-AG2")
        else:
            self.assertEqual(self.pointer["current_packet"], "C2E-AG2-CLOSEOUT")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG2")
            self.assertEqual(self.pointer["ag1_replay_adequacy"], "PASS")
            self.assertEqual(self.pointer["ag2_progression"], "COMPLETED_PASS")
            self.assertEqual(self.pointer["next_gate"], "C2E-AG3")
            self.assertEqual(self.pointer["ag3"], "NOT_EXECUTED")

    def test_qa_passes_without_hiding_replay_warnings(self):
        self.assertEqual(self.qa["qa_disposition"], "PASS")
        self.assertEqual(self.qa["authority_effect"], "AG0_ADMISSIBILITY_ONLY_NO_RUNTIME_ACTIVATION")
        expected = {
            "SRFD_CURRENT_COMPARATOR_UNAVAILABLE_DUE_EXISTING_SRFDI_WP10_V07_SEGMENTATION_BINDING_BLOCKER",
            "WP6_EQUIVALENCE_PROOF_IS_SEMANTIC_NOT_CANONICAL_RUNTIME_BYTE_STREAM_EQUIVALENCE",
            "REAL_SOURCE_RESTART_EQUIVALENCE_NOT_SEPARATELY_MATERIALIZED_IN_WP6_POSTRUN_PACKET",
        }
        self.assertEqual(set(self.qa["warnings"]), expected)
        self.assertEqual(self.qa["blockers"], [])

if __name__ == "__main__":
    unittest.main()
