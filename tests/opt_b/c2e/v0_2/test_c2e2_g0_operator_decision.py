import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
DECISION = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g0/C2E2_G0_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_1.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
RO_C2E = ROOT / "registries/research_operations/c2e/OVC_C2E_PROGRAMME_STATE_v0_1.json"
C2AR = ROOT / "registries/opt_b/c2/vnext/C2_INTEGRATED_SHADOW_PACKAGE_APPROVED_v1.jsonc"
HISTORICAL_DEFERRED_STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_15.json"


class C2E2G0OperatorDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.ro_c2e = json.loads(RO_C2E.read_text())
        cls.c2ar = json.loads(C2AR.read_text())

    def test_operator_pass_binds_exact_plan_and_baseline(self):
        self.assertEqual(self.decision["gate_id"], "C2E2-G0")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE C2E2-G0 PASS")
        self.assertEqual(self.decision["baseline_commit"], "a46aedb2208d9ec88a7835ccd5ac04f46214f961")

    def test_authority_is_bounded_to_wp0_wp5(self):
        auth = self.decision["authority_after"]
        self.assertEqual(auth["c2e2_wp0_wp5_repository_build_test"], "AUTHORIZED")
        self.assertEqual(auth["c2e2_wp6_real_source_replay"], "DENIED_PENDING_C2E2_G6_RUN_AUTH")
        self.assertEqual(auth["active_c2e_selector"], "NONE")
        self.assertEqual(auth["canonical_or_r2_publication"], "DENIED")
        self.assertEqual(auth["validation_consumption"], "DENIED")
        self.assertEqual(auth["family_semantic_probability_risk_exposure_execution"], "NONE")

    def test_historical_block_and_c2ar_shadow_remain_immutable_authority(self):
        self.assertEqual(self.ro_c2e["status"], "BLOCKED")
        self.assertEqual(self.ro_c2e["current_gate"], "C2E-G1")
        self.assertEqual(self.ro_c2e["next_action"], "STOP_UNTIL_NEW_IMMUTABLE_OPERATOR_SUPERSESSION")
        self.assertEqual(self.c2ar["package_id"], "C2AR.INTEGRATED.SHADOW.PACKAGE.v1")
        self.assertEqual(self.c2ar["status"], "IMPLEMENTED_SHADOW_COMPLETE")
        self.assertFalse(self.c2ar["active"])
        self.assertFalse(self.c2ar["canonical"])

    def test_g0_historical_state_stays_immutable_while_pointer_advances(self):
        self.assertEqual(self.state["status"], "READY")
        self.assertEqual(self.state["current_packet"], "C2E2-WP0")
        self.assertEqual(self.state["current_gate"], "C2E2-G1")
        self.assertFalse(self.state["operator_decision_required"])
        self.assertTrue(HISTORICAL_DEFERRED_STATE.is_file())
        historical_defer = json.loads(HISTORICAL_DEFERRED_STATE.read_text())
        self.assertEqual(historical_defer["status"], "BLOCKED")
        self.assertEqual(historical_defer["current_gate"], "C2E2-G6-RUN-AUTH")
        current = self.pointer["authoritative_state"]
        self.assertTrue((ROOT / current).is_file())
        self.assertEqual(self.pointer["programme_id"], "OVC-C2E-CAUSAL-EPISODE-CONFORMANCE-v0.2")
        self.assertEqual(self.pointer["status"], "GATE_READY")
        self.assertEqual(self.pointer["current_gate"], "C2E-AG0")
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual(self.pointer["operator_decision"], "DEFER")
        self.assertEqual(self.pointer["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(self.pointer["wp6_execution"], "DENIED")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertEqual(self.pointer["candidate_admissibility"], "DEFERRED_NOT_ADMITTED")


if __name__ == "__main__":
    unittest.main()
