from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "docs/releases/ci-performance-remediation-v0-1/cipr-wp4/CIPR_G4_GATE_PACKET.json"
QA = ROOT / "docs/releases/ci-performance-remediation-v0-1/cipr-wp4/CIPR_WP4_QA_PACKET.json"
HEAVY = ROOT / "docs/releases/ci-performance-remediation-v0-1/cipr-wp4/CIPR_WP4_HEAVY_TEST_INVENTORY.json"
PYT = ROOT / "docs/releases/ci-performance-remediation-v0-1/cipr-wp4/CIPR_WP4_PYT_COMPATIBILITY_ASSESSMENT.json"
STATE = ROOT / "registries/implementation/ci_performance/OVC_CIPR_STATE_v0_1.json"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"
TIERED_WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CiPerformanceG4GateTests(unittest.TestCase):
    def setUp(self):
        self.gate = load(GATE)
        self.qa = load(QA)
        self.heavy = load(HEAVY)
        self.pyt = load(PYT)
        self.state = load(STATE)
        self.tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
        self.tiered_workflow = TIERED_WORKFLOW.read_text(encoding="utf-8")

    def test_gate_is_operator_required_and_recommends_bounded_shadow_sharding(self):
        self.assertEqual(self.gate["gate_id"], "CIPR-G4-SUITE-TOPOLOGY")
        self.assertTrue(self.gate["qa"]["operator_decision_required"])
        self.assertEqual(self.gate["recommended_decision"], "PASS")
        self.assertEqual(
            self.gate["recommended_option"],
            "B_DETERMINISTIC_REQUIRED_SHARD_UNION_SHADOW",
        )
        self.assertIn("DEFER", self.gate["decision_options"])
        self.assertIn("BLOCK", self.gate["decision_options"])

    def test_no_implementation_candidate_exists_in_gate_packet(self):
        self.assertEqual(
            self.gate["candidate_commit"],
            "NOT_CREATED_OPERATOR_APPROVAL_REQUIRED",
        )
        self.assertEqual(
            self.qa["implementation_candidate_commit"],
            "NOT_CREATED_OPERATOR_APPROVAL_REQUIRED",
        )
        proposed = self.gate["proposed_authority_delta"]
        self.assertIn(
            "activate the shard candidate as a substitute for any existing required check",
            proposed["not_authorised_by_this_pass"],
        )

    def test_current_required_python_assurance_is_preserved(self):
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
        for required in ("'tests'", "'pytest-unittest-parity'", "'runner-parity'"):
            self.assertIn(required, self.tiered_workflow)
        self.assertEqual(
            self.pyt["current_required_exact_head_checks"],
            ["tests", "pytest-unittest-parity", "runner-parity"],
        )
        self.assertEqual(
            self.pyt["python_runner_programme"]["legacy_unittest_ci_command"],
            "PRESERVE_UNTIL_PYT_G2",
        )

    def test_gate_prohibits_test_weakening_and_runner_cutover(self):
        denied = set(self.gate["proposed_authority_delta"]["not_authorised_by_this_pass"])
        self.assertIn("remove, skip, demote or replace standalone unittest", denied)
        self.assertIn("enable pytest-xdist or any unordered process-parallel runner", denied)
        self.assertIn(
            "change benchmark freshness, scientific evidence semantics or heavy-test assertions",
            denied,
        )
        self.assertEqual(
            self.pyt["compatibility_result"],
            "PASS_IF_RUNNER_NEUTRAL_SHADOW_SHARDING_ONLY",
        )

    def test_performance_evidence_distinguishes_fresh_and_historical_measurements(self):
        current = self.heavy["current_main_aggregate"]
        self.assertEqual(current["legacy_unittest"]["complete_repository_suite_step_seconds"], 140)
        self.assertEqual(current["pytest_legacy_parity"]["execute_exact_legacy_surface_seconds"], 153)
        self.assertEqual(current["runner_parity"]["collection_parity_seconds"], 4)
        self.assertEqual(self.heavy["audit_baseline_summary"]["historical_heavy_sum_seconds"], 98.6)
        self.assertIn("not been re-benchmarked individually", self.heavy["audit_baseline_summary"]["freshness_warning"])

    def test_state_preserves_no_topology_activation_across_gate_transition(self):
        self.assertEqual(self.state["packet_id"], "CIPR-WP4")
        self.assertFalse(self.state["topology_change_active"])
        if self.state["status"] == "GATE_READY":
            self.assertEqual(self.state["operator_stop_gate"], "CIPR-G4-SUITE-TOPOLOGY")
            self.assertEqual(self.state["authority_required"], "OPERATOR_REQUIRED")
            self.assertIsNone(self.state["decision_record"])
        elif self.state["status"] == "APPROVED":
            self.assertIsNone(self.state["operator_stop_gate"])
            self.assertEqual(self.state["authority_required"], "SATISFIED_OPERATOR_PASS")
            self.assertEqual(
                self.state["decision_record"],
                "docs/releases/ci-performance-remediation-v0-1/cipr-wp4/CIPR_G4_DECISION.json",
            )
            self.assertEqual(
                self.state["authority_delta"],
                "BOUNDED_RUNNER_NEUTRAL_DETERMINISTIC_REQUIRED_SHARD_SHADOW_EVALUATION",
            )
        else:
            self.fail(f"unexpected CIPR-G4 state: {self.state['status']}")


if __name__ == "__main__":
    unittest.main()
