from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from ovc_opt_b import (
    Bar,
    Direction,
    ReferenceLevel,
    State,
    TermStatus,
    acceptance,
    compression,
    displacement,
    reclaim,
    reference_level_breach_and_response,
    rejection,
    transition,
)


D = Decimal
START = datetime(2026, 1, 5, tzinfo=timezone.utc)


def bar(index: int, open_: str, high: str, low: str, close: str) -> Bar:
    return Bar(
        bar_id=f"b{index:03d}", instrument_id="GBPUSD", timeframe="15M",
        open_time=START + timedelta(minutes=15 * index),
        close_time=START + timedelta(minutes=15 * (index + 1)),
        open=D(open_), high=D(high), low=D(low), close=D(close), price_increment=D("0.01"),
    )


def baseline(count: int = 30, center: Decimal = D("100")) -> list[Bar]:
    result: list[Bar] = []
    for i in range(count):
        close = center + (D("0.1") if i % 2 else D("-0.1"))
        result.append(bar(i, str(center), str(center + D("0.5")), str(center - D("0.5")), str(close)))
    return result


def level(price: str = "100") -> ReferenceLevel:
    return ReferenceLevel(
        level_id="L1", level_type="RANGE_HIGH", price=D(price),
        created_at=START - timedelta(hours=2), first_valid_time=START - timedelta(hours=1),
    )


