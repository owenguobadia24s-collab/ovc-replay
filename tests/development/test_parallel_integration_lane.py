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
        self.assertIn("cancel-in-progress: true", self.workflow)

    def test_merge_readiness_has_one_global_non_cancelling_lane(self):
        self.assertIn("group: ovc-main-integration-lane-v1", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_main_snapshot_must_be_stable(self):
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.workflow)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.workflow)
        self.assertIn("mainSnapshot !== pr.base.sha", self.workflow)
        self.assertIn("finalMain !== mainSnapshot", self.workflow)

    def test_no_duplicate_complete_repository_suite(self):
        full_suite = "python3 -m unittest discover -s tests -v"
        self.assertEqual(self.tests_workflow.count(full_suite), 1)
        self.assertNotIn(full_suite, self.workflow)
        self.assertIn("const requiredNames =", self.workflow)
        for check_name in ("'tests'", "'pytest-unittest-parity'", "'runner-parity'"):
            self.assertIn(check_name, self.workflow)


if __name__ == "__main__":
    unittest.main()
