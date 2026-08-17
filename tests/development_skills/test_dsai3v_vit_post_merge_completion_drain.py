from __future__ import annotations
import unittest
from pathlib import Path
from tools.ci.vit_post_merge_completion_drain import _lawful_historical_skip
ROOT=Path(__file__).resolve().parents[2]
class TestCompletionDrain(unittest.TestCase):
 def test_only_historical_absence_is_skippable(self):
  self.assertEqual(_lawful_historical_skip(RuntimeError("expected exactly one merged main PR for x, found 0")),"NO_ASSOCIATED_MAIN_PR")
  self.assertEqual(_lawful_historical_skip(RuntimeError("expected one pre-write transaction freeze for PR #1, found 0")),"HISTORICAL_PREWRITE_FREEZE_ABSENT")
  for text in ("POST_WRITE_TREE_MISMATCH","VIT_LEDGER_INTEGRITY_FAIL","expected one pre-write transaction freeze for PR #1, found 2"):
   self.assertIsNone(_lawful_historical_skip(RuntimeError(text)))
 def test_workflow_is_per_merge_read_only_and_non_churning(self):
  w=(ROOT/".github/workflows/vit-post-merge-completion.yml").read_text()
  self.assertIn("group: ovc-vit-local-post-merge-completion-v2-${{ inputs.merge_sha || github.sha }}",w); self.assertIn("vit_post_merge_completion_drain.py",w)
  self.assertIn("contents: read",w); self.assertIn("pull-requests: read",w); self.assertNotIn("contents: write",w); self.assertNotIn("pull-requests: write",w); self.assertNotIn("gh pr create",w)
 def test_historical_recovery_is_separate(self):
  h=(ROOT/"src/ovc/development/skills/vit_historical_completion_recovery.py").read_text().lower(); n=(ROOT/"src/ovc/development/skills/vit_completion_closeout.py").read_text()
  self.assertIn("historical",h); self.assertIn("ovc-vit-physical-completion-state/v1",n); self.assertNotIn("ABSENT_NOT_EMITTED",n)
if __name__=="__main__": unittest.main()