class ContractTests(unittest.TestCase):
    def test_compression_confirms(self) -> None:
        bars = baseline(21)
        for i in range(21, 29):
            close = D("100.03") if i % 2 else D("99.97")
            bars.append(bar(i, "100", "100.20", "99.80", str(close)))
        record = compression(bars, 28)
        self.assertEqual(record.status, TermStatus.CONFIRMED)
        self.assertEqual(record.first_valid_time, bars[28].close_time)

    def test_displacement_confirms_up_and_is_deterministic(self) -> None:
        bars = baseline(21)
        bars.append(bar(21, "100", "101.60", "99.95", "101.50"))
        first = displacement(bars, 21)
        second = displacement(bars, 21)
        self.assertEqual(first.status, TermStatus.CONFIRMED)
        self.assertEqual(first.direction, Direction.UP)
        self.assertEqual(first.term_record_id, second.term_record_id)

    def test_displacement_directional_symmetry(self) -> None:
        bars = baseline(21)
        bars.append(bar(21, "100", "100.05", "98.40", "98.50"))
        record = displacement(bars, 21)
        self.assertEqual(record.status, TermStatus.CONFIRMED)
        self.assertEqual(record.direction, Direction.DOWN)

    def test_future_bar_does_not_change_closed_displacement(self) -> None:
        bars = baseline(21)
        bars.append(bar(21, "100", "101.60", "99.95", "101.50"))
        before = displacement(bars, 21)
        bars.append(bar(22, "101.5", "105", "95", "96"))
        after = displacement(bars, 21)
        self.assertEqual(before.term_record_id, after.term_record_id)
        self.assertEqual(before.measurements, after.measurements)

    def test_breach_and_response_confirms_without_stop_claim(self) -> None:
        bars = baseline(21)
        bars.extend([
            bar(21, "99.8", "100.30", "99.7", "100.10"),
            bar(22, "100.1", "100.15", "99.70", "99.80"),
        ])
        record = reference_level_breach_and_response(bars, 21, level(), Direction.UP)
        self.assertEqual(record.status, TermStatus.CONFIRMED)
        self.assertEqual(record.first_valid_time, bars[22].close_time)

    def test_incomplete_breach_response_is_pending(self) -> None:
        bars = baseline(21)
        bars.append(bar(21, "99.8", "100.30", "99.7", "100.10"))
        record = reference_level_breach_and_response(bars, 21, level(), Direction.UP)
        self.assertEqual(record.status, TermStatus.PENDING)

    def test_reclaim_requires_two_confirming_closes(self) -> None:
        bars = baseline(21)
        bars[20] = bar(20, "99.8", "99.9", "99.5", "99.6")
        bars.extend([
            bar(21, "99.8", "100.4", "99.7", "100.2"),
            bar(22, "100.2", "100.5", "100.1", "100.3"),
        ])
        record = reclaim(bars, 21, level(), Direction.UP)
        self.assertEqual(record.status, TermStatus.CONFIRMED)
        self.assertEqual(record.first_valid_time, bars[22].close_time)

    def test_acceptance_above_confirms(self) -> None:
        bars = baseline(21)
        bars.extend([
            bar(21, "100.0", "100.3", "99.9", "100.2"),
            bar(22, "100.2", "100.4", "100.0", "100.3"),
            bar(23, "100.3", "100.5", "100.1", "100.4"),
            bar(24, "100.4", "100.5", "100.1", "100.3"),
        ])
        record = acceptance(bars, 24, level(), Direction.UP)
        self.assertEqual(record.status, TermStatus.CONFIRMED)

    def test_acceptance_below_confirms_symmetrically(self) -> None:
        bars = baseline(21)
        bars.extend([
            bar(21, "100.0", "100.1", "99.7", "99.8"),
            bar(22, "99.8", "100.0", "99.6", "99.7"),
            bar(23, "99.7", "99.9", "99.5", "99.6"),
            bar(24, "99.6", "99.9", "99.5", "99.7"),
        ])
        record = acceptance(bars, 24, level(), Direction.DOWN)
        self.assertEqual(record.status, TermStatus.CONFIRMED)

    def test_rejection_down_confirms(self) -> None:
        bars = baseline(21)
        bars.extend([
            bar(21, "99.8", "100.10", "99.7", "99.9"),
            bar(22, "99.9", "99.95", "99.3", "99.4"),
        ])
        record = rejection(bars, 21, level(), Direction.DOWN)
        self.assertEqual(record.status, TermStatus.CONFIRMED)
        self.assertEqual(record.first_valid_time, bars[22].close_time)

    def test_transition_requires_stable_prior_state(self) -> None:
        bars = baseline(21)
        bars.append(bar(21, "100", "101.60", "99.95", "101.50"))
        trigger = displacement(bars, 21)
        record = transition([State.COMPRESSED.value, State.COMPRESSED.value], State.DISPLACING_UP.value, trigger)
        self.assertEqual(record.status, TermStatus.CONFIRMED)
        self.assertEqual(record.measurements["from_state"], State.COMPRESSED.value)

    def test_transition_fails_when_prior_state_is_not_stable(self) -> None:
        bars = baseline(21)
        bars.append(bar(21, "100", "101.60", "99.95", "101.50"))
        trigger = displacement(bars, 21)
        record = transition([State.NEUTRAL.value, State.COMPRESSED.value], State.DISPLACING_UP.value, trigger)
        self.assertEqual(record.status, TermStatus.FAILED)
        self.assertIn("PREVIOUS_STATE_NOT_STABLE", record.reason_codes)

    def test_level_must_preexist_candidate(self) -> None:
        bars = baseline(25)
        future_level = ReferenceLevel(
            level_id="future", level_type="RANGE_HIGH", price=D("100"),
            created_at=bars[21].open_time, first_valid_time=bars[21].close_time,
        )
        with self.assertRaises(ValueError):
            acceptance(bars, 24, future_level, Direction.UP)

    def test_bar_rejects_invalid_ohlc(self) -> None:
        with self.assertRaises(ValueError):
            bar(0, "100", "99", "98", "100")

    def test_classifier_rejects_reordered_bars(self) -> None:
        bars = baseline(21)
        bars.append(bar(21, "100", "101.60", "99.95", "101.50"))
        bars[19], bars[20] = bars[20], bars[19]
        with self.assertRaises(ValueError):
            displacement(bars, 21)


if __name__ == "__main__":
    unittest.main()
