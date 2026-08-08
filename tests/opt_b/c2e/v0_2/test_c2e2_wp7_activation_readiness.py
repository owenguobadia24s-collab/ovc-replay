import json
from pathlib import Path
import unittest

from ovc.opt_b.c2e_v2.boundary_pack import freeze_pack

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp7"
PACKET = BASE / "C2E2_WP7_ACTIVATION_READINESS_PACKET.json"
CONTINUATION = BASE / "C2E2_WP7_REPLAY_DEFERRED_CONTINUATION.json"
QA = BASE / "C2E2_WP7_QA_PACKET.json"
DECISION = BASE / "C2E2_G7_DELEGATED_DECISION.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_17_CANDIDATE.json"
SCHEMA = ROOT / "schemas/opt_b/c2e/v0_2/c2e_activation_readiness_packet_v0_2.schema.json"
PACK = ROOT / "fixtures/opt_b/c2e/v0_2/wp2/boundary_pack.json"
BOUNDARY_REG = ROOT / "registries/opt_b/c2e/v0_2/C2E_BOUNDARY_PACK_REGISTRY_v0_2.json"
AUTH_REG = ROOT / "registries/opt_b/c2e/v0_2/C2E_AUTHORITY_REGISTRY_v0_2.json"
WP5_QA = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp5/C2E2_WP5_QA_PACKET.json"


