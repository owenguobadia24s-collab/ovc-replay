from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"
LEASE_RUNNER = ROOT / "tools/ci/ovc_run_with_main_lease.py"
ADMISSION_TOOL = ROOT / "tools/ci/prvitr_live_admission.py"
ROUTING_PREFLIGHT = ROOT / "tools/ci/vit_routing_preflight.py"
CONSOLE_PACKAGE = ROOT / "tests/research_console_vnext/__init__.py"


class ParallelIntegrationLaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
        cls.lease_runner = LEASE_RUNNER.read_text(encoding="utf-8")
        cls.admission = ADMISSION_TOOL.read_text(encoding="utf-8")
        cls.routing = ROUTING_PREFLIGHT.read_text(encoding="utf-8")

    def test_only_existing_da2_pr_workflows_are_used(self) -> None:
        workflow_dir = ROOT / ".github/workflows"
        listeners = []
        for path in workflow_dir.glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            if "\n  pull_request:" in text or text.startswith("on:\n  pull_request:"):
                listeners.append(path.name)
        self.assertEqual(sorted(listeners), ["ovc-tiered-tests.yml", "tests.yml"])

    def test_per_pr_cancellation_is_preserved(self) -> None:
        self.assertIn(
            "group: ovc-pr-${{ github.event.pull_request.number || github.ref }}-${{ github.event.pull_request.head.sha || github.sha }}",
            self.workflow,
        )
        self.assertIn(
            "group: ovc-tests-${{ github.event.pull_request.number || github.ref }}",
            self.tests_workflow,
        )
        self.assertIn("cancel-in-progress: true", self.workflow)
        self.assertIn("cancel-in-progress: true", self.tests_workflow)

    def test_single_global_physical_lane_remains(self) -> None:
        self.assertEqual(self.workflow.count("group: ovc-main-integration-lane-v1"), 1)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_base_independent_required_work_is_outside_lease(self) -> None:
        self.assertNotIn("OVC_LEASE_REQUIRED", self.tests_workflow)
        self.assertNotIn("tools/ci/ovc_run_with_main_lease.py", self.tests_workflow)
        self.assertIn("BASE_INDEPENDENT assurance", self.tests_workflow)
        self.assertIn("BASE_INDEPENDENT assurance", self.workflow)

    def test_pip_assurance_identity_precedes_frontier_routing(self) -> None:
        assurance = "python3 tools/ci/vit_assurance_preflight.py"
        placement = "python3 tools/ci/vit_routing_preflight.py"
        self.assertIn(assurance, self.tests_workflow)
        self.assertIn(placement, self.tests_workflow)
        self.assertLess(self.tests_workflow.index(assurance), self.tests_workflow.index(placement))

    def test_same_pr_can_receive_new_frontier_generation(self) -> None:
        self.assertIn("build_frontier_lineage", self.routing)
        self.assertIn("source_head_is_provenance_only", self.workflow)
        self.assertIn("same_pr=true", self.routing)
        self.assertIn("frontier_generation_id", self.workflow)
        self.assertIn("frontier_lineage_b64", self.workflow)
        self.assertNotIn("VIT_REANCHOR_REQUIRED", self.routing)

    def test_base_sensitive_lease_is_late_and_exact(self) -> None:
        readiness = self.workflow.split("\n  merge-readiness:\n", 1)[1]
        self.assertIn("needs: [profile, siq-ready-admission]", readiness)
        self.assertIn("Acquire late physical-main lease", readiness)
        self.assertIn("prospective_commit_sha", readiness)
        self.assertIn("prospective_result_tree", readiness)
        self.assertIn("FrontierIntegrationAdmissionReceipt", self.admission)

    def test_physical_guard_is_stability_not_source_head_ancestry(self) -> None:
        self.assertIn("OVC_REQUIRED_ASSURANCE_LEASE_INVALIDATED", self.lease_runner)
        self.assertIn("PREDECESSOR_MOVED", self.lease_runner)
        self.assertIn("PREDECESSOR_MOVED", self.admission)
        self.assertNotIn("merge-base --is-ancestor", self.workflow)
        self.assertNotIn("_is_ancestor", self.admission)
        self.assertNotIn("compareCommits", self.workflow)
        self.assertNotIn("compareCommits", self.admission)

    def test_vit_predecessor_disposition_advances_successor(self) -> None:
        for marker in [
            "final_integration_predecessor_lease_wait_ms",
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_HELD",
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_MERGED",
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_RELEASED_UNMERGED",
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_INVALIDATED",
        ]:
            self.assertIn(marker, self.admission)

    def test_predecessor_is_vit_placement_not_pr_number_or_ready_job_order(self) -> None:
        self.assertIn("resolve_vit_train_predecessor", self.admission)
        self.assertIn("tree_is_in_commit_ancestry", self.admission)
        self.assertNotIn("if number>=pr_number", self.admission.replace(" ", ""))
        self.assertNotIn("_exact_merge_job_pass", self.admission)
        self.assertNotIn("sorted(_open_pulls", self.admission)
        self.assertNotIn("checks.listForRef", self.workflow)
        self.assertNotIn("latestNamedRun", self.workflow)

    def test_terminal_disposition_does_not_expand_merge_authority(self) -> None:
        self.assertIn(
            "permissions:\n  contents: read\n  checks: read\n  pull-requests: read",
            self.workflow,
        )
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("pull-requests: write", self.workflow)
        self.assertNotIn("github.rest.pulls.merge", self.workflow)
        self.assertNotIn("enablePullRequestAutoMerge", self.workflow)

    def test_research_console_surface_is_in_current_pytest_suite(self) -> None:
        self.assertTrue(CONSOLE_PACKAGE.exists())
        self.assertIn(
            'python3 -m pip install -e ".[test]" -r requirements-console-vnext.txt',
            self.tests_workflow,
        )
        exact = "PYTHONPATH=src:. python3 -m pytest tests/research_console_vnext -q --tb=short"
        self.assertEqual(self.tests_workflow.count(exact), 1)
        full_suite = "PYTHONPATH=src:. python3 -m pytest tests -q --tb=short"
        self.assertEqual(self.tests_workflow.count(full_suite), 1)
        self.assertNotIn(full_suite, self.workflow)


if __name__ == "__main__":
    unittest.main()
