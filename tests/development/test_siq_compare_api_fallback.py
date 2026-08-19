from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ovc-tiered-tests.yml"
ADMISSION = ROOT / "tools" / "ci" / "prvitr_live_admission.py"


class SIQCompareAPIFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.admission = ADMISSION.read_text(encoding="utf-8")

    def test_provider_compare_api_is_not_decision_bearing_ancestry(self) -> None:
        self.assertNotIn("github.rest.repos.compareCommits", self.workflow)
        self.assertNotIn("compareCommits", self.admission)
        self.assertNotIn("OVC_COMPARE_API_404_FALLBACK_GIT", self.workflow)

    def test_local_git_is_normative_exact_composition_path(self) -> None:
        self.assertIn('["git", "merge-tree", "--write-tree", base_sha, head_sha]', self.admission)
        self.assertIn("VIT_LATE_BINDING_CONTENT_CONFLICT", self.admission)
        self.assertIn("prospective_tree_sha=result_tree", self.admission)
        self.assertNotIn("merge-base", self.admission)
        self.assertNotIn("OVC_RECONCILE_REQUIRED", self.admission)

    def test_missing_local_commit_is_fetched_before_exact_composition(self) -> None:
        self.assertIn('_git("fetch", "--no-tags", "origin", sha)', self.admission)
        self.assertIn('git cat-file -e "${OVC_PLACEMENT_COMMIT_SHA}^{commit}"', self.workflow)

    def test_github_api_is_metadata_and_exact_run_identity_only(self) -> None:
        self.assertIn("/pulls/{pr_number}", self.admission)
        self.assertIn("/actions/workflows/{workflow}/runs", self.admission)
        self.assertIn("/actions/runs/{run_id}/jobs", self.admission)
        self.assertIn("_exact_run(TESTS_WORKFLOW", self.admission)
        self.assertIn("_exact_run(TIERED_WORKFLOW", self.admission)


if __name__ == "__main__":
    unittest.main()
