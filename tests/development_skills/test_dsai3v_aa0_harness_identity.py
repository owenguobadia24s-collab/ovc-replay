from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.ci.aa0_harness_identity import HarnessIdentityError, compute_harness_identity


class Dsai3vAa0HarnessIdentityTests(unittest.TestCase):
    def _repo(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "aa0@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "AA0 Harness Test"], check=True)
        return tmp, root

    def _write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "--", relative], check=True)

    def test_identity_is_order_and_cwd_independent(self) -> None:
        tmp, root = self._repo()
        self.addCleanup(tmp.cleanup)
        self._write(root, "a.txt", "alpha\n")
        self._write(root, "b.txt", "beta\n")
        first = compute_harness_identity(root, ("a.txt", "b.txt"))
        old_cwd = Path.cwd()
        try:
            os.chdir(root)
            second = compute_harness_identity(root, ("b.txt", "a.txt"))
        finally:
            os.chdir(old_cwd)
        self.assertEqual(first, second)

    def test_commit_metadata_and_branch_identity_do_not_change_harness(self) -> None:
        tmp, root = self._repo()
        self.addCleanup(tmp.cleanup)
        self._write(root, "a.txt", "alpha\n")
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "first"], check=True)
        before = compute_harness_identity(root, ("a.txt",))
        subprocess.run(["git", "-C", str(root), "commit", "--allow-empty", "-qm", "metadata only"], check=True)
        subprocess.run(["git", "-C", str(root), "branch", "alternate-placement"], check=True)
        after = compute_harness_identity(root, ("a.txt",))
        self.assertEqual(before, after)

    def test_actual_harness_content_change_changes_identity(self) -> None:
        tmp, root = self._repo()
        self.addCleanup(tmp.cleanup)
        self._write(root, "a.txt", "alpha\n")
        before = compute_harness_identity(root, ("a.txt",))
        self._write(root, "a.txt", "alpha changed\n")
        after = compute_harness_identity(root, ("a.txt",))
        self.assertNotEqual(before, after)

    def test_missing_required_input_fails_closed(self) -> None:
        tmp, root = self._repo()
        self.addCleanup(tmp.cleanup)
        self._write(root, "a.txt", "alpha\n")
        with self.assertRaisesRegex(HarnessIdentityError, "AA0_HARNESS_REQUIRED_INPUT_MISSING"):
            compute_harness_identity(root, ("missing.txt",))

    def test_repository_workflow_uses_stable_step_output_not_hashfiles(self) -> None:
        workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
        self.assertNotIn("hashFiles(", workflow)
        # G5 PASS adds one operator-approved canonical-shard assurance planner while
        # preserving the existing unified, unittest-parity, and runner-parity users.
        self.assertEqual(workflow.count("id: aa0-harness"), 4)
        self.assertGreaterEqual(workflow.count("steps.aa0-harness.outputs.harness_hash"), 6)


if __name__ == "__main__":
    unittest.main()
