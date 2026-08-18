from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


TOOL_PATH = Path(__file__).resolve().parents[2] / "tools" / "ci" / "vit_post_merge_completion.py"
SPEC = importlib.util.spec_from_file_location("vit_post_merge_completion_trace_tool", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class VitPostMergeCompletionTraceCollectionTests(unittest.TestCase):
    def test_pr_head_workflow_observations_fetches_completed_pr_runs_and_jobs(self) -> None:
        calls = []

        def fake_json(url, token):
            calls.append(url)
            if "/actions/runs?" in url:
                self.assertIn("head_sha=" + "a" * 40, url)
                self.assertIn("event=pull_request", url)
                self.assertIn("status=completed", url)
                return {
                    "workflow_runs": [
                        {"id": 1001, "name": "tests", "status": "completed"},
                        {"id": 1002, "name": "tiered", "status": "completed"},
                    ]
                }
            if url.endswith("/actions/runs/1001/jobs?per_page=100"):
                return {"jobs": [{"id": 2001, "name": "repository suite"}]}
            if url.endswith("/actions/runs/1002/jobs?per_page=100"):
                return {"jobs": [{"id": 2002, "name": "FINAL_HEAD profile"}]}
            raise AssertionError(url)

        with patch.object(TOOL, "_json", side_effect=fake_json):
            runs, jobs = TOOL._pr_head_workflow_observations(
                "owner/repo",
                "a" * 40,
                "token",
            )

        self.assertEqual([row["id"] for row in runs], [1001, 1002])
        self.assertEqual(jobs[1001][0]["id"], 2001)
        self.assertEqual(jobs[1002][0]["id"], 2002)
        self.assertEqual(len(calls), 3)

    def test_invalid_workflow_payload_fails_closed(self) -> None:
        with patch.object(TOOL, "_json", return_value=[]):
            with self.assertRaisesRegex(TOOL.PostMergeCompletionError, "workflow timing response invalid"):
                TOOL._pr_head_workflow_observations(
                    "owner/repo",
                    "a" * 40,
                    "token",
                )


if __name__ == "__main__":
    unittest.main()
