from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"
ADMISSION = ROOT / "tools/ci/prvitr_live_admission.py"
ASSURANCE_PREFLIGHT = ROOT / "tools/ci/vit_assurance_preflight.py"
LEASE = ROOT / "tools/ci/ovc_run_with_main_lease.py"


class CiPerformanceRemediationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
        cls.admission = ADMISSION.read_text(encoding="utf-8")
        cls.assurance_preflight = ASSURANCE_PREFLIGHT.read_text(encoding="utf-8")
        cls.lease = LEASE.read_text(encoding="utf-8")

    def test_canonical_suite_contract_is_preserved_after_pyt_wp1(self) -> None:
        full_suite = "PYTHONPATH=src:. python3 -m pytest tests -q --tb=short"
        self.assertEqual(self.tests_workflow.count(full_suite), 1)
        self.assertNotIn(full_suite, self.workflow)
        self.assertIn("name: pytest-unittest-parity", self.tests_workflow)
        self.assertIn("name: runner-parity", self.tests_workflow)

    def test_a0_is_pip_bound_and_finishes_before_physical_lease(self) -> None:
        self.assertIn("A0_PIP_ONLY", self.assurance_preflight)
        self.assertIn("BASE_INDEPENDENT assurance", self.tests_workflow)
        self.assertIn("BASE_INDEPENDENT assurance", self.workflow)
        self.assertLess(
            self.workflow.index("\n  siq-ready-admission:\n"),
            self.workflow.index("\n  merge-readiness:\n"),
        )
        self.assertNotIn("tools/ci/ovc_run_with_main_lease.py", self.tests_workflow)

    def test_ready_binds_source_head_and_prospective_tree_not_ancestry(self) -> None:
        ready = self.workflow.split("\n  siq-ready-admission:\n", 1)[1].split(
            "\n  merge-readiness:\n", 1
        )[0]
        self.assertIn("source_head_sha", ready)
        self.assertIn("frontier_generation_id", ready)
        self.assertIn("prospective_result_tree", ready)
        self.assertIn("source_head_is_provenance_only", ready)
        self.assertNotIn("merge-base --is-ancestor", ready)
        self.assertNotIn("OVC_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN", ready)

    def test_a2_executes_on_exact_prospective_checkout_inside_one_lane(self) -> None:
        readiness = self.workflow.split("\n  merge-readiness:\n", 1)[1]
        self.assertIn("group: ovc-main-integration-lane-v1", readiness)
        self.assertIn("cancel-in-progress: false", readiness)
        self.assertIn("Checkout exact qualified prospective materialisation tree", readiness)
        self.assertIn("OVC_LEASE_PROSPECTIVE_COMMIT_SHA", readiness)
        self.assertIn("OVC_LEASE_RESULT_TREE", readiness)
        self.assertEqual(readiness.count("tools/ci/ovc_run_with_main_lease.py"), 1)

    def test_main_movement_after_lease_is_predecessor_moved_not_pr_replacement(self) -> None:
        self.assertIn("PREDECESSOR_MOVED", self.admission)
        self.assertIn("PREDECESSOR_MOVED", self.lease)
        self.assertIn("recompose the same PIP", self.lease)
        self.assertNotIn("fresh immutable reconciliation candidate", self.lease)
        self.assertNotIn("create_pull_request", self.admission)
        self.assertNotIn("REQUEUE_RECONCILE", self.admission)

    def test_final_assertion_binds_qualified_prospective_tree(self) -> None:
        self.assertIn("PRVITR_QUALIFIED_PROSPECTIVE_TREE_RECOMPOSITION_MISMATCH", self.admission)
        self.assertIn("PRVITR_PROSPECTIVE_COMMIT_TREE_MISMATCH", self.admission)
        self.assertIn("FrontierIntegrationAdmissionReceipt", self.admission)
        self.assertNotIn("PRVITR_FINAL_RESULT_TREE_MISMATCH", self.admission)

    def test_one_late_transaction_freeze_is_owned_by_final_physical_lane(self) -> None:
        self.assertIn("PHYSICAL_TRANSACTION_FREEZE_DEFERRED=SIQ_PHYSICAL_LANE", self.assurance_preflight)
        self.assertNotIn("build_live_transaction_freeze", self.assurance_preflight)
        self.assertIn("build_live_transaction_freeze", self.admission)
        self.assertIn("Exactly one late physical transaction freeze", self.admission)

    def test_required_checks_remain_fail_closed_before_ready(self) -> None:
        for check_name in (
            "VIT routing preflight",
            "tests",
            "pytest-unittest-parity",
            "runner-parity",
        ):
            self.assertIn(check_name, self.admission)
        self.assertIn('PROFILE_JOB_NAME = "OVC profile assurance"', self.admission)
        self.assertIn("SIQ_EXACT_A0_TESTS_WORKFLOW_FAILED", self.admission)
        self.assertIn("SIQ_EXACT_A0_PROFILE_WORKFLOW_FAILED", self.admission)

    def test_structured_metrics_cover_late_acquisition(self) -> None:
        self.assertIn("OVC_CI_METRIC", self.admission)
        self.assertIn("final_integration_predecessor_lease_wait_ms", self.admission)
        self.assertIn("OVC_SIQ_BASE_SENSITIVE_LEASE_ACQUIRED", self.admission)
        self.assertIn("OVC_SIQ_BASE_SENSITIVE_LEASE_RELEASED", self.admission)
        self.assertIn("CURRENT_VIT_PREDECESSOR_PHYSICAL", self.admission)

    def test_github_script_node_target_is_current(self) -> None:
        self.assertNotIn("actions/github-script@v7", self.workflow)
        self.assertNotIn("actions/github-script@v7", self.tests_workflow)
        self.assertIn("actions/github-script@v9", self.tests_workflow)


if __name__ == "__main__":
    unittest.main()
