from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"


class ParallelIntegrationLaneTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")

    def test_only_existing_da2_pr_workflows_are_used(self):
        self.assertIn("pull_request:", self.workflow)
        self.assertIn("pull_request:", self.tests_workflow)
        workflow_dir = ROOT / ".github/workflows"
        listeners = []
        for path in workflow_dir.glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            if "\n  pull_request:" in text or text.startswith("on:\n  pull_request:"):
                listeners.append(path.name)
        self.assertEqual(sorted(listeners), ["ovc-tiered-tests.yml", "tests.yml"])

    def test_per_pr_cancellation_is_preserved(self):
        self.assertIn("group: ovc-pr-${{ github.event.pull_request.number || github.ref }}", self.workflow)
        self.assertIn("group: ovc-tests-${{ github.event.pull_request.number || github.ref }}", self.tests_workflow)
        self.assertIn("cancel-in-progress: true", self.workflow)
        self.assertIn("cancel-in-progress: true", self.tests_workflow)

    def test_final_integration_window_reuses_global_lane_and_is_non_cancelling(self):
        self.assertIn("group: ovc-main-integration-lane-v1", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)
        self.assertEqual(self.workflow.count("group: ovc-main-integration-lane-v1"), 1)

    def test_window_is_acquired_before_expensive_required_checks_are_admitted(self):
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_ACQUIRED", self.workflow)
        self.assertIn("final-integration-window-admitted:", self.tests_workflow)
        self.assertIn("OVC final integration window admitted", self.tests_workflow)
        self.assertIn("windowCheckName = 'OVC merge readiness'", self.tests_workflow)
        self.assertIn("windowRun?.status === 'in_progress'", self.tests_workflow)
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_ADMITTED", self.tests_workflow)
        self.assertEqual(self.tests_workflow.count("needs: final-integration-window-admitted"), 3)

    def test_profile_admission_rechecks_main_before_assurance(self):
        self.assertIn("OVC_PROFILE_BASE_MOVED_BEFORE_ASSURANCE", self.workflow)
        self.assertIn("OVC_PROFILE_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN", self.workflow)
        self.assertGreaterEqual(self.workflow.count("git merge-base --is-ancestor"), 2)

    def test_required_check_admission_rechecks_main_before_assurance(self):
        self.assertIn("OVC_REQUIRED_CHECK_BASE_MOVED_BEFORE_ASSURANCE", self.tests_workflow)
        self.assertIn("OVC_REQUIRED_CHECK_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN", self.tests_workflow)
        self.assertIn("git merge-base --is-ancestor", self.tests_workflow)

    def test_candidate_must_contain_acquired_current_main(self):
        self.assertIn("git merge-base --is-ancestor", self.workflow)
        self.assertIn("OVC_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN", self.workflow)
        self.assertIn("github.event.pull_request.head.sha", self.workflow)

    def test_main_snapshot_must_be_stable_for_entire_window(self):
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.workflow)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.workflow)
        self.assertIn("mainSnapshot !== pr.base.sha", self.workflow)
        self.assertIn("currentMain !== mainSnapshot", self.workflow)
        self.assertIn("finalMain !== mainSnapshot", self.workflow)
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_PASS", self.workflow)

    def test_required_checks_are_observed_inside_held_window(self):
        self.assertIn(
            "const requiredNames = ['tests', 'pytest-unittest-parity', 'runner-parity', 'OVC profile assurance'];",
            self.workflow,
        )
        self.assertIn("final_integration_window_hold_ms", self.workflow)
        self.assertNotIn("canonical-tests-observed:", self.workflow)

    def test_no_duplicate_complete_repository_suite(self):
        full_suite = "python3 -m unittest discover -s tests -v"
        self.assertEqual(self.tests_workflow.count(full_suite), 1)
        self.assertNotIn(full_suite, self.workflow)


if __name__ == "__main__":
    unittest.main()
