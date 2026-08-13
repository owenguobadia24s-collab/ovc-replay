from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "registries/implementation/ci_performance/CIPR_UNITTEST_SHARD_POLICY_v0_1.json"
WORKFLOW = ROOT / ".github/workflows/ci-unittest-shard-shadow.yml"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"
TIERED_WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"
DECISION = ROOT / "docs/releases/ci-performance-remediation-v0-1/cipr-wp4/CIPR_G4_DECISION.json"
STATE = ROOT / "registries/implementation/ci_performance/OVC_CIPR_STATE_v0_2_SHADOW_RUNNING.json"


class CiPerformanceShadowPacketTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
        self.tiered_workflow = TIERED_WORKFLOW.read_text(encoding="utf-8")
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_operator_pass_exactly_authorizes_shadow_option_b(self):
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(
            self.decision["selected_option"],
            "B_DETERMINISTIC_REQUIRED_SHARD_UNION_SHADOW",
        )
        self.assertIn(
            "activate shard output as a substitute for any existing required check",
            self.decision["authority_not_granted"],
        )

    def test_policy_is_four_way_deterministic_and_isolates_known_heavy_paths(self):
        self.assertEqual(self.policy["schema"], "ovc-unittest-shard-policy/v1")
        self.assertEqual(self.policy["shard_count"], 4)
        self.assertEqual(
            self.policy["assignment_algorithm"],
            "LEGACY_DISCOVERY_ORDER_HEAVY_PATH_ISOLATION_THEN_ROUND_ROBIN",
        )
        heavy = self.policy["heavy_path_to_shard"]
        self.assertEqual(len(heavy), 4)
        self.assertEqual(set(heavy.values()), {0, 1, 2, 3})

    def test_shadow_workflow_is_not_a_third_pull_request_listener(self):
        self.assertNotIn("pull_request:", self.workflow)
        self.assertIn("build/ci-performance-shadow-shards", self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("matrix:", self.workflow)
        self.assertIn("shard: [0, 1, 2, 3]", self.workflow)
        self.assertIn("unittest_shard_shadow.py prove", self.workflow)
        self.assertIn("unittest_shard_shadow.py run", self.workflow)
        self.assertNotIn("xdist", self.workflow)

    def test_existing_required_checks_are_preserved_under_final_integration_window(self):
        child_suite = "python3 -m unittest discover -s tests -v"
        self.assertEqual(self.tests_workflow.count(child_suite), 1)
        self.assertIn(
            "tools/ci/ovc_run_with_main_lease.py",
            self.tests_workflow,
        )
        self.assertIn(
            "Complete repository suite under shared main lease",
            self.tests_workflow,
        )
        for name in ("pytest-unittest-parity", "runner-parity"):
            self.assertIn(name, self.tests_workflow)
        for name in ("'tests'", "'pytest-unittest-parity'", "'runner-parity'"):
            self.assertIn(name, self.tiered_workflow)
        self.assertIn("ovc-main-integration-lane-v1", self.tiered_workflow)
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_ACQUIRED", self.tiered_workflow)
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.tiered_workflow)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.tiered_workflow)

    def test_packet_state_preserves_non_activation_boundary(self):
        self.assertIn(self.state["status"], {"RUNNING", "APPROVED"})
        self.assertEqual(
            self.state["authority_delta"],
            "BOUNDED_RUNNER_NEUTRAL_DETERMINISTIC_REQUIRED_SHARD_SHADOW_EVALUATION",
        )
        self.assertFalse(self.state["required_check_substitution_active"])
        self.assertFalse(self.state["runner_cutover_active"])
        self.assertFalse(self.state["scientific_authority_delta"])
        if self.state["status"] == "APPROVED":
            self.assertEqual(
                self.state["decision_record"],
                "docs/releases/ci-performance-remediation-v0-1/cipr-wp4-shadow/CIPR_WP4_SHADOW_DECISION.json",
            )
            self.assertEqual(
                self.state["operator_stop_gate"],
                "CIPR-G5-PYT-G2-CANONICAL-SHARD-CUTOVER",
            )


if __name__ == "__main__":
    unittest.main()
