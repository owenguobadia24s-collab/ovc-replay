from __future__ import annotations
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"

class CiPerformanceRemediationTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
        self.profile = self.workflow.split("\n  profile:\n", 1)[1].split("\n  legacy-required-context:\n", 1)[0]
        self.ready = self.workflow.split("\n  siq-ready-admission:\n", 1)[1].split("\n  merge-readiness:\n", 1)[0]
        self.readiness = self.workflow.split("\n  merge-readiness:\n", 1)[1]

    def test_canonical_suite_contract_is_preserved_after_pyt_wp1(self):
        child_suite = "python3 -m unittest discover -s tests -v"
        self.assertEqual(self.tests_workflow.count(child_suite), 1)
        self.assertNotIn(child_suite, self.workflow)
        self.assertIn("name: pytest-unittest-parity", self.tests_workflow)
        self.assertIn("name: runner-parity", self.tests_workflow)

    def test_expensive_assurance_completes_before_final_integration_lease(self):
        self.assertIn("BASE_INDEPENDENT assurance", self.tests_workflow)
        self.assertNotIn("final-integration-window-admitted", self.tests_workflow)
        self.assertIn("OVC_SIQ_READY_ADMITTED", self.ready)
        self.assertIn("Acquire SIQ BASE_SENSITIVE final-integration lease on current main", self.readiness)
        self.assertLess(self.workflow.index("OVC_SIQ_READY_ADMITTED"), self.workflow.index("OVC_SIQ_BASE_SENSITIVE_LEASE_ACQUIRED"))

    def test_ready_admission_rechecks_current_main_and_ancestry(self):
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.ready)
        self.assertIn("git merge-base --is-ancestor", self.ready)
        self.assertIn("OVC_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN", self.ready)

    def test_required_checks_are_fail_closed_before_ready(self):
        for check_name in ("'tests'", "'pytest-unittest-parity'", "'runner-parity'", "'OVC profile assurance'"):
            self.assertIn(check_name, self.ready)
        self.assertIn("SIQ_BASE_INDEPENDENT_ASSURANCE_FAILED", self.ready)

    def test_final_readiness_holds_lane_only_for_exact_final_assurance(self):
        self.assertIn("group: ovc-main-integration-lane-v1", self.readiness)
        self.assertIn("cancel-in-progress: false", self.readiness)
        self.assertIn("Run mandatory SIQ/PDC exact-final assurance inside lease", self.readiness)
        self.assertIn("OVC_SIQ_BASE_SENSITIVE_LEASE_RELEASED", self.readiness)
        self.assertEqual(self.readiness.count("tools/ci/ovc_run_with_main_lease.py"), 1)

    def test_candidate_is_reconciled_before_exact_final_assurance(self):
        self.assertIn("git merge-base --is-ancestor", self.readiness)
        self.assertIn("OVC_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN", self.readiness)
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.readiness)

    def test_stable_main_fail_closed_checks_are_retained(self):
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.readiness)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.readiness)
        self.assertIn("finalMain !== mainSnapshot", self.readiness)

    def test_structured_metrics_cover_late_acquisition_and_hold(self):
        self.assertIn("OVC_CI_METRIC", self.readiness)
        self.assertIn("final_integration_window_acquisition_ms", self.readiness)
        self.assertIn("final_integration_window_hold_ms", self.readiness)
        self.assertIn("ACQUIRED_BASE_SENSITIVE_ONLY", self.readiness)

    def test_github_script_node_target_is_current(self):
        self.assertNotIn("actions/github-script@v7", self.workflow)
        self.assertNotIn("actions/github-script@v7", self.tests_workflow)
        self.assertIn("actions/github-script@v9", self.workflow)

if __name__ == "__main__":
    unittest.main()
