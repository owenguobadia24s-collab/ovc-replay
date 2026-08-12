from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
PYPROJECT = ROOT / "pyproject.toml"
STATE = ROOT / "registries" / "implementation" / "python_test_runner" / "PYT_STATE_v0_1_DUAL_RUN_PARITY.json"
POLICY = ROOT / "docs" / "testing" / "PYTHON_TEST_RUNNER_POLICY_v0_1.md"


class PythonTestRunnerMigrationContractTests(unittest.TestCase):
    def test_legacy_unittest_command_is_preserved_exactly(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("PYTHONPATH=src python3 -m unittest discover -s tests -v", workflow)
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


if __name__ == "__main__":
    unittest.main()
