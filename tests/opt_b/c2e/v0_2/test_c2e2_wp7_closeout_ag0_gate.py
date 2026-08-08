import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
WP7 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp7"
AG0 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0"
RECEIPT = WP7 / "C2E2_WP7_TERMINAL_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_17.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
GATE = AG0 / "C2E_AG0_GATE_PACKET.json"


class C2E2WP7CloseoutAG0GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.gate = json.loads(GATE.read_text())

    def test_wp7_receipt_binds_exact_squash_and_final_assurance(self):
        self.assertEqual(self.receipt["packet_id"], "C2E2-WP7")
        self.assertEqual(self.receipt["gate_id"], "C2E2-G7")
        self.assertEqual(self.receipt["decision"], "PASS")
        self.assertEqual(self.receipt["pr_number"], 451)
        self.assertEqual(self.receipt["pr_head"], "5337845dfeb756012ad5b991563df1706d1b0efa")
        self.assertEqual(self.receipt["merge_method"], "SQUASH")
        self.assertEqual(self.receipt["merge_commit"], "77ac40e613b8f0ffd05935f34eaf6b4eb444c3ff")
        self.assertTrue(all(row["conclusion"] == "SUCCESS" for row in self.receipt["final_assurance"].values()))
        self.assertEqual(self.receipt["authority_delta"], "NONE")

    def test_authoritative_state_is_gate_ready_at_operator_reserved_ag0(self):
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["current_gate"], "C2E-AG0")
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(self.state["packets"][-1]["packet_id"], "C2E2-WP7")
        self.assertEqual(self.state["packets"][-1]["status"], "COMPLETED")
        self.assertEqual(self.state["packets"][-1]["merge_commit"], self.receipt["merge_commit"])
        self.assertEqual(self.state["authority"]["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(self.state["authority"]["wp6_execution"], "DENIED")
        self.assertEqual(self.state["authority"]["active_boundary_pack"], "NONE")
        self.assertEqual(self.state["authority"]["c2e_activation"], "DENIED")

    def test_pointer_advances_without_rewriting_g6_defer(self):
        self.assertEqual(self.pointer["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_18.json")
        self.assertEqual(self.pointer["status"], "GATE_READY")
        self.assertEqual(self.pointer["current_gate"], "C2E-AG0")
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual(self.pointer["operator_decision"], "DEFER")
        self.assertEqual(self.pointer["candidate_admissibility"], "DEFERRED_NOT_ADMITTED")
        self.assertEqual(self.pointer["replay_status"], "DEFERRED")
        self.assertEqual(self.pointer["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(self.pointer["wp6_execution"], "DENIED")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertIn("STOP_C2E_AG0_DEFERRED", self.pointer["next_action"])

    def test_ag0_gate_is_consolidated_and_does_not_hide_replay_gap(self):
        self.assertEqual(self.gate["gate_id"], "C2E-AG0")
        self.assertEqual(self.gate["gate_classification"], "OPERATOR_RESERVED")
        self.assertEqual(self.gate["allowed_decisions"], ["PASS", "DEFER", "BLOCK"])
        self.assertEqual(self.gate["candidate_commit"], self.receipt["merge_commit"])
        self.assertEqual(self.gate["review_subject"]["boundary_pack_id"], "C2E.BOUNDARY.PACK.5e4f9df8a35d1608416c65329b5a98b2")
        self.assertEqual(self.gate["review_subject"]["classification"], "SYNTHETIC_SHADOW_ONLY_NONEMPIRICAL_REVIEW_SUBJECT")
        self.assertEqual(self.gate["acceptance_conditions"]["empirical_candidate_pack"], "ABSENT")
        self.assertEqual(self.gate["acceptance_conditions"]["real_source_replay"], "DEFERRED")
        self.assertEqual(self.gate["recommended_decision"], "DEFER")
        self.assertEqual(len(self.gate["warnings"]), 4)
        self.assertEqual(len(self.gate["unresolved_issues"]), 4)
        self.assertEqual(self.gate["external_artifact_hashes"], [])
        self.assertEqual(self.gate["next_action"], "STOP_AT_OPERATOR_GATE_C2E_AG0")


if __name__ == "__main__":
    unittest.main()
