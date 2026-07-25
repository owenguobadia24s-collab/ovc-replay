from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from ovc_opt_b import Bar
from scripts.build_opt_a_validation_seal import gap_ledger


def bar(at: datetime) -> Bar:
    return Bar(
        bar_id=f"b:{at.isoformat()}", instrument_id="GBPUSD", timeframe="1M",
        open_time=at, close_time=at + timedelta(minutes=1),
        open=Decimal("1.2"), high=Decimal("1.2"), low=Decimal("1.2"), close=Decimal("1.2"),
        source_release_id="test",
    )


class OptAValidationSealTests(unittest.TestCase):
    def test_gap_ledger_conserves_boundaries_and_internal_absence(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(minutes=10)
        raw = (bar(start + timedelta(minutes=2)), bar(start + timedelta(minutes=5)))
        gaps = gap_ledger(raw, start=start, end=end)
        self.assertEqual(sum(item["missing_minutes"] for item in gaps), 8)
        self.assertEqual([item["position"] for item in gaps], ["LEFT_BOUNDARY", "INTERNAL", "RIGHT_BOUNDARY"])

    def test_six_hour_internal_gap_is_closure_like(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        raw = (bar(start), bar(start + timedelta(minutes=361)))
        gaps = gap_ledger(raw, start=start, end=start + timedelta(minutes=362))
        self.assertEqual(gaps[0]["missing_minutes"], 360)
        self.assertEqual(gaps[0]["classification"], "CLOSURE_LIKE")


if __name__ == "__main__":
    unittest.main()
