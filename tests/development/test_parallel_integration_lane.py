from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"
LEASE_RUNNER = ROOT / "tools/ci/ovc_run_with_main_lease.py"
CONSOLE_PACKAGE = ROOT / "tests/research_console_vnext/__init__.py"


class ParallelIntegrationLaneTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
        self.lease_runner = LEASE_RUNNER.read_text(encoding="utf-8")

    def test_only_existing_da2_pr_workflows_are_used(self):
        self.assertIn("pull_request:", self.workflow)
        self.assertIn("pull_request:", self.tests_workflow)
        workflow_dir = ROOT / ".github/workflows"
        listeners = []
        for path in workflow_dir.glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            if "\n  pull_request:" in text or text.startswith("on:\n  pull_request:"):
                listeners.append(path.name)
        self.assertEqual(
            sorted(listeners),
            ["ovc-tiered-tests.yml", "tests.yml"],
        )

    def test_per_pr_cancellation_is_preserved(self):
        self.assertIn(
            "group: ovc-pr-${{ github.event.pull_request.number || github.ref }}",
            self.workflow,
        )
        self.assertIn(
            "group: ovc-tests-${{ github.event.pull_request.number || github.ref }}",
            self.tests_workflow,
        )
        self.assertIn("cancel-in-progress: true", self.workflow)
        self.assertIn("cancel-in-progress: true", self.tests_workflow)

    def test_final_integration_window_reuses_global_lane_and_is_non_cancelling(self):
        self.assertIn("group: ovc-main-integration-lane-v1", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)
        self.assertEqual(
            self.workflow.count("group: ovc-main-integration-lane-v1"),
            1,
        )

    def test_peer_workflows_wait_for_successful_acquisition_step_not_check_start(self):
        marker = "Acquire serialized final-integration window on current main"
        for text in (self.workflow, self.tests_workflow):
            self.assertIn("github.rest.actions.getJobForWorkflowRun", text)
            self.assertIn(marker, text)
            self.assertIn(
                "acquireStep?.status === 'completed'",
                text,
            )
            self.assertIn(
                "acquireStep.conclusion === 'success'",
                text,
            )
            self.assertNotIn(
                "windowRun?.status === 'in_progress'",
                text,
            )
        self.assertIn("OVC_SHARED_FINAL_INTEGRATION_LEASE_ADMITTED", self.tests_workflow)
        self.assertIn(
            "OVC_PROFILE_SHARED_FINAL_INTEGRATION_LEASE_ADMITTED",
            self.workflow,
        )

    def test_shared_lease_identity_is_propagated_to_required_fanout(self):
        self.assertIn(
            "base_sha: ${{ steps.lease.outputs.base_sha }}",
            self.tests_workflow,
        )
        self.assertIn(
            "head_sha: ${{ steps.lease.outputs.head_sha }}",
            self.tests_workflow,
       )
        self.assertEqual(
            self.tests_workflow.count(
                "OVC_LEASE_BASE_SHA: ${{ needs.final-integration-window-admitted.outputs.base_sha }}"
            ),
            4,
        )
        self.assertEqual(
            self.tests_workflow.count(
                "OVC_LEASE_HEAD_SHA: ${{ needs.final-integration-window-admitted.outputs.head_sha }}"
            ),
            4,
        )
        self.assertGreaterEqual(
            self.workflow.count(
                "OVC_LEASE_BASE_SHA: ${{ steps.lease.outputs.base_sha }}"
            ),
            3,
        )

    def test_required_work_is_terminated_when_main_invalidates_the_lease(self):
        self.assertIn("OVC_REQUIRED_ASSURANCE_LEASE_INVALIDATED", self.lease_runner)
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.lease_runner)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.lease_runner)
        self.assertIn("_terminate_process_group(process)", self.lease_runner)
        self.assertIn("MAX_CONSECUTIVE_OBSERVATION_FAILURES = 3", self.lease_runner)
        self.assertEqual(
            self.tests_workflow.count("tools/ci/ovc_run_with_main_lease.py"),
            4,
       )
        self.assertGreaterEqual(
            self.workflow.count("tools/ci/ovc_run_with_main_lease.py"),
            4,
       )

    def test_profile_admission_rechecks_main_before_assurance(self):
        self.assertIn("OVC_PROFILE_BASE_MOVED_BEFORE_ASSURANCE", self.workflow)
        self.assertIn(
            "OVC_PROFILE_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN",
            self.workflow,
        )
        self.assertGreaterEqual(
            self.workflow.count("git merge-base --is-ancestor"),
            2,
        )

    def test_required_check_admission_rechecks_main_before_assurance(self):
        self.assertIn(
            "OVC_REQUIRED_CHECK_BASE_MOVED_BEFORE_ASSURANCE",
            self.tests_workflow,
        )
        self.assertIn(
            "OVC_REQUIRED_CHECK_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN",
            self.tests_workflow,
        )
        self.assertIn("git merge-base --is-ancestor", self.tests_workflow)

    def test_candidate_must_contain_acquired_current_main(self):
        self.assertIn("git merge-base --is-ancestor", self.workflow)
        self.assertIn(
            "OVC_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN",
            self.workflow,
        )
        self.assertIn("github.event.pull_request.head.sha", self.workflow)

    def test_main_snapshot_must_be_stable_for_entire_window(self):
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS", self.workflow)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.workflow)
        self.assertIn("mainSnapshot !== pr.base.sha", self.workflow)
        self.assertIn("currentMain !== mainSnapshot", self.workflow)
        self.assertIn("finalMain !== mainSnapshot", self.workflow)
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_PASS", self.workflow)

    def test_required_checks_are_observed_inside_held_window(self):
        for name in [
            "'tests'",
            "'pytest-unittest-parity'",
            "'runner-parity'",
            "'OVC profile assurance'",
        ]:
            self.assertIn(name, self.workflow)
        self.assertIn("final_integration_window_hold_ms", self.workflow)
        self.assertNotIn("canonical-tests-observed:", self.workflow)

    def test_green_predecessor_holds_next_admission_until_terminal_disposition(self):
        self.assertIn(
            "final_integration_predecessor_lease_wait_ms",
            self.workflow,
        )
        self.assertIn(
            "leaseRun?.status === 'completed'",
            self.workflow,
        )
        self.assertIn(
            "leaseRun.conclusion === 'success'",
            self.workflow,
        )
        self.assertIn("github.rest.repos.compareCommits", self.workflow)
        self.assertIn(
            "OVC_FINAL_INTEGRATION_PREDECESSOR_LEASE_HELD",
            self.workflow,
       )
        self.assertIn("terminal.data.merged_at", self.workflow)
        self.assertIn("terminal.data.state === 'closed'", self.workflow)
        self.assertIn(
            "OVC_FINAL_INTEGRATION_PREDECESSOR_MERGED",
            self.workflow,
       )
        self.assertIn(
            "OVC_FINAL_INTEGRATION_PREDECESSOR_RELEASED",
            self.workflow,
       )
        self.assertIn(
            "OVC_FINAL_INTEGRATION_PREDECESSOR_INVALIDATED",
            self.workflow,
       )
        self.assertIn(
            "OVC_FINAL_INTEGRATION_PREDECESSOR_TERMINAL_TIMEOUT",
            self.workflow,
        )
        self.assertLess(
            self.workflow.index("OVC_FINAL_INTEGRATION_PREDECESSOR_LEASE_HELD"),
            self.workflow.index("OVC_FINAL_INTEGRATION_WINDOW_ACQUIRED"),
        )

    def test_terminal_disposition_lease_does_not_expand_merge_authority(self):
        self.assertIn(
            "permissions:\n  contents: read\n  checks: read\n  pull-requests: read",
            self.workflow,
       )
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("pull-requests: write", self.workflow)
        self.assertNotIn("github.rest.pulls.merge", self.workflow)
        self.assertNotIn("nablePullRequestAutoMerge", self.workflow)

    def test_research_console_surface_is_in_canonical_discovery_and_exact_required_check(self):
        self.assertTrue(CONSOLE_PACKAGE.exists())
        self.assertIn(
            'python3 -m pip install -e ".[test]" -r requirements-console-vnext.txt',
            self.tests_workflow,
        )
        exact = "python3 -m pytest tests/research_console_vnext -q --tb=short"
        self.assertEqual(self.tests_workflow.count(exact), 1)
        full_suite = "python3 -m pytest tests -q --tb=short"
        self.assertEqual(self.tests_workflow.count(full_suite), 1)
        self.assertNotIn(full_suite, self.workflow)
        self.assertEqual(
            self.tests_workflow.count("tools/ci/ovc_run_with_main_lease.py"),
            4,
        )


if __name__ == "__main__":
    unittest.main()
