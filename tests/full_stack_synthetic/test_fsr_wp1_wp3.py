from __future__ import annotations

import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from ovc.opt_a.fsr_synthetic import (
    EXPECTED_SOURCE_SHA256,
    build_opt_a_fixture,
    c1_handoff_records,
)
from ovc.opt_b.c1.builder import build as build_c1

REPO_ROOT = Path(__file__).resolve().parents[2]
HIDDEN_LABELS = (
    "quiet_low_range_persistence",
    "compression",
    "directional_expansion",
    "impulsive_displacement",
    "pullback_retracement",
    "range_construction",
    "repeated_level_interaction",
    "clean_level_crossing",
    "failed_crossing_like_price_behaviour",
    "reversal",
    "continuation",
    "alternating_rotational_behaviour",
    "residual_outlier_candidate",
)


def _c1_stream(handoff: list[dict]) -> list[dict]:
    output: list[dict] = []
    for clock in ("15M", "2H_A_L"):
        for side in ("BID", "ASK"):
            group = sorted(
                (item for item in handoff if item["clock_id"] == clock and item["price_side"] == side),
                key=lambda item: item["open_time"],
            )
            prior = None
            for current in group:
                result = build_c1(current, prior)
                output.append(dataclasses.asdict(result))
                prior = current
    return output


class FSRWP1WP3Tests(unittest.TestCase):
    def test_deterministic_fresh_source_opt_a_and_c1(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            tmp_path = Path(root)
            first = build_opt_a_fixture(tmp_path / "run1", repo_root=REPO_ROOT)
            second = build_opt_a_fixture(tmp_path / "run2", repo_root=REPO_ROOT)

            self.assertEqual(first["fixture_id"], second["fixture_id"])
            self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
            self.assertIs(first["SYNTHETIC"], True)
            self.assertIs(first["MARKET_EVIDENCE"], False)
            self.assertIs(first["CANONICAL"], False)
            self.assertIs(first["PROMOTABLE"], False)
            self.assertEqual(first["authority"]["validation"], "LOCKED_UNCONSUMED")
            self.assertEqual(first["authority"]["selector"], "NONE")
            self.assertEqual(first["authority"]["publication"], "NONE")

            source_hashes = {item["name"]: item["sha256"] for item in first["source_inventory"]}
            self.assertEqual(source_hashes, EXPECTED_SOURCE_SHA256)
            source_counts = {item["name"]: item["row_count"] for item in first["source_inventory"]}
            self.assertEqual(
                source_counts,
                {
                    "GBPUSD_M1_BID_2023-06_FSR.csv": 1435,
                    "GBPUSD_M1_ASK_2023-06_FSR.csv": 1435,
                    "GBPUSD_H1_BID_2023-06_FSR.csv": 24,
                    "GBPUSD_H1_ASK_2023-06_FSR.csv": 24,
                },
            )

            clock_counts: dict[tuple[str, str], int] = {}
            for row in first["observations"]:
                key = (row["clock_id"], row["price_side"])
                clock_counts[key] = clock_counts.get(key, 0) + 1
                self.assertEqual(row["first_valid_time"], row["close_time"])
                self.assertIs(row["synthetic"], True)
                self.assertEqual(row["authority"], "FIXTURE_ONLY")
            self.assertEqual(
                clock_counts,
                {
                    ("M1", "BID"): 1435,
                    ("M1", "ASK"): 1435,
                    ("H1_PROVIDER_NATIVE", "BID"): 24,
                    ("H1_PROVIDER_NATIVE", "ASK"): 24,
                    ("15M", "BID"): 95,
                    ("15M", "ASK"): 95,
                    ("H1_M1_DERIVED", "BID"): 23,
                    ("H1_M1_DERIVED", "ASK"): 23,
                    ("2H_A_L", "BID"): 11,
                    ("2H_A_L", "ASK"): 11,
                },
            )
            self.assertEqual(len(first["quarantine"]), 6)
            self.assertEqual(
                {(item["clock"], item["price_side"]) for item in first["quarantine"]},
                {
                    ("15M", "BID"), ("15M", "ASK"),
                    ("H1_M1_DERIVED", "BID"), ("H1_M1_DERIVED", "ASK"),
                    ("2H_A_L", "BID"), ("2H_A_L", "ASK"),
                },
            )
            self.assertTrue(all(item["repair"] == "DENIED" for item in first["quarantine"]))
            self.assertTrue(
                all(item["reason"] == "INCOMPLETE_OR_NONCONTIGUOUS_M1_BUCKET" for item in first["quarantine"])
            )

            serialized = json.dumps(first, sort_keys=True)
            self.assertTrue(all(label not in serialized for label in HIDDEN_LABELS))

            handoff = c1_handoff_records(first)
            self.assertEqual(len(handoff), 212)
            self.assertTrue(all(item["synthetic"] is True for item in handoff))
            self.assertTrue(all(item["selector_state"] == "NONE" for item in handoff))
            self.assertTrue(all(item["validation_consumption_state"] == "DENIED" for item in handoff))

            c1_first = _c1_stream(handoff)
            c1_second = _c1_stream(c1_handoff_records(second))
            self.assertEqual(c1_first, c1_second)
            self.assertEqual(len(c1_first), 212)
            self.assertEqual(len({item["record_id"] for item in c1_first}), 212)
            self.assertTrue(all(item["synthetic"] is True for item in c1_first))
            self.assertTrue(all(item["authority_state"] == "NONE" for item in c1_first))
            self.assertTrue(all(item["first_valid_time"] == item["close_time"] for item in c1_first))


if __name__ == "__main__":
    unittest.main()
