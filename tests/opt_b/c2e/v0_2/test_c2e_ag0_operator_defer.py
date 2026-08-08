import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0"
GATE = BASE / "C2E_AG0_GATE_PACKET.json"
DECISION = BASE / "C2E_AG0_OPERATOR_DECISION.json"
HISTORICAL_STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_17.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_18.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"


class C2EAG0OperatorDeferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = json.loads(GATE.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.historical = json.loads(HISTORICAL_STATE.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_defer_matches_gate_and_grants_no_authority(self):
        self.assertEqual(self.gate["gate_id"], "C2E-AG0")
        self.assertEqual(self.gate["recommended_decision"], "DEFER")
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE C2E-AG0 DEFER")
        self.assertEqual(self.decision["decision"], "DEFER")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        self.assertEqual(self.decision["authority_delta"], "NONE")
        self.assertEqual(self.decision["effects"]["candidate_admissibility"], "DEFERRED_NOT_ADMITTED")
        self.assertEqual(self.decision["effects"]["ag1_progression"], "DENIED_NOT_READY")
        self.assertEqual(self.decision["authority_after"]["active_boundary_pack"], "NONE")
        self.assertEqual(self.decision["authority_after"]["c2e_activation"], "DENIED")

    def test_ag0_defer_is_append_only_successor_to_gate_ready_state(self):
        self.assertEqual(self.historical["status"], "GATE_READY")
        self.assertTrue(self.historical["operator_decision_required"])
        self.assertEqual(self.historical["current_gate"], "C2E-AG0")
        self.assertEqual(self.state["programme_disposition"], "DEFERRED_AT_C2E_AG0")
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.state["operator_decision"], "DEFER")
        self.assertIn(self.decision["decision_id"], self.state["operator_decision_history"])
        ag0 = next(row for row in self.state["packets"] if row["packet_id"] == "C2E-AG0")
        self.assertEqual(ag0["status"], "COMPLETED")
        self.assertEqual(ag0["decision"], "DEFER")
        self.assertEqual(ag0["authority_delta"], "NONE")

    def test_current_pointer_preserves_replay_defer_and_stops(self):
        self.assertEqual(self.pointer["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_18.json")
        self.assertEqual(self.pointer["current_gate"], "C2E-AG0")
        self.assertEqual(self.pointer["status"], "GATE_READY")
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual(self.pointer["operator_decision"], "DEFER")
        self.assertEqual(self.pointer["candidate_admissibility"], "DEFERRED_NOT_ADMITTED")
        self.assertEqual(self.pointer["replay_status"], "DEFERRED")
        self.assertEqual(self.pointer["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(self.pointer["wp6_execution"], "DENIED")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertIn("STOP_C2E_AG0_DEFERRED", self.pointer["next_action"])

    def test_review_subject_remains_synthetic_nonempirical_and_unadmitted(self):
        self.assertEqual(self.decision["review_subject"]["boundary_pack_id"], self.gate["review_subject"]["boundary_pack_id"])
        self.assertEqual(self.decision["review_subject"]["logical_sha256"], self.gate["review_subject"]["logical_sha256"])
        self.assertEqual(self.decision["review_subject"]["scope"], "SYNTHETIC_ONLY_NONEMPIRICAL")
        self.assertEqual(self.pointer["candidate_review_scope"], "SYNTHETIC_ONLY_NONEMPIRICAL")
        self.assertEqual(self.pointer["candidate_admissibility"], "DEFERRED_NOT_ADMITTED")


if __name__ == "__main__":
    unittest.main()
