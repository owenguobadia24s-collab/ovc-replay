import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0"
RECEIPT = BASE / "C2E_AG0_DEFER_TERMINAL_MERGE_RECEIPT.json"
DECISION = BASE / "C2E_AG0_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_19.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"


class C2EAG0DeferTerminalReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_receipt_binds_exact_operator_decision_and_squash_merge(self):
        self.assertEqual(self.receipt["gate_id"], "C2E-AG0")
        self.assertEqual(self.receipt["decision"], "DEFER")
        self.assertEqual(self.receipt["decision_id"], self.decision["decision_id"])
        self.assertEqual(self.receipt["pr_number"], 456)
        self.assertEqual(self.receipt["pr_head"], "5692056473af32a1b50a4532f3ba1d6fd7297973")
        self.assertEqual(self.receipt["pr_base_main"], "02718698b6dcb1b956ae7a34b767d5148f00aeb9")
        self.assertEqual(self.receipt["merge_method"], "SQUASH")
        self.assertEqual(self.receipt["merge_commit"], "380ac82ca1e98c6adeccff5a91829fbf1d4c1e0d")
        self.assertTrue(all(row["conclusion"] == "SUCCESS" for row in self.receipt["final_assurance"].values()))

    def test_terminal_state_preserves_defer_and_no_authority_delta(self):
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["current_gate"], "C2E-AG0")
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.state["operator_decision"], "DEFER")
        ag0 = next(row for row in self.state["packets"] if row["packet_id"] == "C2E-AG0")
        self.assertEqual(ag0["status"], "COMPLETED")
        self.assertEqual(ag0["decision"], "DEFER")
        self.assertEqual(ag0["candidate_commit"], self.receipt["pr_head"])
        self.assertEqual(ag0["merge_commit"], self.receipt["merge_commit"])
        self.assertEqual(ag0["authority_delta"], "NONE_AFTER_DEFER")
        authority = self.state["authority"]
        self.assertEqual(authority["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(authority["wp6_execution"], "DENIED")
        self.assertEqual(authority["c2e_activation"], "DENIED")
        self.assertEqual(authority["active_boundary_pack"], "NONE")

    def test_pointer_is_terminal_for_this_decision_and_forward_only(self):
        self.assertEqual(self.pointer["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_19.json")
        self.assertEqual(self.pointer["current_gate"], "C2E-AG0")
        self.assertEqual(self.pointer["operator_decision"], "DEFER")
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual(self.pointer["candidate_admissibility"], "DEFERRED_NOT_ADMITTED")
        self.assertEqual(self.pointer["merge_receipt"], "docs/releases/c2e-causal-episode-v0-2/c2e-ag0/C2E_AG0_DEFER_TERMINAL_MERGE_RECEIPT.json")
        self.assertEqual(self.pointer["replay_status"], "DEFERRED")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertTrue(self.pointer["next_action"].startswith("STOP_C2E_AG0_DEFERRED"))


if __name__ == "__main__":
    unittest.main()
