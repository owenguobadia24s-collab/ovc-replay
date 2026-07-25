from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from ovc_opt_b import (
    Bar,
    build_level_registry,
    confirmed_swings,
    eligible_levels,
    rolling_range_boundaries,
)


D = Decimal
START = datetime(2026, 1, 5, tzinfo=timezone.utc)


def bar(index: int, high: str, low: str, *, gap: int = 0) -> Bar:
    open_time = START + timedelta(minutes=15 * (index + gap))
    return Bar(
        bar_id=f"r{index:03d}:{gap}",
        instrument_id="GBPUSD",
        timeframe="15M",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=15),
        open=D("100"),
        high=D(high),
        low=D(low),
        close=D("100"),
        price_increment=D("0.01"),
        source_release_id="sealed-a",
    )


class LevelRegistryTests(unittest.TestCase):
    def test_strict_swing_high_is_known_after_two_right_bars(self) -> None:
        bars = [
            bar(0, "101", "99"),
            bar(1, "102", "98"),
            bar(2, "105", "97"),
            bar(3, "103", "98"),
            bar(4, "102", "99"),
        ]
        levels = confirmed_swings(bars)
        high = next(level for level in levels if level.level_type == "PRIOR_SWING_HIGH")
        self.assertEqual(high.price, D("105"))
        self.assertEqual(high.created_at, bars[2].close_time)
        self.assertEqual(high.first_valid_time, bars[4].close_time)
        self.assertEqual(high.source_bar_ids, tuple(b.bar_id for b in bars))

    def test_equal_high_tie_does_not_create_swing(self) -> None:
        bars = [
            bar(0, "101", "99"),
            bar(1, "105", "98"),
            bar(2, "105", "97"),
            bar(3, "103", "98"),
            bar(4, "102", "99"),
        ]
        levels = confirmed_swings(bars)
        self.assertFalse(any(level.level_type == "PRIOR_SWING_HIGH" for level in levels))

    def test_gap_prevents_cross_gap_swing(self) -> None:
        before = [bar(i, str(101 + i), str(99 - i)) for i in range(2)]
        after = [bar(i + 2, str(105 - i), str(97 + i), gap=1) for i in range(3)]
        self.assertEqual(confirmed_swings(before + after), ())

    def test_rolling_range_emits_only_when_boundary_changes(self) -> None:
        bars = [bar(i, "101", "99") for i in range(9)]
        levels = rolling_range_boundaries(bars)
        self.assertEqual(len(levels), 2)
        self.assertEqual({level.level_type for level in levels}, {"RANGE_HIGH", "RANGE_LOW"})

    def test_rolling_range_boundary_change_gets_new_id(self) -> None:
        bars = [bar(i, "101", "99") for i in range(8)]
        bars.append(bar(8, "102", "99"))
        highs = [level for level in rolling_range_boundaries(bars) if level.level_type == "RANGE_HIGH"]
        self.assertEqual([level.price for level in highs], [D("101"), D("102")])
        self.assertNotEqual(highs[0].level_id, highs[1].level_id)

    def test_registry_is_deterministic_and_future_stable(self) -> None:
        bars = [bar(i, str(101 + (i % 3)), str(99 - (i % 2))) for i in range(12)]
        first = build_level_registry(bars)
        second = build_level_registry(bars)
        self.assertEqual(first.registry_hash, second.registry_hash)
        self.assertEqual([x.level_id for x in first.levels], [x.level_id for x in second.levels])
        extended = build_level_registry(bars + [bar(12, "110", "90")])
        self.assertEqual(
            [x.level_id for x in first.levels],
            [x.level_id for x in extended.levels[: len(first.levels)]],
        )

    def test_eligible_levels_are_known_by_candidate_open(self) -> None:
        bars = [bar(i, "101", "99") for i in range(9)]
        registry = build_level_registry(bars[:8])
        self.assertEqual(eligible_levels(registry.levels, bars[7]), ())
        self.assertEqual(len(eligible_levels(registry.levels, bars[8])), 2)

    def test_reordered_input_is_rejected(self) -> None:
        bars = [bar(i, "101", "99") for i in range(8)]
        bars[2], bars[3] = bars[3], bars[2]
        with self.assertRaises(ValueError):
            build_level_registry(bars)


if __name__ == "__main__":
    unittest.main()
