import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "registries/implementation/c2e_v0_2"
AG0 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0-r2"
AG1 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag1"
AG0_DECISION = AG0 / "C2E_AG0_R2_OPERATOR_DECISION.json"
AG0_RECEIPT = AG0 / "C2E_AG0_R2_TERMINAL_MERGE_RECEIPT.json"
GATE = AG1 / "C2E_AG1_GATE_PACKET.json"
QA = AG1 / "C2E_AG1_GATE_PREP_QA_PACKET.json"
STATE = BASE / "OVC_C2E2_STATE_v0_33.json"
POINTER = BASE / "CURRENT_STATE_POINTER.json"

PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
PACK_HASH = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
AG0_PASS_ID = "C2E-AG0.OPERATOR.PASS.20260809T213300+0100"

class C2EAG1GateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ag0 = json.loads(AG0_DECISION.read_text())
        cls.receipt = json.loads(AG0_RECEIPT.read_text())
        cls.gate = json.loads(GATE.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_ag0_pass_and_merge_receipt_are_exact_prerequisites(self):
        self.assertEqual(self.ag0["decision_id"], AG0_PASS_ID)
        self.assertEqual(self.ag0["decision"], "PASS")
        self.assertEqual(self.receipt["decision_id"], AG0_PASS_ID)
        self.assertEqual(self.receipt["merge_commit"], "dd2182f22b0223f7193332dfc7b482509031ceeb")
        self.assertEqual(self.receipt["final_assurance"]["complete_repository_suite"]["conclusion"], "SUCCESS")
        self.assertEqual(self.receipt["final_assurance"]["profile_tiered_merge_readiness"]["conclusion"], "SUCCESS")

    def test_gate_is_operator_reserved_and_exact_subject_is_unchanged(self):
        self.assertEqual(self.gate["gate_id"], "C2E-AG1")
        self.assertEqual(self.gate["gate_classification"], "OPERATOR_RESERVED")
        self.assertEqual(self.gate["decision_status"], "PENDING_OPERATOR")
        self.assertEqual(self.gate["allowed_decisions"], ["PASS", "DEFER", "BLOCK"])
        subject = self.gate["review_subject"]
        self.assertEqual(subject["boundary_pack_id"], PACK_ID)
        self.assertEqual(subject["logical_sha256"], PACK_HASH)
        self.assertEqual(subject["population_scope"]["target_frame_count"], 4072)
        self.assertFalse(subject["active"])
        self.assertFalse(subject["canonical"])

    def test_replay_evidence_is_complete_except_real_source_restart_equivalence(self):
        conditions = self.gate["acceptance_conditions"]
        self.assertEqual(conditions["exact_source_run_manifest"], "PASS")
        self.assertEqual(conditions["two_clean_run_determinism"], "PASS")
        self.assertEqual(conditions["source_coverage"], "PASS_4072_FRAMES")
        self.assertTrue(conditions["gap_and_release_reconciliation"].startswith("PASS"))
        self.assertTrue(conditions["split_merge_nest_reparent_conflict_topology_fixture_evidence"].startswith("PASS"))
        self.assertEqual(conditions["capacity_envelope"], "PASS_WITHIN_T0")
        self.assertTrue(conditions["restart_equivalence"].startswith("NOT_MET_"))
        self.assertEqual(len(self.gate["required_evidence_gaps"]), 1)
        self.assertEqual(self.gate["required_evidence_gaps"][0]["id"], "C2E-AG1-GAP-001")
        self.assertTrue(self.gate["required_evidence_gaps"][0]["must_not_infer"])

    def test_gate_recommends_defer_without_hiding_or_reclassifying_gap(self):
        self.assertEqual(self.gate["recommended_decision"], "DEFER")
        self.assertEqual(self.qa["qa_disposition"], "PASS_FOR_OPERATOR_REVIEW")
        self.assertEqual(self.qa["operator_gate_recommendation"], "DEFER")
        self.assertEqual(self.qa["blockers_to_gate_preparation"], [])
        self.assertEqual(self.qa["blockers_to_recommended_ag1_pass"], ["C2E-AG1-GAP-001_RESTART_EQUIVALENCE"])
        self.assertIn("REAL_SOURCE_RESTART_EQUIVALENCE_NOT_SEPARATELY_MATERIALIZED_IN_WP6_POSTRUN_PACKET", self.gate["warnings"])

    def test_no_ag2_or_activation_authority_is_granted_by_gate_preparation(self):
        current = self.gate["current_authority"]
        self.assertEqual(current["ag0_admissibility"], "PASS")
        self.assertEqual(current["ag2_progression"], "DENIED_PENDING_AG1")
        self.assertEqual(current["ag3_activation_or_replacement"], "DENIED_OPERATOR_RESERVED")
        self.assertEqual(current["active_c2e"], "NONE")
        self.assertEqual(current["active_boundary_pack"], "NONE")
        delta = self.gate["proposed_delta_if_pass"]
        self.assertEqual(delta["active_c2e"], "NONE")
        self.assertEqual(delta["active_boundary_pack"], "NONE")
        self.assertEqual(delta["selector_mutation"], "NONE")

    def test_historical_gate_ready_state_is_exact_while_pointer_may_advance_after_gap_resolution(self):
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["current_packet"], "C2E-AG1-PREP")
        self.assertEqual(self.state["current_gate"], "C2E-AG1")
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(self.state["recommended_operator_decision"], "DEFER")
        self.assertEqual(self.state["authority"]["active_c2e"], "NONE")
        self.assertEqual(self.state["authority"]["active_boundary_pack"], "NONE")
        self.assertEqual(self.state["authority"]["ag2_progression"], "DENIED_PENDING_AG1")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        if self.pointer["status"] == "GATE_READY":
            self.assertEqual(self.pointer["current_gate"], "C2E-AG1")
            self.assertTrue(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["recommended_operator_decision"], "DEFER")
            self.assertEqual(self.pointer["next_action"], "STOP_FOR_OPERATOR_C2E_AG1")
        elif self.pointer["status"] == "APPROVED":
            self.assertEqual(self.pointer["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_38.json")
            self.assertEqual(self.pointer["current_packet"], "C2E-AG1-DECISION")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG1")
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["operator_decision"], "PASS")
            self.assertEqual(self.pointer["ag1_replay_adequacy"], "PASS")
            self.assertEqual(self.pointer["ag2_progression"], "AUTHORIZED_FOR_GATE_PREPARATION_ONLY")
            self.assertEqual(self.pointer["next_gate"], "C2E-AG2")
        else:
            self.assertEqual(self.pointer["status"], "COMPLETED")
            self.assertEqual(self.pointer["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_42_AG2_COMPLETED.json")
            self.assertEqual(self.pointer["current_packet"], "C2E-AG2-CLOSEOUT")
            self.assertEqual(self.pointer["current_gate"], "C2E-AG2")
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertEqual(self.pointer["operator_decision"], "PASS")
            self.assertEqual(self.pointer["ag1_replay_adequacy"], "PASS")
            self.assertEqual(self.pointer["ag2_progression"], "COMPLETED_PASS")
            self.assertEqual(self.pointer["next_gate"], "C2E-AG3")
            self.assertEqual(self.pointer["ag3"], "NOT_EXECUTED")

if __name__ == "__main__":
    unittest.main()
