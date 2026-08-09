import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
DECISION = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp6/C2E2_G6_BINDING_SUPERSESSION_OPERATOR_DECISION.json"
RECEIPT = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp6/C2E2_G6_OLD_TOKEN_INVALIDATION_RECEIPT.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_24.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
OLD_REGISTRY = ROOT / "registries/implementation/c2e_v0_2/run_authority/C2E2_SOURCE_REPLAY_AUTHORITY_REGISTRY_v0_1.json"

class C2E2G6BindingSupersessionOperatorDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.old = json.loads(OLD_REGISTRY.read_text())["tokens"][0]

    def test_operator_decision_exact(self):
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE C2E2-G6-BINDING-SUPERSESSION SUPERSEDE")
        self.assertEqual(self.decision["decision"], "SUPERSEDE")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")

    def test_old_token_invalidated_unconsumed_without_history_rewrite(self):
        self.assertEqual(self.old["status"], "AUTHORIZED_UNCONSUMED")
        self.assertFalse(self.old["consumed"])
        self.assertFalse(self.old["invalidated"])
        self.assertTrue(self.receipt["invalidated"])
        self.assertFalse(self.receipt["consumed"])
        self.assertTrue(self.receipt["reuse_prohibited"])
        self.assertFalse(self.receipt["historical_token_registry_mutated"])
        self.assertEqual(self.receipt["token_id"], self.old["token_id"])

    def test_supersession_preparation_only_no_wp6_execution(self):
        delta = self.decision["authority_delta"]
        self.assertEqual(delta["superseding_base_c2_observation_frame_population_preparation"], "AUTHORIZED_BOUNDED")
        self.assertEqual(delta["superseding_empirical_boundary_pack_creation"], "AUTHORIZED_INACTIVE_CANDIDATE_ONLY")
        self.assertEqual(delta["wp6_execution"], "DENIED_UNTIL_FRESH_EXACT_C2E2_G6_RUN_AUTH_OPERATOR_DECISION")
        self.assertEqual(delta["active_c2e"], "NONE")
        self.assertEqual(delta["active_boundary_pack"], "NONE")

    def test_historical_supersession_state_is_preserved_during_later_lawful_progression(self):
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.state["next_packet"], "C2E2-G6-BINDING-REPAIR")
        self.assertEqual(self.pointer["old_run_token_status"], "INVALIDATED_UNCONSUMED_BY_OPERATOR_SUPERSESSION")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertIn(self.pointer["wp6_execution"], {
            "DENIED_UNTIL_FRESH_EXACT_C2E2_G6_RUN_AUTH_OPERATOR_DECISION",
            "AUTHORIZED_NOT_STARTED",
            "EXECUTED_EVIDENCE_PENDING_QA",
            "COMPLETED",
        })
        if self.pointer["wp6_execution"] in {"AUTHORIZED_NOT_STARTED", "EXECUTED_EVIDENCE_PENDING_QA", "COMPLETED"}:
            self.assertIn(
                "C2E2-G6-RUN-AUTH.OPERATOR.AUTHORIZE_EXACT_RUN.20260809T145800+0100",
                self.pointer["operator_decision_history"],
            )
        if self.pointer["wp6_execution"] in {"EXECUTED_EVIDENCE_PENDING_QA", "COMPLETED"}:
            self.assertEqual(self.pointer["replacement_run_token_status"], "CONSUMED_FOR_RUN")
        self.assertIn(
            "C2E2-G6-BINDING-SUPERSESSION.OPERATOR.SUPERSEDE.20260809T084300+0100",
            self.pointer["operator_decision_history"],
        )

if __name__ == "__main__":
    unittest.main()
