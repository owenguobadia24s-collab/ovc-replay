from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from ovc.research_operations.cli import main


class ROWP2CLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        (self.repo / "registries" / "research_operations").mkdir(parents=True)
        (self.repo / "records" / "research_operations").mkdir(parents=True)
        registry = {
            "roots": [
                {"alias": "records", "path_template": "${RECORD_ROOT}", "read_only": False, "required": True},
                {"alias": "runtime", "path_template": "${RUNTIME_ROOT}", "read_only": False, "required": False},
            ]
        }
        (self.repo / "registries" / "research_operations" / "RESEARCH_OPERATIONS_PATH_REGISTRY_v0_1.json").write_text(json.dumps(registry), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, args: list[str]) -> tuple[int, dict]:
        stream = io.BytesIO()
        class Capture:
            buffer = stream
        with mock.patch("sys.stdout", Capture()):
            code = main(["--repo-root", str(self.repo), *args])
        return code, json.loads(stream.getvalue().decode("utf-8"))

    def test_open_session_and_queue(self) -> None:
        code, result = self.run_cli([
            "research", "open-session",
            "--instrument", "GBPUSD",
            "--release", "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
            "--role", "DISCOVERY",
            "--cutoff", "2023-06-15T10:00:00Z",
            "--objective", "CLI fixture",
            "--at", "2023-06-15T10:00:00Z",
        ])
        self.assertEqual(0, code)
        self.assertTrue(result["draft_id"].startswith("draft:research_session:"))
        code, queue = self.run_cli(["queue", "show", "--type", "incomplete-sessions", "--as-of", "2023-06-15T11:00:00Z"])
        self.assertEqual(0, code)
        self.assertEqual(1, len(queue["items"]))

    def test_no_git_or_remote_side_effect_command_exists(self) -> None:
        text = Path(__file__).parents[2] / "src" / "ovc" / "research_operations" / "cli.py"
        source = text.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("rclone", source)
        self.assertNotIn("git push", source)


if __name__ == "__main__":
    unittest.main()
