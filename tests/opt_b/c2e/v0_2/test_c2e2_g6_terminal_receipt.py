import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6"
RECEIPT = BASE / "C2E2_G6_DEFER_TERMINAL_MERGE_RECEIPT.json"
DECISION = BASE / "C2E2_G6_RUN_AUTH_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_16.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"


class C2E2G6TerminalReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_receipt_binds_exact_decision_head_checks_and_squash_merge(self):
        self.assertEqual(self.receipt["gate_id"], "C2E2-G6-RUN-AUTH")
        self.assertEqual(self.receipt["decision"], "DEFER")
        self.assertEqual(self.receipt["decision_id"], self.decision["decision_id"])
        self.assertEqual(self.receipt["pr_number"], 444)
        self.assertEqual(self.receipt["pr_head"], "3e3eef272b157111295ed9b3a23979091a9df6a7")
        self.assertEqual(self.receipt["pr_base_main"], "549b09e6a6e98366db12a07e57bb2d0991c3b6f6")
        self.assertEqual(self.receipt["merge_method"], "SQUASH")
        self.assertEqual(self.receipt["merge_commit"], "a35543c0845f1af70d896a449bd9739af753b8f4")
        self.assertTrue(all(row["conclusion"] == "SUCCESS" for row in self.receipt["final_assurance"].values()))

    def test_terminal_g6_state_remains_immutable_history(self):
        self.assertEqual(self.state["status"], "BLOCKED")
        self.assertFalse(self.state["operator_decision_required"])
        self.assertIsNone(self.state["current_packet"])
        self.assertEqual(self.state["current_gate"], "C2E2-G6-RUN-AUTH")
        self.assertIsNone(self.state["next_packet"])
        g6 = next(row for row in self.state["packets"] if row["packet_id"] == "C2E2-G6-RUN-AUTH")
        self.assertEqual(g6["status"], "COMPLETED")
        self.assertEqual(g6["decision"], "DEFER")
        self.assertEqual(g6["merge_commit"], self.receipt["merge_commit"])
        self.assertEqual(g6["candidate_commit"], self.receipt["pr_head"])
        self.assertEqual(len(g6["blockers"]), 4)

    def test_no_runtime_or_reserved_authority_was_granted_at_g6(self):
        authority = self.state["authority"]
        self.assertEqual(authority["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(authority["wp6_execution"], "DENIED")
        self.assertEqual(authority["c2e_activation"], "DENIED")
        self.assertEqual(authority["active_boundary_pack"], "NONE")
        self.assertEqual(authority["selector_publication_validation"], "DENIED")
        self.assertEqual(authority["family_semantic_probability_risk_exposure_execution"], "NONE")
        self.assertEqual(self.receipt["authority_delta"], "NONE")

    def test_current_pointer_may_advance_but_g6_replay_denial_persists(self):
        self.assertEqual(self.pointer["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_18.json")
        self.assertEqual(self.pointer["status"], "GATE_READY")
        self.assertEqual(self.pointer["current_gate"], "C2E-AG0")
        self.assertEqual(self.pointer["operator_decision"], "DEFER")
        self.assertEqual(self.pointer["candidate_admissibility"], "DEFERRED_NOT_ADMITTED")
        self.assertEqual(self.pointer["replay_status"], "DEFERRED")
        self.assertEqual(self.pointer["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(self.pointer["wp6_execution"], "DENIED")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertIn("STOP_C2E_AG0_DEFERRED", self.pointer["next_action"])


if __name__ == "__main__":
    unittest.main()
