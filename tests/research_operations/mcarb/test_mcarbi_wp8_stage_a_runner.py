from __future__ import annotations

from decimal import Decimal
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/research_operations/run_mcarbi_stage_a.py"
spec = importlib.util.spec_from_file_location("mcarbi_stage_a_runner", SCRIPT)
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

from ovc.research_operations.mcarb.intrinsic_time import directional_change, variation_clock
from ovc.research_operations.mcarb.models import PriceBar


class MCARBIWP8StageARunnerTest(unittest.TestCase):
    def _bars(self):
        closes = ["1.0000", "1.0012", "1.0004", "1.0025", "1.0010"]
        rows = []
        prices = []
        for index, close in enumerate(closes):
            start_ms = index * runner.CLOCK_MS
            value = Decimal(close)
            rows.append(
                {
                    "side": "BID",
                    "timestamp_ms": start_ms,
                    "start": runner.iso_ms(start_ms),
                    "end": runner.iso_ms(start_ms + runner.CLOCK_MS),
                    "open": value,
                    "high": value + Decimal("0.0005"),
                    "low": value - Decimal("0.0005"),
                    "close": value,
                    "volume": Decimal("100") + index,
                    "source_path": "canonical/2H_A_L/BID/test.csv",
                    "object_id": f"bar-{index}",
                    "slot": runner.slot_id(start_ms),
                }
            )
            prices.append(
                PriceBar(
                    object_id=f"bar-{index}",
                    side="BID",
                    start_utc=runner.iso_ms(start_ms),
                    end_utc=runner.iso_ms(start_ms + runner.CLOCK_MS),
                    open=value,
                    high=value + Decimal("0.0005"),
                    low=value - Decimal("0.0005"),
                    close=value,
                    volume=Decimal("100") + index,
                )
            )
        return rows, prices

    def test_directional_change_matches_registered_engine_event_times(self):
        rows, prices = self._bars()
        threshold = Decimal("0.0010")
        actual = runner.directional_change_counts(rows, threshold)
        expected = {row["timestamp_ms"]: 0 for row in rows}
        by_end = {row["end"]: row["timestamp_ms"] for row in rows}
        for event in directional_change(prices, threshold, variant_id="ET-DC.abs-close.2H.v1"):
            expected[by_end[event.interval_end]] = 1
        self.assertEqual(actual, expected)

    def test_variation_clock_matches_registered_engine_event_times(self):
        rows, prices = self._bars()
        target = Decimal("0.0020")
        actual = runner.variation_counts(rows, target)
        expected = {row["timestamp_ms"]: 0 for row in rows}
        by_end = {row["end"]: row["timestamp_ms"] for row in rows}
        for event in variation_clock(prices, target, variant_id="ET-VAR.abs-close.2H.reset-zero.v1"):
            expected[by_end[event.interval_end]] = 1
        self.assertEqual(actual, expected)

    def test_decimal_lattice_crossing_predicate_is_exact(self):
        self.assertEqual(
            runner.lattice_crossing_count(
                Decimal("1.0049"), Decimal("1.0151"), Decimal("0.0050"), Decimal("0.5000"), Decimal("2.0000")
            ),
            3,
        )
        self.assertEqual(
            runner.lattice_crossing_count(
                Decimal("1.0151"), Decimal("1.0049"), Decimal("0.0050"), Decimal("0.5000"), Decimal("2.0000")
            ),
            3,
        )
        self.assertEqual(
            runner.lattice_crossing_count(
                Decimal("1.0050"), Decimal("1.0100"), Decimal("0.0050"), Decimal("0.5000"), Decimal("2.0000")
            ),
            1,
        )

    def test_source_bar_identity_matches_opt_a_contract(self):
        value = runner.source_bar_id(
            "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
            "canonical/2H_A_L/BID/GBPUSD_2H_A_L_BID_2023-11_UTC.csv",
            1698796800000,
        )
        self.assertEqual(
            value,
            "opt-a:177b214a161fd9717cf66727d3810c2c2c0886dc408d19f2941598b618b36755",
        )

    def test_gzip_jsonl_is_byte_deterministic(self):
        records = [{"b": 2, "a": 1}, {"a": 3}]
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.gz"
            second = Path(tmp) / "b.gz"
            one = runner.write_gzip_jsonl(first, records)
            two = runner.write_gzip_jsonl(second, records)
            self.assertEqual(one["sha256"], two["sha256"])
            self.assertEqual(one["logical_sha256"], two["logical_sha256"])
            with gzip.open(first, "rt") as handle:
                self.assertEqual([json.loads(line) for line in handle], records)

    def test_controls_are_deterministic_and_do_not_impute_missing(self):
        records = [
            {"record_id": "r1", "side": "BID", "slot": "A", "r0_signature": "s", "fields": {"x": "1"}},
            {"record_id": "r2", "side": "BID", "slot": "A", "r0_signature": "s", "fields": {"x": None}},
            {"record_id": "r3", "side": "BID", "slot": "A", "r0_signature": "s", "fields": {"x": "3"}},
        ]
        self.assertEqual(runner.deterministic_shuffle(records, "x"), runner.deterministic_shuffle(records, "x"))
        self.assertEqual(runner.deterministic_noise(records, "x"), runner.deterministic_noise(records, "x"))
        self.assertNotIn("r2", runner.deterministic_shuffle(records, "x"))
        self.assertNotIn("r2", runner.deterministic_noise(records, "x"))

    def test_pack_surface_contains_r4x_and_no_hidden_catalogue_fields(self):
        self.assertEqual(runner.PACKS["R4X"], runner.PRICE_FIELDS + runner.AL_FIELDS + runner.ET_FIELDS)
        self.assertEqual(runner.PACKS["R6"], runner.PRICE_FIELDS + runner.AL_FIELDS + runner.ET_FIELDS + runner.VS_FIELDS)
        self.assertNotIn("AL-10", runner.AL_FIELDS)
        self.assertNotIn("AL-11", runner.AL_FIELDS)


if __name__ == "__main__":
    unittest.main()
