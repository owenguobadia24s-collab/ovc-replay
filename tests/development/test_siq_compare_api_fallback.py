from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ovc-tiered-tests.yml"
ADMISSION = ROOT / "tools" / "ci" / "prvitr_live_admission.py"
FRONTIER = ROOT / "src" / "ovc" / "development" / "skills" / "vit_frontier_decoupling.py"
FRONTIER_IMPL = ROOT / "src" / "ovc" / "development" / "skills" / "vit_frontier_decoupling_impl.py"

class SIQCompareAPIFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.admission = ADMISSION.read_text(encoding="utf-8")
        cls.frontier = (
            FRONTIER.read_text(encoding="utf-8")
            + "\n"
            + FRONTIER_IMPL.read_text(encoding="utf-8")
        )

    def test_provider_compare_api_is_not_decision_bearing(self) -> None:
        self.assertNotIn("github.rest.repos.compareCommits", self.workflow)
        self.assertNotIn("compareCommits", self.admission)
        self.assertNotIn("OVC_COMPARE_API_404_FALLBACK_GIT", self.workflow)

    def test_local_git_is_normative_for_physical_history_and_tree_composition(self) -> None:
        self.assertIn('"log", "--first-parent"', self.frontier)
        self.assertIn('"diff",', self.frontier)
        self.assertIn('"read-tree", predecessor', self.frontier)
        self.assertIn('"write-tree"', self.frontier)
        self.assertNotIn("_is_ancestor(", self.admission)
        self.assertNotIn("git merge-base --is-ancestor", self.workflow)
        self.assertNotIn("OVC_RECONCILE_REQUIRED", self.admission)

    def test_missing_local_commit_is_fetched_before_tree_proof(self) -> None:
        self.assertIn('_git("fetch", "--no-tags", "origin", sha)', self.admission)
        self.assertIn("git cat-file -e", self.workflow)

    def test_github_api_is_metadata_and_exact_run_identity_only(self) -> None:
        self.assertIn("/pulls/{pr_number}", self.admission)
        self.assertIn("/actions/workflows/{workflow}/runs", self.admission)
        self.assertIn("/actions/runs/{run_id}/jobs", self.admission)
        self.assertIn("_exact_run(TESTS_WORKFLOW", self.admission)
        self.assertIn("_exact_run(TIERED_WORKFLOW", self.admission)

if __name__ == "__main__":
    unittest.main()