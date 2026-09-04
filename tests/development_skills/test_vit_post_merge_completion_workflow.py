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

    def test_executor_is_github_hosted_and_operator_device_independent(self) -> None:
        self.assertIn("runs-on: ubuntu-latest", self.text)
        self.assertNotIn("self-hosted", self.text)
        self.assertNotIn("OVC_EXTERNAL_ARTIFACT_ROOT", self.text)
        self.assertIn("Bind runner-local staging paths", self.text)
        self.assertIn('echo "OVC_VIT_RECEIPT_STAGE=${RUNNER_TEMP}/vit-completion-receipts" >> "$GITHUB_ENV"', self.text)
        self.assertIn('echo "OVC_VIT_REMOTE_REPORT=${RUNNER_TEMP}/vit-remote-publication-report.json" >> "$GITHUB_ENV"', self.text)
        self.assertNotIn("OVC_VIT_RECEIPT_STAGE: ${{ runner.temp }}", self.text)
        self.assertNotIn("OVC_VIT_REMOTE_REPORT: ${{ runner.temp }}", self.text)
        self.assertIn("python tools/ci/vit_post_merge_completion_remote.py", self.text)
        self.assertIn("--receipt-store-root \"$OVC_VIT_RECEIPT_STAGE\"", self.text)

    def test_remote_receipt_publication_is_bounded_and_readback_verified(self) -> None:
        self.assertIn("python tools/ci/vit_publish_completion_receipts.py", self.text)
        self.assertIn("--remote ovc_r2", self.text)
        self.assertIn("--prefix ovc-evidence/development/vit-completion-receipts/v1", self.text)
        self.assertIn("Publish immutable remote receipt tree and verify readback", self.text)
        self.assertIn("RCLONE_CONFIG_OVC_R2_ACCESS_KEY_ID", self.text)
        self.assertIn("RCLONE_CONFIG_OVC_R2_SECRET_ACCESS_KEY", self.text)

    def test_executor_preserves_read_only_github_authority(self) -> None:
        self.assertIn("actions: read", self.text)
        self.assertIn("checks: read", self.text)
        self.assertIn("contents: read", self.text)
        self.assertIn("pull-requests: read", self.text)
        self.assertNotIn("contents: write", self.text)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", self.text)
        self.assertIn("PYTHONPATH: src:.\n", self.text)

    def test_checkout_keeps_latest_code_and_fetches_history_for_exact_target(self) -> None:
        self.assertIn("ref: ${{ github.sha }}", self.text)
        self.assertIn("fetch-depth: 0", self.text)
        self.assertNotIn("force", self.text.lower())


if __name__ == "__main__":
    unittest.main()
