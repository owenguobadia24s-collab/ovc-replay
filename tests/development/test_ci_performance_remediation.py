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
        readiness_marker = "\n  merge-readiness:\n"
        admission_marker = "\n  final-integration-window-admitted:\n"
        self.assertIn(readiness_marker, self.workflow)
        self.assertIn(admission_marker, self.tests_workflow)
        self.readiness = self.workflow.split(readiness_marker, 1)[1]
        after_admission = self.tests_workflow.split(admission_marker, 1)[1]
        self.admission = after_admission.split("\n  legacy-unittest:\n", 1)[0]

    def test_canonical_suite_contract_is_preserved_after_pyt_wp1(self):
        full_suite = "PYTHONPATH=src python3 -m unittest discover -s tests -v"
        self.assertEqual(self.tests_workflow.count(full_suite), 1)
        self.assertNotIn(full_suite, self.workflow)
        self.assertIn("name: pytest-unittest-parity", self.tests_workflow)
        self.assertIn("name: runner-parity", self.tests_workflow)

    def test_final_integration_window_is_acquired_before_expensive_assurance(self):
        self.assertIn("group: ovc-main-integration-lane-v1", self.readiness)
        self.assertIn("cancel-in-progress: false", self.readiness)
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_ACQUIRED", self.readiness)
        self.assertIn("windowCheckName = 'OVC merge readiness'", self.admission)
        self.assertIn("windowRun?.status === 'in_progress'", self.admission)
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_ADMITTED", self.admission)
        self.assertEqual(self.tests_workflow.count("needs: final-integration-window-admitted"), 3)

    def test_dual_run_required_checks_are_fail_closed(self):
        for check_name in ("'tests'", "'pytest-unittest-parity'", "'runner-parity'"):
            self.assertIn(check_name, self.readiness)
        self.assertIn("required.every", self.readiness)
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_NOT_ADMITTED", self.admission)

    def test_final_readiness_holds_global_lane_through_required_assurance(self):
        self.assertIn("while (Date.now() < deadline)", self.readiness)
        self.assertIn("await sleep(10000)", self.readiness)
        self.assertIn("final_integration_window_hold_ms", self.readiness)
        self.assertIn("'OVC profile assurance'", self.readiness)
        self.assertNotIn("canonical-tests-observed:", self.workflow)

    def test_candidate_is_reconciled_before_required_assurance(self):
        self.assertIn("git merge-base --is-ancestor", self.readiness)
        self.assertIn("OVC_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN", self.readiness)
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.readiness)

    def test_stable_main_fail_closed_checks_are_retained(self):
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.readiness)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.readiness)
        self.assertIn("mainSnapshot !== pr.base.sha", self.readiness)
        self.assertIn("currentMain !== mainSnapshot", self.readiness)
        self.assertIn("finalMain !== mainSnapshot", self.readiness)

    def test_structured_metrics_cover_window_acquisition_and_hold(self):
        self.assertGreaterEqual(self.readiness.count("OVC_CI_METRIC"), 2)
        self.assertIn("schema: 'ovc-ci-metric/v1'", self.readiness)
        self.assertIn("final_integration_window_acquisition_ms", self.readiness)
        self.assertIn("final_integration_window_hold_ms", self.readiness)
        self.assertIn("required_checks: requiredNames", self.readiness)

    def test_github_script_node_target_deprecation_is_remediated(self):
        self.assertEqual(self.workflow.count("actions/github-script@v9"), 2)
        self.assertEqual(self.tests_workflow.count("actions/github-script@v9"), 1)
        self.assertNotIn("actions/github-script@v7", self.workflow)
        self.assertNotIn("actions/github-script@v7", self.tests_workflow)


if __name__ == "__main__":
    unittest.main()