class C2E2WP7ActivationReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = json.loads(PACKET.read_text())
        cls.continuation = json.loads(CONTINUATION.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.schema = json.loads(SCHEMA.read_text())
        cls.pack = json.loads(PACK.read_text())
        cls.boundary_reg = json.loads(BOUNDARY_REG.read_text())
        cls.auth_reg = json.loads(AUTH_REG.read_text())
        cls.wp5_qa = json.loads(WP5_QA.read_text())

    def test_operator_continuation_is_exact_and_replay_deferred(self):
        self.assertEqual(self.continuation["operator_command"], "OVC CONTINUE C2E2-WP7 REPLAY_STATUS=DEFERRED CONTINUE_THROUGH_AUTO_GATES=YES STOP_AT=C2E-AG0")
        self.assertEqual(self.continuation["decision_authority"], "OPERATOR")
        self.assertEqual(self.continuation["replay_status"], "DEFERRED")
        self.assertEqual(self.continuation["wp6_execution"], "DENIED")
        self.assertEqual(self.continuation["stop_at"], "C2E-AG0")
        self.assertTrue(all(value == "NONE" for value in self.continuation["authority_delta"].values()))

    def test_exact_existing_shadow_pack_identity_reconstructs(self):
        frozen = freeze_pack(self.pack)
        subject = self.packet["candidate_boundary_pack"]
        self.assertEqual(subject["boundary_pack_id"], frozen["boundary_pack_id"])
        self.assertEqual(subject["logical_sha256"], frozen["logical_sha256"])
        self.assertEqual(subject["version"], "SYNTHETIC.WP2.v1")
        self.assertEqual(subject["authority"], "SHADOW")
        self.assertFalse(subject["active"])
        self.assertFalse(subject["canonical"])
        self.assertEqual(subject["population_scope"]["source_population_id"], "SYNTHETIC_ONLY")

    def test_wp5_implementation_evidence_is_preserved_and_no_real_replay_claimed(self):
        self.assertEqual(self.wp5_qa["status"], "PASS")
        self.assertEqual(self.wp5_qa["fixture_status"], "PASS_40_OF_40")
        self.assertEqual(self.wp5_qa["qa_assertions"]["QA-15"], "PASS")
        self.assertFalse(self.wp5_qa["evidence"]["real_source_market_replay_performed"])
        evidence = self.packet["implementation_evidence"]
        self.assertEqual(evidence["fixture_status"], "PASS_40_OF_40")
        self.assertEqual(evidence["qa_15"], "PASS")
        self.assertFalse(evidence["real_source_market_replay_performed"])

    def test_ag0_ready_only_for_operator_review_and_later_gates_not_ready(self):
        self.assertEqual(self.packet["ag0"]["classification"], "OPERATOR_RESERVED")
        self.assertEqual(self.packet["ag0"]["decision_status"], "READY_FOR_OPERATOR_REVIEW")
        self.assertEqual(self.packet["ag0"]["scope"], "SYNTHETIC_ONLY_NONEMPIRICAL")
        self.assertEqual(self.packet["ag1"]["decision_status"], "NOT_READY_REPLAY_DEFERRED")
        self.assertEqual(self.packet["ag2"]["decision_status"], "NOT_READY_REPLAY_DEFERRED")
        self.assertEqual(self.packet["ag3"]["decision_status"], "NOT_EXECUTED")
        self.assertIsNone(self.packet["ag3"]["active_boundary_pack_id"])

    def test_conflict_denominators_and_replay_gap_visible(self):
        metrics = self.packet["conflict_evidence"]["metrics"]
        self.assertEqual(metrics["ambiguous_boundary_rate"], {"numerator": 1, "denominator": 10})
        self.assertEqual(metrics["explicit_conflict_rate"], {"numerator": 1, "denominator": 10})
        self.assertEqual(metrics["peer_owner_collision_rate"], {"numerator": 1, "denominator": 10})
        self.assertEqual(self.packet["conflict_evidence"]["real_source_counterexamples"], "NONE_REPLAY_DEFERRED")
        self.assertIn("SOURCE_REPLAY_DEFERRED_AT_C2E2_G6", self.packet["warnings"])
        self.assertIn("NO_EMPIRICAL_BOUNDARY_PACK_FROZEN", self.packet["warnings"])

    def test_no_active_selector_pack_publication_or_validation_delta(self):
        self.assertFalse(self.boundary_reg["active"])
        self.assertFalse(self.boundary_reg["canonical"])
        self.assertIsNone(self.boundary_reg["active_boundary_pack_id"])
        self.assertFalse(self.auth_reg["active_c2e"])
        self.assertIsNone(self.auth_reg["active_boundary_pack_id"])
        self.assertEqual(self.auth_reg["selector_mutation"], "DENIED")
        self.assertEqual(self.auth_reg["publication"], "DENIED")
        self.assertEqual(self.auth_reg["validation"], "DENIED")
        self.assertEqual(self.packet["authority_after"]["active_c2e"], "NONE")
        self.assertEqual(self.packet["authority_after"]["active_boundary_pack"], "NONE")

    def test_g7_delegated_pass_is_packet_only_and_conditioned_on_final_head(self):
        self.assertEqual(self.qa["status"], "PASS")
        self.assertEqual(self.qa["recommendation"], "PASS")
        self.assertEqual(self.qa["authority_delta"], "NONE")
        self.assertEqual(self.decision["gate_id"], "C2E2-G7")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["gate_classification"], "AUTO_RATIFIABLE_PACKET_COMPLETENESS_ONLY")
        self.assertEqual(self.decision["authority_delta"], "NONE")
        self.assertIn("EXACT_FINAL_HEAD", self.decision["effectiveness_condition"])
        self.assertEqual(self.decision["next_gate"], "C2E-AG0")
        self.assertEqual(self.decision["next_gate_classification"], "OPERATOR_RESERVED")

    def test_state_candidate_is_non_authoritative_and_stops_at_ag0(self):
        self.assertEqual(self.state["state_role"], "NON_AUTHORITATIVE_WP7_MERGE_CANDIDATE")
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertEqual(self.state["current_gate"], "C2E-AG0")
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(self.state["authority"]["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(self.state["authority"]["active_boundary_pack"], "NONE")
        self.assertIn("STOP_AT_C2E_AG0", self.state["next_action"])

    def test_schema_required_fields_and_terminal_next_action(self):
        self.assertEqual(self.schema["properties"]["schema"]["const"], "c2e_activation_readiness_packet/v0_2")
        for field in self.schema["required"]:
            self.assertIn(field, self.packet)
        self.assertEqual(self.packet["next_action"], "STOP_AT_C2E_AG0_OPERATOR_RESERVED")


if __name__ == "__main__":
    unittest.main()
