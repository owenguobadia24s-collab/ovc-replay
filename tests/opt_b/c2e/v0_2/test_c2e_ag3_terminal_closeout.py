import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
REL = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag3"
BASE = ROOT / "registries/implementation/c2e_v0_2"
PACK_REGISTRY = ROOT / "registries/opt_b/c2e/v0_2/C2E_BOUNDARY_PACK_REGISTRY_v0_2.json"
AUTH_REGISTRY = ROOT / "registries/opt_b/c2e/v0_2/C2E_AUTHORITY_REGISTRY_v0_2.json"
PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
MERGE_SHA = "04726c84d534249efeac5391bb10785cf37d57fd"


def load(path):
    return json.loads(path.read_text())


class C2EAG3TerminalCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = load(REL / "C2E_AG3_TERMINAL_MERGE_RECEIPT.json")
        cls.closeout = load(REL / "C2E_AG3_CLOSEOUT_DELEGATED_DECISION.json")
        cls.state = load(BASE / "OVC_C2E2_STATE_v0_45_AG3_TERMINAL.json")
        cls.pointer = load(BASE / "CURRENT_STATE_POINTER.json")
        cls.pack_registry = load(PACK_REGISTRY)
        cls.auth_registry = load(AUTH_REGISTRY)

    def test_activation_merge_and_final_assurance_are_pinned(self):
        self.assertEqual(self.receipt["merge_commit"], MERGE_SHA)
        self.assertEqual(self.receipt["merge_method"], "SQUASH")
        self.assertEqual(self.receipt["pr_number"], 608)
        self.assertTrue(all(
            row["conclusion"] == "SUCCESS"
            for row in self.receipt["final_assurance"].values()
            if isinstance(row, dict) and "conclusion" in row
        ))
        self.assertEqual(self.receipt["final_assurance"]["unresolved_review_threads"], 0)

    def test_closeout_is_zero_authority_and_terminal(self):
        self.assertEqual(self.closeout["decision"], "PASS")
        self.assertEqual(self.closeout["authority_delta"], "NONE")
        self.assertIsNone(self.closeout["next_packet"])
        self.assertIsNone(self.closeout["next_gate"])
        self.assertEqual(self.state["status"], "COMPLETED")
        self.assertEqual(self.state["merge_commit"], MERGE_SHA)
        self.assertIsNone(self.state["next_packet"])
        self.assertIsNone(self.state["next_gate"])

    def test_pointer_resolves_terminal_state_and_exact_active_pack(self):
        self.assertEqual(
            self.pointer["authoritative_state"],
            "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_45_AG3_TERMINAL.json",
        )
        self.assertEqual(self.pointer["current_packet"], "C2E-AG3-CLOSEOUT")
        self.assertEqual(self.pointer["ag3"], "EXECUTED_PASS_ACTIVATE_NAMED_PACK")
        self.assertEqual(self.pointer["ag3_merge_commit"], MERGE_SHA)
        self.assertEqual(self.pointer["active_boundary_pack"], PACK_ID)
        self.assertEqual(self.pointer["active_c2e"], "ACTIVE_EXACT_NAMED_PACK_SCOPE_BOUND")
        self.assertIsNone(self.pointer["next_gate"])
        self.assertIsNone(self.pointer["next_packet"])

    def test_runtime_authority_is_exact_and_downstream_denials_hold(self):
        self.assertEqual(self.pack_registry["active_boundary_pack_id"], PACK_ID)
        self.assertTrue(self.pack_registry["production_pack_selected"])
        self.assertTrue(self.pack_registry["active"])
        self.assertFalse(self.pack_registry["canonical"])
        self.assertTrue(self.auth_registry["active_c2e"])
        self.assertEqual(self.auth_registry["active_boundary_pack_id"], PACK_ID)
        self.assertEqual(self.auth_registry["publication"], "DENIED")
        self.assertEqual(self.auth_registry["validation"], "DENIED")
        self.assertEqual(self.auth_registry["family_semantic_probability_risk_exposure_execution"], "NONE")
        self.assertEqual(self.auth_registry["agent_write"], "NONE")


if __name__ == "__main__":
    unittest.main()
