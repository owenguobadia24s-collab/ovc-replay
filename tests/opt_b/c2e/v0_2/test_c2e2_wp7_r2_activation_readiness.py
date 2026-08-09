import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp7-r2"
PACKET = BASE / "C2E2_WP7_R2_ACTIVATION_READINESS_PACKET.json"
CONTINUATION = BASE / "C2E2_WP7_R2_CONTINUATION.json"
QA = BASE / "C2E2_WP7_R2_QA_PACKET.json"
DECISION = BASE / "C2E2_G7_R2_DELEGATED_DECISION.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_31_CANDIDATE.json"
SCHEMA = ROOT / "schemas/opt_b/c2e/v0_2/c2e_activation_readiness_packet_v0_2.schema.json"
PACK = ROOT / "registries/opt_b/c2e/v0_2/C2E_EMPIRICAL_BOUNDARY_PACK_JUNE_STABLE_v0_2.json"
WP6_QA = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp6/C2E2_WP6_POSTRUN_QA_PACKET.json"
WP6_EQ = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp6/C2E2_WP6_EQUIVALENCE_PROOF.json"
WP6_COMP = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp6/C2E2_WP6_COMPARATOR_STATUS.json"
HISTORICAL_WP7 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp7/C2E2_WP7_ACTIVATION_READINESS_PACKET.json"
HISTORICAL_AG0 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0/C2E_AG0_OPERATOR_DECISION.json"


