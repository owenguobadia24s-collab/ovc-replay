import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6"
GATE = BASE / "C2E2_G6_RUN_AUTH_GATE_PACKET.json"
DECISION = BASE / "C2E2_G6_RUN_AUTH_OPERATOR_DECISION.json"
GATE_READY_STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_14.json"
DEFERRED_STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_15.json"
TERMINAL_STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_16.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"


class C2E2G6OperatorDeferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = json.loads(GATE.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.gate_ready = json.loads(GATE_READY_STATE.read_text())
        cls.deferred = json.loads(DEFERRED_STATE.read_text())
        cls.terminal = json.loads(TERMINAL_STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_gate_was_operator_required_and_recommended_defer(self):
        self.assertEqual(self.gate["gate_id"], "C2E2-G6-RUN-AUTH")
        self.assertEqual(self.gate["gate_classification"], "OPERATOR_REQUIRED")
        self.assertEqual(self.gate["recommended_decision"], "DEFER")
        self.assertEqual(self.gate["authority_effect_of_defer"], "NONE")
        self.assertEqual(self.gate["next_action"], "STOP_AT_OPERATOR_GATE")

    def test_missing_exact_run_prerequisites_are_explicit(self):
        prerequisites = self.gate["pass_prerequisites"]
        self.assertEqual(prerequisites["exact_revised_c2_source_population"], "REQUIRED_NOT_FROZEN_IN_C2E2_GATE_RECORD")
        self.assertEqual(prerequisites["readable_external_source_payloads"], "REQUIRED_NOT_VERIFIED_AT_GATE")
        self.assertEqual(prerequisites["frozen_empirical_candidate_or_shadow_boundary_pack"], "REQUIRED_NOT_REGISTERED_AS_ELIGIBLE")
        self.assertEqual(prerequisites["exact_source_run_manifest"], "REQUIRED_NOT_FROZEN")
        self.assertEqual(prerequisites["exact_resource_envelope"], "REQUIRED_OPERATOR_DECISION_NOT_YET_DEFINED")
        self.assertEqual(prerequisites["validation"], "LOCKED_DENIED")
        self.assertEqual(prerequisites["srfd_token_reuse"], "FORBIDDEN")
        self.assertEqual(len(self.gate["unresolved_issues"]), 4)

    def test_operator_defer_is_exact_and_grants_no_authority(self):
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE C2E2-G6-RUN-AUTH DEFER")
        self.assertEqual(self.decision["decision"], "DEFER")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        self.assertEqual(self.decision["authority_delta"], "NONE")
        effects = self.decision["effects"]
        self.assertEqual(effects["wp6_execution"], "DENIED")
        self.assertEqual(effects["source_run_token"], "NONE")
        self.assertEqual(effects["empirical_pack_selection"], "NONE")
        self.assertEqual(effects["provider_fetch"], "NOT_AUTHORIZED")
        self.assertEqual(effects["validation_consumption"], "DENIED")
        self.assertEqual(effects["publication"], "DENIED")

    def test_gate_ready_deferred_and_terminal_states_are_append_only_history(self):
        self.assertEqual(self.gate_ready["status"], "GATE_READY")
        self.assertTrue(self.gate_ready["operator_decision_required"])
        self.assertEqual(self.gate_ready["current_gate"], "C2E2-G6-RUN-AUTH")
        self.assertEqual(self.gate_ready["authority"]["real_source_replay"], "DENIED_PENDING_C2E2_G6_RUN_AUTH")
        self.assertEqual(self.deferred["status"], "BLOCKED")
        self.assertEqual(self.deferred["current_gate"], "C2E2-G6-RUN-AUTH")
        self.assertEqual(self.deferred["authority"]["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertIn(self.decision["decision_id"], self.deferred["operator_decision_history"])
        self.assertEqual(self.terminal["status"], "BLOCKED")
        self.assertEqual(self.terminal["authority"]["wp6_execution"], "DENIED")
        self.assertEqual(self.terminal["packets"][-1]["merge_commit"], "a35543c0845f1af70d896a449bd9739af753b8f4")

    def test_current_pointer_advances_but_preserves_g6_defer(self):
        self.assertTrue((ROOT / self.pointer["authoritative_state"]).is_file())
        self.assertEqual(self.pointer["current_gate"], "C2E-AG0")
        self.assertEqual(self.pointer["replay_status"], "DEFERRED")
        self.assertEqual(self.pointer["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(self.pointer["wp6_execution"], "DENIED")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertEqual(self.pointer["operator_decision"], "DEFER")
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual(self.pointer["candidate_admissibility"], "DEFERRED_NOT_ADMITTED")


if __name__ == "__main__":
    unittest.main()
