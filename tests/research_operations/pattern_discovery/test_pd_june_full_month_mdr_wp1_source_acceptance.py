from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.research_operations.validate_pd_june_full_month_mdr_wp1_source_acceptance import validate


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-full-month-mdr"
INDEX = BASE / "PD_JUNE_FULL_MONTH_MDR_WP1_SOURCE_ACCEPTANCE_INDEX.json"


class PDJuneFullMonthMDRWP1SourceAcceptanceTests(unittest.TestCase):
    def test_packet_validator_passes(self) -> None:
        validate()

    def test_source_and_target_boundaries_remain_exact(self) -> None:
        value = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertEqual(value["target_start_utc"], "2026-06-01T00:00:00Z")
        self.assertEqual(value["target_end_exclusive_utc"], "2026-07-01T00:00:00Z")
        self.assertEqual(value["source_window_start_utc"], "2026-05-30T00:00:00Z")
        self.assertEqual(value["source_window_end_exclusive_utc"], "2026-07-03T00:00:00Z")
        self.assertEqual(value["target_eligibility"], "TARGET_JUNE_ONLY")
        self.assertEqual(value["context_eligibility"], "MAY_AND_JULY_CONTEXT_ONLY")

    def test_sparse_source_is_explicit_and_never_repaired(self) -> None:
        value = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertEqual(value["qa"]["m1"]["state"], "PASS_PAIRED_SPARSE")
        self.assertEqual(value["qa"]["m1"]["absent_timestamps_per_side"], 138)
        self.assertEqual(value["qa"]["m1"]["gap_runs_per_side"], 95)
        self.assertTrue(value["qa"]["m1"]["exact_bid_ask_timestamp_set"])
        self.assertFalse(value["qa"]["post_target_context"]["repair_performed"])
        self.assertEqual(
            value["qa"]["post_target_context"]["downstream_policy"],
            "INCOMPLETE_REQUIRED_MEMBERSHIP_NOT_EVALUABLE_NO_BRIDGING",
        )

    def test_external_bytes_are_bound_but_not_committed(self) -> None:
        value = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertFalse(value["external_evidence"]["raw_provider_bytes_in_git"])
        self.assertFalse(value["external_evidence"]["source_csvs_in_git"])
        self.assertEqual(len(value["compact_files"]), 8)
        self.assertEqual(len(value["source_objects"]), 4)
        self.assertEqual(
            value["qa"]["source_object_byte_verification"],
            "PASS_4_OF_4_EXACT_SHA256_AND_SIZE",
        )


if __name__ == "__main__":
    unittest.main()
