from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
TIERED_WORKFLOW = ROOT / ".github" / "workflows" / "ovc-tiered-tests.yml"
PYPROJECT = ROOT / "pyproject.toml"
STATE = ROOT / "registries" / "implementation" / "python_test_runner" / "PYT_STATE_v0_1_DUAL_RUN_PARITY.json"
POLICY = ROOT / "docs" / "testing" / "PYTHON_TEST_RUNNER_POLICY_v0_1.md"
WP2 = ROOT / "docs" / "releases" / "python-test-runner-migration-v0-1" / "pyt-wp2"
EACR = ROOT / "docs" / "releases" / "external-artifact-capacity-ownership-v0-1"


class PythonTestRunnerMigrationContractTests(unittest.TestCase):
    def test_legacy_unittest_rollback_command_and_siq_timing_are_preserved(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        tiered = TIERED_WORKFLOW.read_text(encoding="utf-8")
        full_suite = "python3 -m unittest discover -s tests -v"
        self.assertEqual(workflow.count(full_suite), 1)
        self.assertIn("Historical rollback command (not executed)", workflow)
        self.assertIn("Complete repository suite as BASE_INDEPENDENT assurance", workflow)
        self.assertNotIn("tools/ci/ovc_run_with_main_lease.py", workflow)
        self.assertIn("tools/ci/ovc_run_with_main_lease.py", tiered)
        self.assertIn("Run mandatory SIQ/PDC exact-final assurance inside lease", tiered)
        self.assertIn("name: tests", workflow)

    def test_pytest_is_pinned_and_parity_jobs_are_explicit(self) -> None:
        pyproject = PYPROJECT.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('pytest==9.1.1', pyproject)
        self.assertIn("pytest-unittest-parity", workflow)
        self.assertIn("runner-parity", workflow)
        self.assertIn("pytest_unittest_parity.py run", workflow)
        self.assertIn("pytest_unittest_parity.py collect", workflow)

    def test_cutover_cannot_remove_unittest_before_merged_main_parity(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual(state["legacy_unittest_tests"], "PRESERVE")
        self.assertEqual(state["legacy_unittest_ci_command"], "PRESERVE_UNTIL_PYT_G2")
        self.assertEqual(state["pytest_native_tests"], "NOT_YET_ADMITTED_BY_PYT_G1")
        self.assertIn("MERGED_MAIN_PYT_G1_PASS", state["cutover_rule"])

    def test_policy_forbids_test_weakening_and_silent_native_admission(self) -> None:
        policy = POLICY.read_text(encoding="utf-8")
        self.assertIn("not rewritten, deleted or weakened", policy)
        self.assertIn("not silently admitted", policy)
        self.assertIn("separately inventory/admit pytest-native tests", policy)

    def test_wp2_qa_binds_clean_population_and_eacr_successor(self) -> None:
        evidence = json.loads((WP2 / "PYT_WP2_REMEDIATION_EVIDENCE.json").read_text(encoding="utf-8"))
        qa = json.loads((WP2 / "PYT_G2_QA_PACKET.json").read_text(encoding="utf-8"))
        discrepancy = json.loads(
            (WP2 / "PYT_WP2_PROGRAMME_OWNED_DISCREPANCY_EACR_QA_LOGICAL_HASH.json").read_text(encoding="utf-8")
        )
        successor = json.loads(
            (EACR / "EACR_WP4_WP5_CONFORMANCE_QA_IDENTITY_SUCCESSOR.json").read_text(encoding="utf-8")
        )
        result = evidence["fresh_pytest_unified"]["results"]
        self.assertEqual((result["failed"], result["errors"], result["collection_errors"]), (0, 0, 0))
        self.assertEqual(result["junit_tests"], result["ordinary_passed"] + result["subtests_passed"] + result["skipped"])
        self.assertEqual(qa["recommendation"], "PASS")
        self.assertEqual(qa["blockers"], [])
        self.assertEqual(discrepancy["status"], "RESOLVED_BY_PROGRAMME_ADJUDICATION")
        corrected = "827ff0afb6e9344ead9b57eda4c6a4db7b9e29710ac2b311127779541282a024"
        self.assertEqual(discrepancy["resolution"]["corrected_logical_sha256"], corrected)
        self.assertEqual(successor["logical_sha256"], corrected)
        self.assertTrue(discrepancy["resolution"]["historical_qa_artifact_unchanged"])
        self.assertEqual(discrepancy["authority_effect"], "NONE")


if __name__ == "__main__":
    unittest.main()