class C2E2WP7R2ActivationReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = json.loads(PACKET.read_text())
        cls.continuation = json.loads(CONTINUATION.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.schema = json.loads(SCHEMA.read_text())
        cls.pack = json.loads(PACK.read_text())
        cls.wp6_qa = json.loads(WP6_QA.read_text())
        cls.wp6_eq = json.loads(WP6_EQ.read_text())
        cls.wp6_comp = json.loads(WP6_COMP.read_text())
        cls.historical_wp7 = json.loads(HISTORICAL_WP7.read_text())
        cls.historical_ag0 = json.loads(HISTORICAL_AG0.read_text())

    def test_continuation_is_exact_bounded_and_post_wp6(self):
        self.assertEqual(self.continuation["operator_instruction"], "OVC Continue C2E2")
        self.assertEqual(self.continuation["baseline_main"], "4adec4ab6d5f6a41e153be06d48f1cd2537fa927")
        self.assertEqual(self.continuation["replay_status"], "EXECUTED")
        self.assertEqual(self.continuation["authority_delta"], "NONE")
        self.assertEqual(self.continuation["active_c2e"], "NONE")
        self.assertEqual(self.continuation["active_boundary_pack"], "NONE")
        self.assertEqual(self.continuation["stop_at"], "C2E-AG0")

    def test_schema_required_fields_and_executed_terminal_action(self):
        self.assertEqual(self.schema["properties"]["schema"]["const"], "c2e_activation_readiness_packet/v0_2")
        self.assertIn("EXECUTED", self.schema["properties"]["replay_status"]["enum"])
        for field in self.schema["required"]:
            self.assertIn(field, self.packet)
        self.assertEqual(self.packet["schema"], "c2e_activation_readiness_packet/v0_2")
        self.assertEqual(self.packet["replay_status"], "EXECUTED")
        self.assertEqual(self.packet["next_action"], "STOP_AT_C2E_AG0_OPERATOR_RESERVED")

    def test_exact_empirical_pack_and_population_identity(self):
        subject = self.packet["candidate_boundary_pack"]
        self.assertEqual(subject["boundary_pack_id"], self.pack["boundary_pack_id"])
        self.assertEqual(subject["logical_sha256"], self.pack["logical_sha256"])
        self.assertEqual(subject["version"], self.pack["version"])
        self.assertEqual(subject["source_blob_sha"], "dc12ed68d55b14579bcd0050a3f102979781656b")
        self.assertEqual(subject["authority"], "CANDIDATE")
        self.assertFalse(subject["active"])
        self.assertFalse(subject["canonical"])
        self.assertEqual(subject["population_scope"]["logical_population_sha256"], self.pack["population_scope"]["logical_population_sha256"])
        self.assertEqual(subject["population_scope"]["target_frame_count"], 4072)

    def test_wp6_real_source_evidence_is_exact_and_not_promotional(self):
        evidence = self.packet["implementation_evidence"]
        self.assertTrue(evidence["real_source_market_replay_performed"])
        self.assertEqual(evidence["run_manifest_id"], self.wp6_qa["frozen_inputs"]["run_manifest_id"])
        self.assertEqual(evidence["run_manifest_logical_sha256"], self.wp6_qa["frozen_inputs"]["run_manifest_logical_sha256"])
        self.assertEqual(evidence["logical_output_sha256"], self.wp6_eq["independent_checks"][-1]["logical_output_sha256"])
        self.assertEqual(self.wp6_qa["qa_disposition"], "PASS_WITH_NONBLOCKING_WARNINGS")
        self.assertEqual(self.wp6_qa["authority_effect"], "NONE")
        self.assertEqual(evidence["canonical_runtime_byte_stream_equivalence"], "NOT_CLAIMED")

    def test_real_source_conflict_and_negative_evidence_are_visible(self):
        metrics = self.packet["conflict_evidence"]["real_source_metrics"]
        self.assertEqual(metrics["frame_count"], 4072)
        self.assertEqual(metrics["matched_candidate_boundaries"], 8490)
        self.assertEqual(metrics["not_evaluable_candidates"], 34)
        self.assertEqual(metrics["ambiguous_boundary_sets"], 0)
        self.assertEqual(metrics["resolver_conflicts"], 0)
        self.assertEqual(metrics["conflicted_episodes"], 0)
        self.assertEqual(metrics["peer_owner_collisions"], 0)
        self.assertEqual(metrics["legacy_disagreements"], 3524)
        self.assertEqual(self.packet["conflict_evidence"]["negative_evidence_status"], "PRESERVED_NOT_CONVERTED_TO_NEUTRALITY")

    def test_all_activation_ladder_gates_remain_operator_reserved(self):
        for gate in ("ag0", "ag1", "ag2", "ag3"):
            self.assertEqual(self.packet[gate]["classification"], "OPERATOR_RESERVED")
        self.assertEqual(self.packet["ag0"]["decision_status"], "READY_FOR_OPERATOR_REVIEW")
        self.assertEqual(self.packet["ag3"]["decision_status"], "NOT_EXECUTED")
        self.assertIsNone(self.packet["ag3"]["active_boundary_pack_id"])
        self.assertEqual(self.packet["ag3"]["execution"], "DENIED_UNTIL_EXPLICIT_OPERATOR_AG3_DECISION")

    def test_ag1_and_ag2_do_not_hide_evidence_gaps(self):
        self.assertEqual(
            self.packet["ag1"]["evidence_map"]["real_source_restart_equivalence"],
            "NOT_SEPARATELY_MATERIALIZED_IN_WP6_POSTRUN_PACKET",
        )
        self.assertEqual(self.packet["ag1"]["evidence_map"]["canonical_runtime_byte_stream_equivalence"], "NOT_CLAIMED")
        self.assertEqual(self.packet["ag2"]["evidence_map"]["srfd_comparator"], "UNAVAILABLE_CURRENT_LAWFUL_ROUTE")
        self.assertEqual(self.wp6_comp["srfd_comparator"]["status"], "UNAVAILABLE_CURRENT_LAWFUL_ROUTE")
        self.assertIn("SRFD_CURRENT_COMPARATOR_UNAVAILABLE", self.packet["ag2"]["required_warning"])

    def test_g7_r2_pass_is_packet_completeness_only(self):
        self.assertEqual(self.qa["status"], "PASS")
        self.assertEqual(self.qa["recommendation"], "PASS")
        self.assertEqual(self.qa["gate_scope"], "PACKET_COMPLETENESS_ONLY")
        self.assertEqual(self.qa["authority_delta"], "NONE")
        self.assertEqual(self.qa["blocking_warnings"], [])
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["gate_classification"], "AUTO_RATIFIABLE_PACKET_COMPLETENESS_ONLY")
        self.assertEqual(self.decision["authority_delta"], "NONE")
        self.assertEqual(self.decision["next_gate"], "C2E-AG0")
        self.assertEqual(self.decision["next_gate_classification"], "OPERATOR_RESERVED")
        self.assertEqual(set(self.decision["operator_reserved_decisions_not_taken"]), {"C2E-AG0", "C2E-AG1", "C2E-AG2", "C2E-AG3"})

    def test_state_candidate_is_non_authoritative_and_no_active_c2e(self):
        self.assertEqual(self.state["state_role"], "NON_AUTHORITATIVE_WP7_R2_MERGE_CANDIDATE")
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertEqual(self.state["current_gate"], "C2E-AG0")
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(self.state["authority"]["source_replay_evidence"], "COMPLETE")
        self.assertEqual(self.state["authority"]["active_c2e"], "NONE")
        self.assertEqual(self.state["authority"]["active_boundary_pack"], "NONE")
        self.assertEqual(self.state["authority"]["c2e_activation"], "DENIED_OPERATOR_RESERVED")
        self.assertIn("STOP_AT_C2E_AG0", self.state["next_action"])

    def test_historical_replay_deferred_wp7_and_ag0_defer_are_immutable_context(self):
        self.assertEqual(self.historical_wp7["replay_status"], "DEFERRED")
        self.assertEqual(self.historical_wp7["candidate_boundary_pack"]["authority"], "SHADOW")
        self.assertEqual(self.historical_ag0["decision"], "DEFER")
        self.assertIn("C2E-AG0.OPERATOR.DEFER.20260808T205200+0100", self.state["operator_decision_history"])
        self.assertIn("C2E2-G6-RUN-AUTH.OPERATOR.AUTHORIZE_EXACT_RUN.20260809T145800+0100", self.state["operator_decision_history"])


if __name__ == "__main__":
    unittest.main()
