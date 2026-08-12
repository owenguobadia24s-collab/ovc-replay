from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
STATE = ROOT / "registries" / "implementation" / "python_test_runner" / "PYT_STATE_v0_1_DUAL_RUN.json"
PYPROJECT = ROOT / "pyproject.toml"


class PythonTestRunnerMigrationContractTests(unittest.TestCase):
    def test_dual_run_state_preserves_legacy_command_until_parity_gate(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "QA_REVIEW")
        self.assertEqual(state["target_runner"], "pytest")
        self.assertEqual(state["legacy_unittest_tests"], "PRESERVE")
        self.assertEqual(state["legacy_unittest_ci_command"], "PRESERVE_UNTIL_PYT_G2")

    def test_ci_runs_both_runners_and_collection_parity_checker(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("PYTHONPATH=src python3 -m unittest discover -s tests -v", workflow)
        self.assertIn("python3 -m pytest -v", workflow)
        self.assertIn("python3 tools/ci/check_pytest_unittest_parity.py", workflow)

    def test_pytest_is_pinned_as_test_extra_and_legacy_paths_are_collectable(self) -> None:
        pyproject = PYPROJECT.read_text(encoding="utf-8")
        self.assertIn('"pytest==9.1.1"', pyproject)
        self.assertIn('[tool.pytest.ini_options]', pyproject)
        self.assertIn('testpaths = ["tests"]', pyproject)
        self.assertIn('--import-mode=importlib', pyproject)
        self.assertIn('pythonpath = ["src", "tests"]', pyproject)


if __name__ == "__main__":
    unittest.main()
