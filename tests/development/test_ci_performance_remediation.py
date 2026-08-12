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
        observer_marker = "\n  canonical-tests-observed:\n"
        readiness_marker = "\n  merge-readiness:\n"
        self.assertIn(observer_marker, self.workflow)
        self.assertIn(readiness_marker, self.workflow)
        after_observer = self.workflow.split(observer_marker, 1)[1]
        self.observer, self.readiness = after_observer.split(readiness_marker, 1)

    def test_canonical_suite_contract_is_preserved_after_pyt_wp1(self):
        full_suite = "PYTHONPATH=src python3 -m unittest discover -s tests -v"
        self.assertEqual(self.tests_workflow.count(full_suite), 1)
        self.assertNotIn(full_suite, self.workflow)
        self.assertIn("name: pytest-unittest-parity", self.tests_workflow)
        self.assertIn("name: runner-parity", self.tests_workflow)

    def test_observer_waits_outside_global_integration_lane(self):
        self.assertIn("name: OVC canonical tests observed", self.observer)
        self.assertIn("while (Date.now() < deadline)", self.observer)
        self.assertIn("canonical_tests_observation_wait_ms", self.observer)
        self.assertNotIn("ovc-main-integration-lane-v1", self.observer)

    def test_dual_run_required_checks_are_fail_closed(self):
        for check_name in ("'tests'", "'pytest-unittest-parity'", "'runner-parity'"):
            self.assertIn(check_name, self.observer)
            self.assertIn(check_name, self.readiness)
        self.assertIn("required.every", self.observer)
        self.assertIn("required.every", self.readiness)

    def test_final_readiness_enters_global_lane_only_after_observer(self):
        self.assertIn("needs: [profile, canonical-tests-observed]", self.readiness)
        self.assertIn("group: ovc-main-integration-lane-v1", self.readiness)
        self.assertIn("cancel-in-progress: false", self.readiness)
        self.assertEqual(self.workflow.count("group: ovc-main-integration-lane-v1"), 1)

    def test_final_readiness_does_not_poll_inside_global_lane(self):
        self.assertNotIn("while (Date.now() < deadline)", self.readiness)
        self.assertNotIn("await sleep(10000)", self.readiness)
        self.assertIn("integration_lane_evaluation_ms", self.readiness)

    def test_stable_main_fail_closed_checks_are_retained(self):
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.readiness)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.readiness)
        self.assertIn("mainSnapshot !== pr.base.sha", self.readiness)
        self.assertIn("finalMain !== mainSnapshot", self.readiness)

    def test_structured_metrics_are_present_in_both_stages(self):
        self.assertIn("OVC_CI_METRIC", self.observer)
        self.assertIn("OVC_CI_METRIC", self.readiness)
        self.assertIn("schema: 'ovc-ci-metric/v1'", self.observer)
        self.assertIn("schema: 'ovc-ci-metric/v1'", self.readiness)
        self.assertIn("required_checks: requiredNames", self.observer)
        self.assertIn("required_checks: requiredNames", self.readiness)

    def test_github_script_node_target_deprecation_is_remediated(self):
        self.assertEqual(self.workflow.count("actions/github-script@v9"), 2)
        self.assertNotIn("actions/github-script@v7", self.workflow)


if __name__ == "__main__":
    unittest.main()
