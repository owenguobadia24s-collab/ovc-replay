import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
DECISION = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6-signature-contract-supersession/C2E2_G6_SIGNATURE_CONTRACT_SUPERSESSION_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_26.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"

class C2E2G6SignatureContractSupersessionOperatorDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_decision_exact(self):
        self.assertEqual(
            self.decision["operator_command"],
            "OVC APPROVE C2E2-G6-SIGNATURE-CONTRACT-SUPERSESSION SUPERSEDE",
        )
        self.assertEqual(self.decision["decision"], "SUPERSEDE")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")

    def test_authority_is_bounded_and_wp6_remains_denied(self):
        delta = self.decision["authority_delta"]
        self.assertEqual(delta["versioned_c2e_handoff_signature_contract"], "AUTHORIZED_BOUNDED_CANDIDATE")
        self.assertEqual(delta["versioned_c2e_input_frame_schema_adapter"], "AUTHORIZED_BOUNDED_CANDIDATE")
        self.assertEqual(delta["new_numeric_thresholds"], "DENIED")
        self.assertEqual(delta["new_structural_axes_or_categories"], "DENIED")
        self.assertEqual(delta["upstream_c2_identity_mutation"], "DENIED")
        self.assertEqual(delta["wp6_execution"], "DENIED_UNTIL_FRESH_EXACT_C2E2_G6_RUN_AUTH_OPERATOR_DECISION")
        self.assertEqual(delta["active_c2e"], "NONE")
        self.assertEqual(delta["active_boundary_pack"], "NONE")

    def test_decision_state_advances_to_signature_repair_and_later_progression_is_explicit(self):
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.state["current_gate"], "C2E2-G6-SIGNATURE-CONTRACT-SUPERSESSION")
        self.assertEqual(self.state["next_packet"], "C2E2-G6-SIGNATURE-CONTRACT-REPAIR")
        self.assertIn(
            "C2E2-G6-SIGNATURE-CONTRACT-SUPERSESSION.OPERATOR.SUPERSEDE.20260809T100800+0100",
            self.pointer["operator_decision_history"],
        )
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
        if self.pointer.get("ag3") == "EXECUTED_PASS_ACTIVATE_NAMED_PACK":
            self.assertEqual(self.pointer["active_c2e"], "ACTIVE_EXACT_NAMED_PACK_SCOPE_BOUND")
            self.assertEqual(self.pointer["active_boundary_pack"], PACK_ID)
        else:
            self.assertEqual(self.pointer["active_c2e"], "NONE")
            self.assertEqual(self.pointer["active_boundary_pack"], "NONE")

if __name__ == "__main__":
    unittest.main()
