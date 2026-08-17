from __future__ import annotations

import unittest
from pathlib import Path

from tools.ci.vit_post_merge_completion_drain import _lawful_historical_skip


ROOT = Path(__file__).resolve().parents[2]


class Dsai3vVitPostMergeCompletionDrainTests(unittest.TestCase):
    def test_only_absent_historical_inputs_are_skippable(self) -> None:
        self.assertEqual(
            _lawful_historical_skip(
                RuntimeError("expected exactly one merged main PR for abc, found 0")
            ),
            "NO_ASSOCIATED_MAIN_PR",
        )
        self.assertEqual(
            _lawful_historical_skip(
                RuntimeError("expected one pre-write transaction freeze for PR #1, found 0")
            ),
            "HISTORICAL_PREWRITE_FREEZE_ABSENT",
        )
        self.assertIsNone(_lawful_historical_skip(RuntimeError("POST_WRITE_TREE_MISMATCH")))
        self.assertIsNone(_lawful_historical_skip(RuntimeError("VIT_LEDGER_INTEGRITY_FAIL")))
        self.assertIsNone(
            _lawful_historical_skip(
                RuntimeError("expected one pre-write transaction freeze for PR #1, found 2")
            )
        )

    def test_workflow_keeps_each_merge_completion_demand_and_never_writes_git(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "vit-post-merge-completion.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "group: ovc-vit-local-post-merge-completion-v2-${{ inputs.merge_sha || github.sha }}",
            workflow,
        )
        self.assertIn("vit_post_merge_completion_drain.py", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("pull-requests: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("pull-requests: write", workflow)
        self.assertNotIn("gh pr create", workflow)

    def test_historical_recovery_remains_separate_from_normal_completion(self) -> None:
        historical = (
            ROOT / "src" / "ovc" / "development" / "skills" / "vit_historical_completion_recovery.py"
        ).read_text(encoding="utf-8")
        normal = (
            ROOT / "src" / "ovc" / "development" / "skills" / "vit_completion_closeout.py"
        ).read_text(encoding="utf-8")
        self.assertIn("historical", historical.lower())
        self.assertIn("ovc-vit-physical-completion-state/v1", normal)
        self.assertNotIn("ABSENT_NOT_EMITTED", normal)


if __name__ == "__main__":
    unittest.main()
