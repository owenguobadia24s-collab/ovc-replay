from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from ovc.fsr_adjudication import adjudicate_hidden_construction
from ovc.fsr_full_stack import run_full_stack

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = os.environ.get("GITHUB_SHA", "FSR.WP11.POST_FREEZE.LOCAL_HEAD")


class FSRWP11AdjudicationTests(unittest.TestCase):
    def test_hidden_construction_is_opened_only_after_full_stack_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            result = run_full_stack(
                repo_root=REPO_ROOT,
                output_root=Path(root) / "frozen-run",
                source_commit=SOURCE_COMMIT,
            )
            before = json.loads(json.dumps(result["run_manifest"]))
            adjudication = adjudicate_hidden_construction(repo_root=REPO_ROOT, frozen_result=result)

            self.assertEqual(result["run_manifest"], before)
            self.assertTrue(adjudication["pipeline_unchanged_after_oracle_read"])
            self.assertEqual(adjudication["oracle_access_phase"], "FSR-WP11_POST_FREEZE_ONLY")
            self.assertEqual(adjudication["pipeline_run_manifest_sha256"], before["logical_sha256"])
            self.assertEqual(adjudication["interpretation"]["architecture_fidelity"], "PASS")
            self.assertEqual(adjudication["interpretation"]["architecture_failure_conclusion"], "NONE")
            self.assertGreater(len(adjudication["segment_metrics"]), 10)
            self.assertGreater(len(adjudication["comparisons"]), 15)
            self.assertGreater(adjudication["comparison_status_counts"].get("STRUCTURAL_SIGNAL_PRESENT", 0), 0)
            self.assertGreater(adjudication["comparison_status_counts"].get("NOT_TESTABLE", 0), 0)
            persistent = next(
                item for item in adjudication["comparisons"] if item["intent"] == "persistent_object_survival_candidate"
            )
            self.assertEqual(persistent["status"], "NOT_TESTABLE")
            self.assertEqual(persistent["testability"], "NOT_TESTABLE_AT_REACHED_LAYER")
            self.assertEqual(adjudication["authority"]["selector_mutation"], "NONE")
            self.assertEqual(adjudication["authority"]["validation_consumption"], "DENIED")
            self.assertFalse(adjudication["authority"]["market_evidence"])
            self.assertFalse(adjudication["authority"]["canonical"])
            self.assertFalse(adjudication["authority"]["promotable"])

            # GitHub Actions workflow-command notices create success annotations.
            # This makes exact post-freeze hashes/counts retrievable without exposing
            # the hidden construction ledger or adding a new workflow/write path.
            run_manifest = json.dumps(result["run_manifest"], sort_keys=True, separators=(",", ":"))
            adjudication_summary = json.dumps(
                {
                    "logical_sha256": adjudication["logical_sha256"],
                    "comparison_status_counts": adjudication["comparison_status_counts"],
                    "architecture_fidelity": adjudication["interpretation"]["architecture_fidelity"],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            print(f"::notice file=tests/full_stack_synthetic/test_fsr_wp11_adjudication.py,title=FSR_RUN_MANIFEST::{run_manifest}")
            print(f"::notice file=tests/full_stack_synthetic/test_fsr_wp11_adjudication.py,title=FSR_ADJUDICATION_SUMMARY::{adjudication_summary}")


if __name__ == "__main__":
    unittest.main()
