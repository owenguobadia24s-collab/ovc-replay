from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"
LEASE_RUNNER = ROOT / "tools/ci/ovc_run_with_main_lease.py"
ADMISSION_TOOL = ROOT / "tools/ci/prvitr_live_admission.py"
ROUTING_TOOL = ROOT / "tools/ci/vit_routing_preflight.py"
CONSOLE_PACKAGE = ROOT / "tests/research_console_vnext/__init__.py"


class ParallelIntegrationLaneTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
        self.lease_runner = LEASE_RUNNER.read_text(encoding="utf-8")
        self.admission = ADMISSION_TOOL.read_text(encoding="utf-8")
        self.routing = ROUTING_TOOL.read_text(encoding="utf-8")

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
        self.assertIn(
            "group: ovc-tests-${{ github.event.pull_request.number || inputs.aa0_target_head_sha || github.ref }}",
            self.tests_workflow,
        )
        self.assertIn("cancel-in-progress: true", self.workflow)
        self.assertIn("cancel-in-progress: true", self.tests_workflow)

    def test_single_physical_writer_lane_remains_but_only_after_qualification(self):
        self.assertEqual(self.workflow.count("group: ovc-main-integration-lane-v1"), 1)
        readiness = self.workflow.split("\n  merge-readiness:\n", 1)[1]
        self.assertIn("needs: [profile, siq-ready-admission]", readiness)
        self.assertIn("group: ovc-main-integration-lane-v1", readiness)
        self.assertIn("Acquire one-writer lease and late-bind current physical main", readiness)

    def test_base_independent_required_work_is_outside_physical_binding(self):
        self.assertNotIn("final-integration-window-admitted", self.tests_workflow)
        self.assertNotIn("OVC_LEASE_REQUIRED", self.tests_workflow)
        self.assertNotIn("tools/ci/ovc_run_with_main_lease.py", self.tests_workflow)
        self.assertIn("BASE_INDEPENDENT assurance", self.tests_workflow)
        self.assertIn("BASE_INDEPENDENT assurance", self.workflow)
        self.assertIn("OVC_READY_PHYSICAL_BASE_BINDING=NONE", self.workflow)

    def test_payload_assurance_precedes_routing_without_live_base_binding(self):
        assurance = "python3 tools/ci/vit_assurance_preflight.py"
        routing = "python3 tools/ci/vit_routing_preflight.py"
        self.assertIn(assurance, self.tests_workflow)
        self.assertIn(routing, self.tests_workflow)
        self.assertLess(self.tests_workflow.index(assurance), self.tests_workflow.index(routing))
        self.assertNotIn("VIT_REANCHOR_REQUIRED", self.routing)
        self.assertIn("PLACEMENT_NON_AUTHORITATIVE", self.routing)
        self.assertIn("NO_PHYSICAL_BASE_BINDING", self.routing)

    def test_ready_admission_binds_stable_pip_not_main(self):
        self.assertIn("OVC_VIT_QUALIFIED_PAYLOAD_READY", self.admission)
        ready = self.workflow.split("\n  siq-ready-admission:\n", 1)[1].split("\n  merge-readiness:\n", 1)[0]
        self.assertIn("pip_id", ready)
        self.assertNotIn("base_sha:", ready)
        self.assertNotIn("merge-base --is-ancestor", ready)

    def test_late_placement_is_ephemeral_and_exact_final_runs_on_it(self):
        readiness = self.workflow.split("\n  merge-readiness:\n", 1)[1]
        self.assertIn("placement_commit_sha", readiness)
        self.assertIn("placement_tree_sha", readiness)
        self.assertIn("git checkout --detach", readiness)
        self.assertIn("LateBindingPlacement", self.admission)
        self.assertIn('"merge-tree", "--write-tree"', self.admission)
        self.assertNotIn("resolve_vit_train_predecessor", self.admission)
        self.assertNotIn("PREDECESSOR_TIMEOUT_SECONDS", self.admission)

    def test_main_movement_no_longer_demands_new_candidate(self):
        self.assertIn("discard the ephemeral placement and retry the same qualified payload", self.admission)
        self.assertNotIn("PLACEMENT_RECOMPUTE_ONLY selective renewal is required", self.admission)
        self.assertNotIn("candidate does not contain acquired", self.admission)

    def test_stable_main_guard_remains_during_exact_final_only(self):
        self.assertIn("OVC_REQUIRED_ASSURANCE_LEASE_INVALIDATED", self.lease_runner)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.admission)
        self.assertIn("OVC_LEASE_BASE_SHA", self.workflow)
        self.assertNotIn("Prove candidate contains acquired current main", self.workflow)

    def test_terminal_disposition_does_not_expand_merge_authority(self):
        self.assertIn("permissions:\n  contents: read\n  checks: read\n  pull-requests: read", self.workflow)
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("pull-requests: write", self.workflow)
        self.assertNotIn("github.rest.pulls.merge", self.workflow)
        self.assertNotIn("enablePullRequestAutoMerge", self.workflow)

    def test_research_console_surface_is_in_operator_approved_canonical_shard_suite(self):
        self.assertTrue(CONSOLE_PACKAGE.exists())
        self.assertIn('python3 -m pip install -e ".[test]" -r requirements-console-vnext.txt', self.tests_workflow)
        exact = "PYTHONPATH=src:. python3 -m pytest tests/research_console_vnext -q --tb=short"
        self.assertEqual(self.tests_workflow.count(exact), 1)
        serial_full_suite = "PYTHONPATH=src:. python3 -m pytest tests -q --tb=short"
        self.assertEqual(self.tests_workflow.count(serial_full_suite), 0)
        self.assertIn("pytest_shard_canonical.py prove", self.tests_workflow)
        self.assertIn("pytest_shard_canonical.py run", self.tests_workflow)
        self.assertIn("pytest_shard_canonical.py aggregate", self.tests_workflow)
        self.assertIn("matrix:\n        shard: [0, 1, 2, 3]", self.tests_workflow)
        aggregate = self.tests_workflow.split("\n  pytest-unified:\n", 1)[1].split("\n  pytest-unittest-parity:\n", 1)[0]
        self.assertIn("name: tests", aggregate)
        self.assertEqual(self.tests_workflow.count("tools/ci/ovc_run_with_main_lease.py"), 0)


if __name__ == "__main__":
    unittest.main()
