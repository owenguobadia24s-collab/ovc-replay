from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest

from ovc_opt_b import (
    assess_15m_path_coverage,
    context_quality,
    event_direction,
    expected_15m_open_times,
    measure_neutral_path,
    persistent_trigger_kind,
)


class OptCContractTests(unittest.TestCase):
    def test_event_direction_preserves_compound_opposition(self) -> None:
        self.assertEqual(event_direction([{"direction": "UP"}, {"direction": "DOWN"}]), "MIXED")

    def test_event_direction_ignores_non_directional_components(self) -> None:
        self.assertEqual(event_direction([{"direction": "NONE"}, {"direction": "UP"}]), "UP")

    def test_persistent_trigger_kinds(self) -> None:
        self.assertEqual(persistent_trigger_kind("NONE", "DISPLACING_UP", "NONE"), "ONSET")
        self.assertEqual(persistent_trigger_kind("DISPLACING_UP", "DISPLACING_UP", "NONE"), "REFRESH")
        self.assertEqual(persistent_trigger_kind("DISPLACING_UP", "DISPLACING_DOWN", "NONE"), "DIRECTION_CHANGE")
        self.assertEqual(persistent_trigger_kind("DISPLACING_UP", "NONE", "NONE"), "EXIT")

    def test_context_quality_rejects_future_context(self) -> None:
        anchor = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            context_quality(anchor, datetime(2026, 1, 1, 14, tzinfo=timezone.utc), maximum_age_minutes=120)

    def test_context_quality_marks_gap_stale(self) -> None:
        anchor = datetime(2026, 1, 5, 8, tzinfo=timezone.utc)
        context = datetime(2026, 1, 2, 22, tzinfo=timezone.utc)
        self.assertEqual(context_quality(anchor, context, maximum_age_minutes=120), "STALE_AFTER_GAP")

    def test_exact_one_hour_path_requires_four_bars(self) -> None:
        anchor = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        expected = expected_15m_open_times(anchor, 1)
        bars = {at: f"bar-{index}" for index, at in enumerate(expected)}
        result = assess_15m_path_coverage(
            anchor,
            1,
            bar_ids_by_open_time=bars,
            source_last_close_time=datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
        )
        self.assertEqual(result.coverage_status, "COMPLETE")
        self.assertEqual(result.expected_bar_count, 4)
        self.assertIsNotNone(result.path_bar_ids_hash)

    def test_internal_gap_censors_without_repair(self) -> None:
        anchor = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        expected = expected_15m_open_times(anchor, 1)
        bars = {at: f"bar-{index}" for index, at in enumerate(expected) if index != 2}
        result = assess_15m_path_coverage(
            anchor,
            1,
            bar_ids_by_open_time=bars,
            source_last_close_time=datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
        )
        self.assertEqual(result.coverage_status, "CENSORED")
        self.assertIn("INTERNAL_INTERVALS_MISSING", result.censor_reasons)
        self.assertEqual(result.missing_interval_count, 1)
        self.assertIsNone(result.path_bar_ids_hash)

    def test_source_end_truncation_is_explicit(self) -> None:
        anchor = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        expected = expected_15m_open_times(anchor, 2)
        bars = {at: f"bar-{index}" for index, at in enumerate(expected[:4])}
        result = assess_15m_path_coverage(
            anchor,
            2,
            bar_ids_by_open_time=bars,
            source_last_close_time=datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
        )
        self.assertIn("SOURCE_END_TRUNCATION", result.censor_reasons)
        self.assertEqual(result.max_missing_run_bars, 4)

    def test_upward_neutral_measurement_and_frontier_loss(self) -> None:
        anchor = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        bars = [
            SimpleNamespace(
                high=Decimal("1.1010"), low=Decimal("1.0995"), close=Decimal("1.1005"),
                close_time=datetime(2026, 1, 1, 12, 15, tzinfo=timezone.utc),
            ),
            SimpleNamespace(
                high=Decimal("1.1020"), low=Decimal("1.0980"), close=Decimal("1.0985"),
                close_time=datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc),
            ),
        ]
        result = measure_neutral_path(
            anchor_time=anchor,
            anchor_price=Decimal("1.1000"),
            event_direction_value="UP",
            event_bar_high=Decimal("1.1015"),
            event_bar_low=Decimal("1.0990"),
            path_bars=bars,
            frontier_summary={"accepted_floor_price": "1.0990", "accepted_ceiling_price": None},
        )
        self.assertEqual(result["raw_return_pips"], "-15")
        self.assertEqual(result["direction_normalized_favorable_excursion_pips"], "20")
        self.assertTrue(result["continued_beyond_event_extreme"])
        self.assertTrue(result["primary_frontier_lost_on_close"])

    def test_downward_normalization_inverts_endpoint_return(self) -> None:
        anchor = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        bars = [
            SimpleNamespace(
                high=Decimal("1.1005"), low=Decimal("1.0980"), close=Decimal("1.0990"),
                close_time=datetime(2026, 1, 1, 12, 15, tzinfo=timezone.utc),
            )
        ]
        result = measure_neutral_path(
            anchor_time=anchor,
            anchor_price=Decimal("1.1000"),
            event_direction_value="DOWN",
            event_bar_high=Decimal("1.1010"),
            event_bar_low=Decimal("1.0985"),
            path_bars=bars,
            frontier_summary={"accepted_floor_price": None, "accepted_ceiling_price": "1.1010"},
        )
        self.assertEqual(result["raw_return_pips"], "-10")
        self.assertEqual(result["direction_normalized_endpoint_return_pips"], "10")
        self.assertTrue(result["continued_beyond_event_extreme"])

    def test_mixed_direction_has_no_direction_normalized_measurement(self) -> None:
        anchor = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        bars = [
            SimpleNamespace(
                high=Decimal("1.1010"), low=Decimal("1.0990"), close=Decimal("1.1000"),
                close_time=datetime(2026, 1, 1, 12, 15, tzinfo=timezone.utc),
            )
        ]
        result = measure_neutral_path(
            anchor_time=anchor,
            anchor_price=Decimal("1.1000"),
            event_direction_value="MIXED",
            event_bar_high=Decimal("1.1010"),
            event_bar_low=Decimal("1.0990"),
            path_bars=bars,
            frontier_summary={},
        )
        self.assertEqual(result["direction_normalization_status"], "NOT_DIRECTIONAL")
        self.assertIsNone(result["direction_normalized_endpoint_return_pips"])

    def test_directional_event_without_matching_frontier_has_no_primary_frontier(self) -> None:
        anchor = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        bars = [
            SimpleNamespace(
                high=Decimal("1.1010"), low=Decimal("1.0995"), close=Decimal("1.1005"),
                close_time=datetime(2026, 1, 1, 12, 15, tzinfo=timezone.utc),
            )
        ]
        result = measure_neutral_path(
            anchor_time=anchor,
            anchor_price=Decimal("1.1000"),
            event_direction_value="UP",
            event_bar_high=Decimal("1.1015"),
            event_bar_low=Decimal("1.0990"),
            path_bars=bars,
            frontier_summary={"accepted_floor_price": None, "accepted_ceiling_price": "1.1020"},
        )
        self.assertIsNone(result["primary_frontier_type"])
        self.assertIsNone(result["primary_frontier_retested"])
        self.assertIsNone(result["directional_reversal_through_frontier"])


if __name__ == "__main__":
    unittest.main()
