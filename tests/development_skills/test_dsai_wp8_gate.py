from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.development.skills.orchestration import (
    build_capability_execution_graph,
    build_continuation_record,
    build_packet_eligibility_record,
    build_packet_graph_snapshot,
    build_run_intent,
    orch0_shadow,
)

ROOT = Path(__file__).resolve().parents[2]
WP8 = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp8"
QUAL = WP8 / "DSAI_WP8_PACKET_EXECUTOR_QUALIFICATION.json"
G8B = WP8 / "DSAI_G8B_PACKET_EXECUTOR_TRUSTED_PROMOTION_DECISION_PACKET.json"
G8A = ROOT / "records/development/skills/DSAI_G8A_AUTO_PASS_ORCH0_SHADOW_20260812T140300+0100.json"
CANDIDATES = ROOT / "registries/development/skills/orchestration_candidates_v0_1.json"
TRUSTED = ROOT / "registries/development/skills/trusted_promotions_v0_1.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_18.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"
BASELINE = "a69bf6c1c7a2febcaf5db71eddbf1ac43083ea3a"
ENVIRONMENT = "windows-local-python311"
PACKET_EXECUTOR_RELEASE = "OVC-SKILL-030@0.1.0+sha256:62809d0f5f1d4298fa916766912d4bec7b5a8bf7712f7382d448137f6f12f130"


