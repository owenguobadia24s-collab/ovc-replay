from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INDEX = (
    ROOT
    / "docs"
    / "releases"
    / "prospective-source-v0-1"
    / "rps-wp2"
    / "RPS_WP2_COMPACT_EVIDENCE_INDEX.json"
)


class RpsWp2CompactEvidenceIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = json.loads(INDEX.read_text(encoding="utf-8"))

    def test_identity_and_logical_hashes_are_exact(self) -> None:
        value = self.value
        self.assertEqual(
            value["slice_id"],
            "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1",
        )
        self.assertEqual(value["coverage_state"], "GAPPED")
        self.assertEqual(
            value["manifest_logical_sha256"],
            "429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41",
        )
        self.assertEqual(
            value["manifest_file_sha256"],
            "8509b6cc66814663786e429e6ba1dc0c3497482fc6ac8ceb016cfc1867ec78eb",
        )
        self.assertEqual(
            value["quarantine_inventory_logical_sha256"],
            "ce58bc91ea36e920fa2f855a96ee7084e5d867b976a0d06a9e94bf65b20084c2",
        )

    def test_all_nine_compact_files_are_hash_pinned(self) -> None:
        files = self.value["compact_files"]
        self.assertEqual(len(files), 9)
        self.assertEqual(len({item["name"] for item in files}), 9)
        for item in files:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(item["size_bytes"], 0)

    def test_source_object_inventory_is_exact(self) -> None:
        objects = self.value["source_objects"]
        self.assertEqual(len(objects), 4)
        counts = {
            (item["clock"], item["side"]): item["row_count"]
            for item in objects
        }
        self.assertEqual(
            counts,
            {
                ("M1", "BID"): 4285,
                ("M1", "ASK"): 4285,
                ("H1", "BID"): 72,
                ("H1", "ASK"): 72,
            },
        )
        for item in objects:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(item["schema_fingerprint"], r"^[0-9a-f]{64}$")

    def test_gapped_qa_and_downstream_exclusion_pass(self) -> None:
        qa = self.value["qa"]
        gaps = qa["gap_and_duplicate"]
        self.assertEqual(gaps["state"], "PASS_GAPPED")
        self.assertEqual(gaps["missing_timestamps_per_side"], 35)
        self.assertEqual(gaps["gap_runs_per_side"], 24)
        self.assertTrue(gaps["shared_m1_timestamp_set"])
        self.assertEqual(gaps["duplicates"], 0)
        self.assertEqual(gaps["non_monotonic"], 0)

        self.assertEqual(qa["bid_ask"]["state"], "PASS")
        self.assertEqual(qa["native_h1"]["state"], "PASS")
        self.assertEqual(qa["native_h1"]["ohlc_mismatches"], 0)

        coverage = qa["downstream_coverage"]
        self.assertEqual(coverage["state"], "PASS_GAPPED_EXCLUSION")
        self.assertEqual(coverage["15M"], {"available": 271, "unavailable": 17})
        self.assertEqual(
            coverage["H1_M1_DERIVED"],
            {"available": 64, "unavailable": 8},
        )
        self.assertEqual(coverage["2H"], {"available": 30, "unavailable": 6})
        self.assertEqual(coverage["incomplete_parent_consumption"], "DENIED")
        self.assertFalse(coverage["repair_performed"])
        self.assertFalse(coverage["forward_fill_performed"])
        self.assertFalse(coverage["interpolation_performed"])
        self.assertFalse(coverage["synthesis_performed"])

    def test_freeze_retains_all_authority_denials(self) -> None:
        freeze = self.value["freeze"]
        self.assertTrue(freeze["frozen"])
        self.assertTrue(freeze["source_quarantine_unchanged_after_copy"])
        self.assertFalse(freeze["provider_network_access_performed"])
        self.assertEqual(freeze["release_status"], "NOT_A_RELEASE")
        self.assertEqual(freeze["selector_eligibility"], "NONE")
        self.assertEqual(freeze["r2_publication"], "DENIED")
        self.assertEqual(freeze["validation_consumption"], "DENIED")
        self.assertEqual(freeze["live_prospective_append"], "DENIED")
        self.assertEqual(self.value["acceptance"]["status"], "PASS")
        self.assertEqual(self.value["acceptance"]["next_packet"], "RPS-WP3")


if __name__ == "__main__":
    unittest.main()
