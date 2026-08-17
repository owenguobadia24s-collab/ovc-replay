from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ovc-tiered-tests.yml"


class SIQCompareAPIFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_compare_api_remains_primary_ancestry_path(self) -> None:
        self.assertGreaterEqual(self.text.count("github.rest.repos.compareCommits"), 2)

    def test_compare_404_has_git_ancestry_fallback(self) -> None:
        self.assertIn("const {execFileSync} = require('node:child_process');", self.text)
        self.assertGreaterEqual(self.text.count("OVC_COMPARE_API_404_FALLBACK_GIT"), 2)
        self.assertGreaterEqual(
            self.text.count("['merge-base', '--is-ancestor', base, head]"),
            2,
        )

    def test_non_404_compare_errors_still_fail_closed(self) -> None:
        self.assertGreaterEqual(
            self.text.count("if (error?.status !== 404) throw error;"),
            2,
        )

    def test_missing_local_commit_is_fetched_before_fallback_proof(self) -> None:
        self.assertGreaterEqual(
            self.text.count("execFileSync('git', ['fetch', '--no-tags', 'origin', ref]"),
            2,
        )


if __name__ == "__main__":
    unittest.main()