class DSAIWP8GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qual = json.loads(QUAL.read_text(encoding="utf-8"))
        cls.g8a = json.loads(G8A.read_text(encoding="utf-8"))
        cls.g8b = json.loads(G8B.read_text(encoding="utf-8"))
        cls.candidate = json.loads(CANDIDATES.read_text(encoding="utf-8"))["entries"][0]
        cls.trusted = json.loads(TRUSTED.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))
        cls.pointer = json.loads(POINTER.read_text(encoding="utf-8"))

    def test_packet_executor_is_qualified_but_not_trusted(self):
        self.assertEqual(self.candidate["skill_id"], "OVC-SKILL-030")
        self.assertEqual(self.candidate["release_id"], PACKET_EXECUTOR_RELEASE)
        self.assertEqual(self.candidate["maturity"], "QUALIFIED")
        self.assertEqual(self.candidate["availability"], "SHADOW_ONLY")
        self.assertEqual(self.candidate["write_permission"], "DENY")
        self.assertEqual(self.candidate["merge_permission"], "DENY")
        trusted_releases = {row["release_id"] for row in self.trusted["entries"]}
        self.assertNotIn(PACKET_EXECUTOR_RELEASE, trusted_releases)
        self.assertEqual(self.trusted["entry_count"], 8)

    def test_e1_through_e6_are_closed_for_operator_review(self):
        layers = self.qual["evaluation_layers"]
        self.assertEqual(set(layers), {"E1", "E2", "E3", "E4", "E5", "E6"})
        for name, row in layers.items():
            with self.subTest(layer=name):
                self.assertTrue(row["status"].startswith("PASS"))
        self.assertFalse(self.qual["skill"]["trusted_promoted"])
        self.assertEqual(self.qual["composition"]["status"], "QUALIFIED_FOR_G8B_OPERATOR_REVIEW")
        self.assertEqual(self.qual["limitations"]["write_authority"], "NONE")
        self.assertEqual(self.qual["limitations"]["merge_authority"], "NONE")
        self.assertFalse(self.qual["evaluation_layers"]["E4"]["independent_human_review_claimed"])

    def test_g8a_is_auto_pass_with_zero_authority_delta(self):
        self.assertEqual(self.g8a["gate_id"], "DSAI-G8A")
        self.assertEqual(self.g8a["gate_classification"], "AUTO_RATIFIABLE")
        self.assertEqual(self.g8a["decision"], "PASS")
        self.assertEqual(self.g8a["decision_authority"], "DELEGATED_AUTO_RATIFIABLE")
        self.assertEqual(self.g8a["authority_effect"], "NONE")
        self.assertFalse(self.g8a["non_effects"]["packet_executor_trusted"])
        self.assertEqual(self.g8a["non_effects"]["orch_1"], "INACTIVE")
        self.assertEqual(self.g8a["next_gate"], "DSAI-G8B")
        self.assertTrue(self.g8a["mandatory_stop_after_packet_preparation"])

    def test_g8b_packet_is_exact_tuple_and_pending_operator(self):
        self.assertEqual(self.g8b["gate_id"], "DSAI-G8B")
        self.assertEqual(self.g8b["gate_classification"], "OPERATOR_REQUIRED")
        self.assertEqual(self.g8b["decision"], "PENDING_OPERATOR")
        candidate = self.g8b["promotion_candidate"]
        self.assertEqual(candidate["release_id"], PACKET_EXECUTOR_RELEASE)
        self.assertEqual(candidate["capability_id"], "PACKET_EXECUTION")
        self.assertEqual(candidate["environment_id"], ENVIRONMENT)
        self.assertEqual(candidate["current_maturity"], "QUALIFIED")
        self.assertEqual(candidate["requested_maturity"], "TRUSTED")
        effects = self.g8b["effects_if_operator_passes"]
        self.assertEqual(effects["write_authority"], "NONE")
        self.assertEqual(effects["merge_authority"], "NONE")
        self.assertEqual(effects["automatic_merge"], "DENIED")
        self.assertEqual(effects["orch_1"], "INACTIVE_PENDING_SEPARATE_DSAI_G8C")

    def test_programme_pointer_stops_at_g8b(self):
        self.assertEqual(self.pointer["current_state"], "OVC_DSAI_STATE_v0_18.json")
        self.assertEqual(self.pointer["status"], "READY_OPERATOR_G8B")
        self.assertEqual(self.pointer["next_packet"], "DSAI-WP8")
        self.assertEqual(self.state["current_gate"], "DSAI-G8B")
        self.assertEqual(self.state["packet_updates"]["DSAI-WP8"]["g8b_decision"], "PENDING_OPERATOR")
        self.assertEqual(self.state["packet_updates"]["DSAI-WP8"]["g8c_decision"], "NOT_REACHED")
        self.assertTrue(self.state["mandatory_stop"]["active"])
        self.assertFalse(self.state["packet_executor"]["trusted"])
        self.assertEqual(self.state["authority"]["orch_1"], "INACTIVE_PENDING_DSAI_G8C")
        self.assertEqual(self.state["authority"]["orch_2"], "INACTIVE")

    def test_historical_g7_shadow_replay_stops_before_reserved_promotion(self):
        control_resolution = {
            "PACKET_PREFLIGHT": "OVC-SKILL-001@0.1.0+sha256:6609c3cffb8be1b81da4870e6d6c752057c7deed4e35f7d5eabaaca5e0f440f7",
            "AUTHORITY_RESOLUTION": "OVC-SKILL-002@0.1.0+sha256:6d56ba0c93e467a6c07c359eb8167d3fc6fe70ec43b788038ba1d03059fb55f9",
            "GATE_EVALUATION": "OVC-SKILL-024@0.1.0+sha256:be6b62b8a85426563fcb389a944ae1764473bf550477b8492a98b7dab755a831",
        }
        graph = build_packet_graph_snapshot(
            programme_id="OVC-DSAI-v0.1",
            baseline_main=BASELINE,
            packets=[{
                "packet_id": "DSAI-WP7",
                "prerequisites": ["DSAI-G6"],
                "required_capabilities": list(control_resolution),
                "gate_class": "OPERATOR_REQUIRED",
                "authority_delta": "TRUSTED_PROMOTION",
            }],
        )
        eligibility = build_packet_eligibility_record(
            packet_id="DSAI-WP7", packet_graph=graph, completed_prerequisites=["DSAI-G6"]
        )
        cap_graph = build_capability_execution_graph(
            packet_id="DSAI-WP7", required_capabilities=list(control_resolution), resolution=control_resolution
        )
        intent = build_run_intent(
            command="RUN", scope={"programme_id": "OVC-DSAI-v0.1", "packet_ids": ["DSAI-WP7"]}
        )
        result = orch0_shadow(
            run_intent=intent,
            programme_state={"programme_id": "OVC-DSAI-v0.1", "next_packet": "DSAI-WP7"},
            packet_graph=graph,
            packet_eligibility=eligibility,
            capability_graph=cap_graph,
            baseline_main=BASELINE,
            current_main=BASELINE,
            environment_id=ENVIRONMENT,
            next_gate_class="OPERATOR_REQUIRED",
            next_authority_delta="TRUSTED_PROMOTION",
        )
        self.assertEqual(result["status"], "WOULD_EXECUTE_TO_OPERATOR_GATE")
        self.assertEqual(result["writes_performed"], [])
        self.assertFalse(result["merge_performed"])
        self.assertIn("OPERATOR_REQUIRED_RESERVED_DELTA", result["stop_record"]["reason_codes"])

    def test_restart_reconciliation_fails_closed_after_main_churn(self):
        continuation = build_continuation_record(
            programme_id="OVC-DSAI-v0.1",
            run_id="CRASHED.WP8",
            current_packet="DSAI-WP8",
            next_action="RESUME_DSAI_WP8",
            baseline_main=BASELINE,
            evidence_refs=["registries/implementation/dsai/OVC_DSAI_STATE_v0_17.json"],
        )
        graph = build_packet_graph_snapshot(
            programme_id="OVC-DSAI-v0.1",
            baseline_main=BASELINE,
            packets=[{"packet_id":"DSAI-WP8","prerequisites":["DSAI-G7"],"required_capabilities":["PACKET_PREFLIGHT"]}],
        )
        eligibility = build_packet_eligibility_record(
            packet_id="DSAI-WP8", packet_graph=graph, completed_prerequisites=["DSAI-G7"]
        )
        cap_graph = build_capability_execution_graph(
            packet_id="DSAI-WP8",
            required_capabilities=["PACKET_PREFLIGHT"],
            resolution={"PACKET_PREFLIGHT":"OVC-SKILL-001@0.1.0+sha256:6609c3cffb8be1b81da4870e6d6c752057c7deed4e35f7d5eabaaca5e0f440f7"},
        )
        intent = build_run_intent(
            command="CONTINUE",
            scope={"programme_id":"OVC-DSAI-v0.1","packet_ids":["DSAI-WP8"]},
            continuation_record_id=continuation["record_id"],
        )
        result = orch0_shadow(
            run_intent=intent,
            programme_state={"programme_id":"OVC-DSAI-v0.1","next_packet":"DSAI-WP8"},
            packet_graph=graph,
            packet_eligibility=eligibility,
            capability_graph=cap_graph,
            baseline_main=BASELINE,
            current_main="new-main-after-crash",
            environment_id=ENVIRONMENT,
            continuation_record=continuation,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("MAIN_HEAD_CHURN", result["continuation_reconstruction"]["reason_codes"])


if __name__ == "__main__":
    unittest.main()
