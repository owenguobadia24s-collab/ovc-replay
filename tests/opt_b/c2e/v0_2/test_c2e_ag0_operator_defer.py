import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0"
GATE = BASE / "C2E_AG0_GATE_PACKET.json"
DECISION = BASE / "C2E_AG0_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_18.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"


class C2EAG0OperatorDeferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = json.loads(GATE.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_defer_is_exact(self):
        self.assertEqual(self.gate["gate_id"], "C2E-AG0")
        self.assertEqual(self.gate["gate_classification"], "OPERATOR_RESERVED")
        self.assertEqual(self.gate["recommended_decision"], "DEFER")
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE C2E-AG0 DEFER")
        self.assertEqual(self.decision["decision"], "DEFER")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        self.assertEqual(self.decision["authority_delta"], "NONE")

    def test_exact_synthetic_subject_is_deferred_not_admitted(self):
        subject = self.decision["review_subject"]
        self.assertEqual(subject["boundary_pack_id"], "C2E.BOUNDARY.PACK.5e4f9df8a35d1608416c65329b5a98b2")
        self.assertEqual(subject["logical_sha256"], "5e4f9df8a35d1608416c65329b5a98b2b2e6e381197a03d2321a1ca413c33a25")
        self.assertEqual(subject["scope"], "SYNTHETIC_ONLY_NONEMPIRICAL")
        self.assertEqual(self.decision["effects"]["candidate_admissibility"], "DEFERRED_NOT_ADMITTED")
        self.assertEqual(self.decision["effects"]["ag1_progression"], "DENIED_NOT_READY")
        self.assertEqual(self.decision["effects"]["ag2_progression"], "DENIED_NOT_READY")

    def test_defer_grants_no_runtime_or_activation_authority(self):
        effects = self.decision["effects"]
        self.assertEqual(effects["wp6_execution"], "DENIED")
        self.assertEqual(effects["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(effects["active_c2e"], "NONE")
        self.assertEqual(effects["active_boundary_pack"], "NONE")
        self.assertEqual(effects["selector_mutation"], "DENIED")
        self.assertEqual(effects["publication"], "DENIED")
        self.assertEqual(effects["validation"], "DENIED")
        self.assertEqual(effects["family_semantic_probability_risk_exposure_execution"], "NONE")

    def test_state_remains_deferred_while_pointer_may_advance(self):
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["current_gate"], "C2E-AG0")
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.state["operator_decision"], "DEFER")
        self.assertIn(self.decision["decision_id"], self.state["operator_decision_history"])
        current_path = ROOT / self.pointer["authoritative_state"]
        self.assertTrue(current_path.is_file())
        current = json.loads(current_path.read_text())
        self.assertIn(self.decision["decision_id"], current.get("operator_decision_history", []))
        if self.pointer.get("ag3") == "EXECUTED_PASS_ACTIVATE_NAMED_PACK":
            self.assertEqual(self.pointer["active_c2e"], "ACTIVE_EXACT_NAMED_PACK_SCOPE_BOUND")
            self.assertEqual(self.pointer["active_boundary_pack"], PACK_ID)
            self.assertEqual(current["authority"]["ag3_activation_or_replacement"], "ACTIVATE_NAMED_PACK_PASS")
            self.assertEqual(current["authority"]["active_boundary_pack"], PACK_ID)
        else:
            self.assertEqual(self.pointer["active_c2e"], "NONE")
            self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
            self.assertIn(current["authority"]["c2e_activation"], {"DENIED", "DENIED_OPERATOR_RESERVED"})
            self.assertEqual(current["authority"]["active_boundary_pack"], "NONE")


if __name__ == "__main__":
    unittest.main()
