from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc_opt_b import aggregate_bars, read_dukascopy_csv


class DukascopyAdapterTests(unittest.TestCase):
    def _csv(self, path: Path, count: int, *, skip: int | None = None) -> None:
        lines = ["Local time,Open,High,Low,Close,Volume"]
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        for index in range(count):
            if index == skip:
                continue
            stamp = (start + timedelta(minutes=index)).strftime("%d.%m.%Y %H:%M:%S.%f")[:-3]
            lines.append(f"{stamp},1.25000,1.25020,1.24980,1.25010,10")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_read_and_aggregate_complete_15m_bucket(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "GBPUSD.csv"
            self._csv(path, 15)
            raw = read_dukascopy_csv(path, source_release_id="fixture-1")
            result = aggregate_bars(raw, target_timeframe="15M")
        self.assertEqual(len(raw), 15)
        self.assertEqual(len(result.accepted), 1)
        self.assertEqual(len(result.rejected), 0)
        self.assertEqual(result.accepted[0].open, Decimal("1.25000"))
        self.assertEqual(result.accepted[0].price_side, "BID")

    def test_incomplete_bucket_is_rejected_not_filled(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "GBPUSD.csv"
            self._csv(path, 15, skip=7)
            raw = read_dukascopy_csv(path, source_release_id="fixture-2")
            result = aggregate_bars(raw, target_timeframe="15M")
        self.assertEqual(len(result.accepted), 0)
        self.assertEqual(result.rejected[0].reason, "INCOMPLETE_OR_MISALIGNED_BUCKET")

    def test_15m_to_fixed_utc_2h(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "GBPUSD.csv"
            self._csv(path, 120)
            raw = read_dukascopy_csv(path, source_release_id="fixture-3")
            fifteen = aggregate_bars(raw, target_timeframe="15M")
            two_hour = aggregate_bars(fifteen.accepted, target_timeframe="2H")
        self.assertEqual(len(fifteen.accepted), 8)
        self.assertEqual(len(two_hour.accepted), 1)
        self.assertEqual(two_hour.accepted[0].open_time.hour, 0)
        self.assertEqual(two_hour.accepted[0].close_time.hour, 2)

    def test_csv_rejects_non_monotonic_time(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "GBPUSD.csv"
            path.write_text(
                "Local time,Open,High,Low,Close,Volume\n"
                "05.01.2026 00:00:00.000,1.2,1.3,1.1,1.2,1\n"
                "05.01.2026 00:00:00.000,1.2,1.3,1.1,1.2,1\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                read_dukascopy_csv(path, source_release_id="fixture-4")

    def test_offset_aware_europe_london_column_normalizes_to_utc(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "GBPUSD.csv"
            path.write_text(
                "Europe/London,Open,High,Low,Close,Volume\n"
                "2026-07-16T00:00:00+01:00,1.2,1.3,1.1,1.2,1\n",
                encoding="utf-8",
            )
            result = read_dukascopy_csv(path, source_release_id="fixture-5")
        self.assertEqual(result[0].open_time, datetime(2026, 7, 15, 23, 0, tzinfo=timezone.utc))

    def test_hourly_export_aggregates_to_2h(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "GBPUSD_1H.csv"
            path.write_text(
                "Etc/UTC,Open,High,Low,Close,Volume\n"
                "2026-01-05T00:00:00+00:00,1.20,1.22,1.19,1.21,1\n"
                "2026-01-05T01:00:00+00:00,1.21,1.23,1.20,1.22,1\n",
                encoding="utf-8",
            )
            hourly = read_dukascopy_csv(path, source_release_id="fixture-6", source_timeframe="1H")
            result = aggregate_bars(hourly, target_timeframe="2H")
        self.assertEqual(len(result.accepted), 1)
        self.assertEqual(result.accepted[0].open, Decimal("1.20"))
        self.assertEqual(result.accepted[0].close, Decimal("1.22"))
        self.assertEqual(result.accepted[0].timeframe, "2H")

    def test_epoch_millisecond_timestamp_from_direct_feed(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "GBPUSD_direct.csv"
            path.write_text(
                "timestamp,open,high,low,close,volume\n"
                "1767304800000,1.34643,1.34648,1.34643,1.34648,1800000\n",
                encoding="utf-8",
            )
            result = read_dukascopy_csv(path, source_release_id="fixture-7")
        self.assertEqual(result[0].open_time, datetime(2026, 1, 1, 22, 0, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
