from __future__ import annotations
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"
RESOLVER = ROOT / "tools/ci/prvitr_live_admission.py"
READY_SELECTOR = ROOT / "tools/ci/prvitr_rac_ready.py"


class CiPerformanceRemediationTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
        self.resolver = RESOLVER.read_text(encoding="utf-8")
        self.ready_selector = READY_SELECTOR.read_text(encoding="utf-8")
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
        self.assertIn("prvitr_rac_ready.py", self.ready)
        self.assertIn("import tools.ci.prvitr_live_admission as live", self.ready_selector)
        self.assertIn("return live.command_ready()", self.ready_selector)
        self.assertIn("OVC_VIT_QUALIFIED_PAYLOAD_READY", self.resolver)
        self.assertIn("prvitr_live_admission.py acquire", self.readiness)
        self.assertIn("OVC_SIQ_BASE_SENSITIVE_LEASE_ACQUIRED", self.resolver)
        self.assertLess(self.workflow.index("\n  siq-ready-admission:\n"), self.workflow.index("\n  merge-readiness:\n"))

    def test_ready_admission_is_payload_only_and_does_not_bind_current_main(self):
        ready_body = self.resolver.split("def command_ready()", 1)[1].split("def command_acquire()", 1)[0]
        self.assertIn("BaseIndependentAssuranceGeneration", ready_body)
        self.assertIn("OVC_VIT_QUALIFIED_PAYLOAD_READY", ready_body)
        self.assertNotIn("current_main = _branch_sha(base_ref)", ready_body)
        self.assertNotIn("merge-base", ready_body)
        self.assertIn("no physical-main predecessor is acquired during qualification", ready_body)
        self.assertNotIn("_branch_sha(base_ref)", self.ready_selector)

    def test_required_checks_are_fail_closed_before_ready(self):
        for check_name in ("VIT routing preflight", "tests", "pytest-unittest-parity", "runner-parity"):
            self.assertIn(check_name, self.resolver)
        self.assertIn('PROFILE_JOB_NAME = "OVC profile assurance"', self.resolver)
        self.assertIn("SIQ_EXACT_TESTS_WORKFLOW_FAILED", self.resolver)
        self.assertIn("SIQ_EXACT_PROFILE_WORKFLOW_FAILED", self.resolver)

    def test_final_readiness_holds_lane_only_for_exact_final_assurance(self):
        self.assertIn("group: ovc-main-integration-lane-v1", self.readiness)
        self.assertIn("cancel-in-progress: false", self.readiness)
        self.assertIn("Run mandatory SIQ/PDC exact-final assurance inside lease", self.readiness)
        self.assertIn("prvitr_live_admission.py finalize", self.readiness)
        self.assertEqual(self.readiness.count("tools/ci/ovc_run_with_main_lease.py"), 1)
        self.assertIn("OVC_INTEGRATION_ADMISSION_RECEIPT", self.resolver)

    def test_candidate_is_late_composed_before_exact_final_assurance(self):
        self.assertIn('git checkout --detach "${OVC_PLACEMENT_COMMIT_SHA}"', self.readiness)
        self.assertIn('test "$(git rev-parse "${OVC_PLACEMENT_COMMIT_SHA}^{tree}")" = "${OVC_PLACEMENT_TREE_SHA}"', self.readiness)
        self.assertIn('["git", "merge-tree", "--write-tree", base_sha, head_sha]', self.resolver)
        self.assertIn("VIT_LATE_BINDING_CONTENT_CONFLICT", self.resolver)
        self.assertIn("OVC_VIT_LATE_BINDING_PLACEMENT_ACQUIRED", self.resolver)

    def test_stable_main_and_exact_placement_checks_are_fail_closed(self):
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.resolver)
        self.assertIn("final_main = _branch_sha(base_ref)", self.resolver)
        self.assertIn("PRVITR_LATE_BINDING_PLACEMENT_MISMATCH", self.resolver)
        self.assertIn("recomposed.prospective_tree_sha != placement_tree", self.resolver)
        self.assertIn("recomposed.placement_id != placement_id", self.resolver)

    def test_late_binding_evidence_covers_qualification_placement_and_receipt(self):
        for marker in (
            "OVC_BASE_INDEPENDENT_ASSURANCE_GENERATION",
            "OVC_VIT_QUALIFIED_PAYLOAD_READY",
            "OVC_VIT_LATE_BINDING_PLACEMENT_ACQUIRED",
            "OVC_SIQ_BASE_SENSITIVE_LEASE_ACQUIRED",
            "OVC_INTEGRATION_ADMISSION_RECEIPT",
            "OVC_FINAL_INTEGRATION_WINDOW_PASS",
        ):
            self.assertIn(marker, self.resolver)

    def test_github_script_node_target_is_current(self):
        self.assertNotIn("actions/github-script@v7", self.workflow)
        self.assertNotIn("actions/github-script@v7", self.tests_workflow)
        self.assertIn("actions/github-script@v9", self.tests_workflow)
        self.assertNotIn("actions/github-script@", self.ready)
        self.assertIn("prvitr_rac_ready.py", self.ready)
        self.assertIn("return live.command_ready()", self.ready_selector)


if __name__ == "__main__":
    unittest.main()
