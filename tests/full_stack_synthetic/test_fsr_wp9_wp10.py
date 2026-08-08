from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ovc.fsr_full_stack import replay_identity, run_full_stack

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "FSR.WP10.CLEAN_ROOM.SAME_HEAD"


class FSRWP9WP10Tests(unittest.TestCase):
    def test_research_operations_and_clean_room_replay_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            first = run_full_stack(repo_root=REPO_ROOT, output_root=root_path / "run1", source_commit=SOURCE_COMMIT)
            second = run_full_stack(repo_root=REPO_ROOT, output_root=root_path / "run2", source_commit=SOURCE_COMMIT)

            self.assertEqual(replay_identity(first), replay_identity(second))
            manifest = first["run_manifest"]
            self.assertFalse(manifest["hidden_construction_consumed"])
            self.assertTrue(manifest["authority"]["synthetic"])
            self.assertFalse(manifest["authority"]["market_evidence"])
            self.assertFalse(manifest["authority"]["canonical"])
            self.assertFalse(manifest["authority"]["promotable"])
            self.assertEqual(manifest["authority"]["selector_mutation"], "NONE")
            self.assertEqual(manifest["authority"]["publication"], "NONE")
            self.assertEqual(manifest["authority"]["validation_consumption"], "DENIED")
            self.assertGreater(manifest["counts"]["source_rows"], 2800)
            self.assertEqual(manifest["counts"]["c1_records"], 212)
            self.assertGreater(manifest["counts"]["c2_snapshots"], 0)
            self.assertGreater(manifest["counts"]["c2e_episodes"], 0)
            self.assertGreater(manifest["counts"]["srfd_representations"], 0)
            self.assertGreater(manifest["counts"]["srfd_family_catalogs"], 0)
            self.assertGreater(manifest["counts"]["research_records"], 0)
            self.assertGreater(manifest["counts"]["read_model_nodes"], 0)
            self.assertEqual(
                set(manifest["not_reached"]),
                {
                    "OccurrenceContext standalone forward object",
                    "C2P persistent structural objects",
                    "revised C2.5 forward event projection",
                    "canonical forward C3",
                },
            )

            ro = first["research_operations"]
            self.assertEqual(ro["qa_run"]["disposition"], "PASS")
            self.assertTrue(all(item["status"] == "PASS" for item in ro["qa_run"]["assertions"]))
            self.assertEqual(len(ro["records"]), 3)
            self.assertTrue(all(item["lifecycle_state"] == "FROZEN" for item in ro["records"]))
            self.assertTrue(all(item["authority_state"] == "FROZEN" for item in ro["records"]))
            self.assertEqual(ro["authority"]["market_authority"], "NONE")
            self.assertEqual(ro["authority"]["validation_consumption"], "DENIED")
            self.assertEqual(len(ro["catalogue"]["issues"]), 0)
            self.assertGreater(len(ro["catalogue"]["nodes"]), 0)
            self.assertGreater(len(ro["read_model"]["nodes"]), len(ro["records"]))

            for stage, digest in manifest["stage_hashes"].items():
                self.assertEqual(len(str(digest)), 64, stage)


if __name__ == "__main__":
    unittest.main()
