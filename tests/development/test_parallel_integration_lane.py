from __future__ import annotations
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"
LEASE_RUNNER = ROOT / "tools/ci/ovc_run_with_main_lease.py"
ADMISSION_TOOL = ROOT / "tools/ci/prvitr_live_admission.py"
CONSOLE_PACKAGE = ROOT / "tests/research_console_vnext/__init__.py"


class ParallelIntegrationLaneTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
        self.lease_runner = LEASE_RUNNER.read_text(encoding="utf-8")
        self.admission = ADMISSION_TOOL.read_text(encoding="utf-8")

    def test_only_existing_da2_pr_workflows_are_used(self):
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

    def test_single_global_integration_lane_remains(self):
        self.assertEqual(self.workflow.count("group: ovc-main-integration-lane-v1"), 1)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_base_independent_required_work_is_outside_lease(self):
        self.assertNotIn("final-integration-window-admitted", self.tests_workflow)
        self.assertNotIn("OVC_LEASE_REQUIRED", self.tests_workflow)
        self.assertNotIn("tools/ci/ovc_run_with_main_lease.py", self.tests_workflow)
        self.assertIn("BASE_INDEPENDENT assurance", self.tests_workflow)
        self.assertIn("BASE_INDEPENDENT assurance", self.workflow)

    def test_pip_assurance_identity_precedes_placement_routing(self):
        assurance = "python3 tools/ci/vit_assurance_preflight.py"
        placement = "python3 tools/ci/vit_routing_preflight.py"
        self.assertIn(assurance, self.tests_workflow)
        self.assertIn(placement, self.tests_workflow)
        self.assertLess(self.tests_workflow.index(assurance), self.tests_workflow.index(placement))

    def test_ready_admission_binds_exact_assurance_generation(self):
        self.assertIn("SIQ READY admission", self.workflow)
        self.assertIn("prvitr_live_admission.py ready", self.workflow)
        self.assertIn("assurance_generation_id", self.workflow)
        self.assertIn("OVC_SIQ_READY_ADMITTED", self.admission)
        self.assertIn("IntegrationAssuranceGeneration", self.admission)

    def test_base_sensitive_lease_is_late_and_single(self):
        readiness = self.workflow.split("\n  merge-readiness:\n", 1)[1]
        self.assertIn("needs: [profile, siq-ready-admission]", readiness)
        self.assertIn("group: ovc-main-integration-lane-v1", readiness)
        self.assertIn("prvitr_live_admission.py acquire", readiness)
        self.assertIn("prvitr_live_admission.py finalize", readiness)
        self.assertIn("IntegrationAdmissionReceipt", self.admission)

    def test_stable_main_guards_remain_effective_and_local_git_is_normative(self):
        self.assertIn("OVC_REQUIRED_ASSURANCE_LEASE_INVALIDATED", self.lease_runner)
        self.assertIn("OVC_RECONCILE_REQUIRED", self.admission)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.admission)
        self.assertIn("git merge-base --is-ancestor", self.workflow)
        self.assertIn('["git", "merge-base", "--is-ancestor"', self.admission)
        self.assertNotIn("compareCommits", self.workflow)
        self.assertNotIn("compareCommits", self.admission)

    def test_vit_predecessor_disposition_advances_successor(self):
        for marker in [
            "final_integration_predecessor_lease_wait_ms",
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_HELD",
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_MERGED",
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_RELEASED_UNMERGED",
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_INVALIDATED",
        ]:
            self.assertIn(marker, self.admission)

    def test_predecessor_is_vit_placement_not_pr_number_or_ready_job_order(self):
        self.assertIn("resolve_vit_train_predecessor", self.admission)
        self.assertIn("main_tree == expected_tree", self.admission)
        self.assertIn("OVC_FINAL_INTEGRATION_NO_VIT_PLACEMENT_PREDECESSOR", self.admission)
        self.assertNotIn("if number>=pr_number", self.admission.replace(" ", ""))
        self.assertNotIn("_exact_merge_job_pass", self.admission)
        self.assertNotIn("sorted(_open_pulls", self.admission)
        self.assertNotIn("checks.listForRef", self.workflow)
        self.assertNotIn("latestNamedRun", self.workflow)

    def test_terminal_disposition_does_not_expand_merge_authority(self):
        self.assertIn("permissions:\n  contents: read\n  checks: read\n  pull-requests: read", self.workflow)
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("pull-requests: write", self.workflow)
        self.assertNotIn("github.rest.pulls.merge", self.workflow)
        self.assertNotIn("enablePullRequestAutoMerge", self.workflow)

    def test_research_console_surface_is_in_current_pytest_suite(self):
        self.assertTrue(CONSOLE_PACKAGE.exists())
        self.assertIn('python3 -m pip install -e ".[test]" -r requirements-console-vnext.txt', self.tests_workflow)
        exact = "PYTHONPATH=src:. python3 -m pytest tests/research_console_vnext -q --tb=short"
        self.assertEqual(self.tests_workflow.count(exact), 1)
        full_suite = "PYTHONPATH=src:. python3 -m pytest tests -q --tb=short"
        self.assertEqual(self.tests_workflow.count(full_suite), 1)
        self.assertNotIn(full_suite, self.workflow)
        self.assertEqual(self.tests_workflow.count("tools/ci/ovc_run_with_main_lease.py"), 0)


if __name__ == "__main__":
    unittest.main()
