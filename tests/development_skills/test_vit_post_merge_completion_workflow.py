from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "vit-post-merge-completion.yml"


class VitPostMergeCompletionWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_historical_recovery_is_manual_input_on_existing_workflow(self) -> None:
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("merge_sha:", self.text)
        self.assertIn("required: false", self.text)
        self.assertIn("OVC_VIT_RECOVERY_MERGE_SHA: ${{ inputs.merge_sha || github.sha }}", self.text)

    def test_recovery_preserves_existing_controller_executor_boundary(self) -> None:
        self.assertIn("runs-on: [self-hosted, Windows]", self.text)
        self.assertIn("OVC_EXTERNAL_ARTIFACT_ROOT", self.text)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", self.text)
        self.assertIn("PYTHONPATH: src;.\n", self.text)
        self.assertIn("--merge-sha \"$env:OVC_VIT_RECOVERY_MERGE_SHA\"", self.text)

    def test_checkout_keeps_latest_code_and_fetches_history_for_exact_target(self) -> None:
        self.assertIn("ref: ${{ github.sha }}", self.text)
        self.assertIn("fetch-depth: 0", self.text)
        self.assertNotIn("force", self.text.lower())


if __name__ == "__main__":
    unittest.main()
