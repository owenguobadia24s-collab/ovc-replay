from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from ovc.research_operations.prospective_source.aggregation import aggregate_m1
from ovc.research_operations.prospective_source.binding import (
    ACTIVE_C2_RELEASE,
    build_replay_binding,
    validate_non_activating,
)
from ovc.research_operations.prospective_source.cursor import advance_cursor, reconcile_cursor
from ovc.research_operations.prospective_source.models import SourceBar, manifest_hash
from ovc.research_operations.prospective_source.projection import build_c1_records, build_c2_records


def fixture_bars(count: int = 120, *, missing_index: int | None = None) -> list[SourceBar]:
    start = datetime(2026, 7, 20, tzinfo=timezone.utc)
    bars: list[SourceBar] = []
    for index in range(count):
        if index == missing_index:
            continue
        timestamp = start + timedelta(minutes=index)
        base = Decimal("1.2500") + Decimal(index) / Decimal("100000")
        bars.append(
            SourceBar(
                object_id=f"FIXTURE.M1.BID.{index:03d}",
                timestamp_utc=timestamp.isoformat().replace("+00:00", "Z"),
                side="BID",
                open=base,
                high=base + Decimal("0.0002"),
                low=base - Decimal("0.0002"),
                close=base + Decimal("0.0001"),
                volume=Decimal("1"),
            )
        )
    return bars


class FixturePipelineTests(unittest.TestCase):
    cutoff = "2026-07-20T02:00:00Z"

    def test_two_runs_are_identical(self) -> None:
        source = fixture_bars()
        first = aggregate_m1(source, clock="15M", side="BID", admissible_cutoff_utc=self.cutoff)
        second = aggregate_m1(reversed(source), clock="15M", side="BID", admissible_cutoff_utc=self.cutoff)
        self.assertEqual(first, second)
        self.assertEqual(manifest_hash(first), manifest_hash(second))
        first_c2 = build_c2_records(build_c1_records(first), active_model_release_id=ACTIVE_C2_RELEASE)
        second_c2 = build_c2_records(build_c1_records(second), active_model_release_id=ACTIVE_C2_RELEASE)
        self.assertEqual(first_c2, second_c2)

    def test_exact_15m_and_2h_parent_counts(self) -> None:
        source = fixture_bars()
        bars_15m = aggregate_m1(source, clock="15M", side="BID", admissible_cutoff_utc=self.cutoff)
        bars_2h = aggregate_m1(source, clock="2H_A_L", side="BID", admissible_cutoff_utc=self.cutoff)
        self.assertEqual(len(bars_15m), 8)
        self.assertTrue(all(len(bar.parent_source_object_ids) == 15 for bar in bars_15m))
        self.assertEqual(len(bars_2h), 1)
        self.assertEqual(len(bars_2h[0].parent_source_object_ids), 120)

    def test_future_source_is_rejected(self) -> None:
        source = fixture_bars() + [
            SourceBar(
                object_id="FUTURE", timestamp_utc=self.cutoff, side="BID",
                open=Decimal("1"), high=Decimal("1"), low=Decimal("1"), close=Decimal("1"), volume=Decimal("1"),
            )
        ]
        with self.assertRaisesRegex(ValueError, "future source"):
            aggregate_m1(source, clock="15M", side="BID", admissible_cutoff_utc=self.cutoff)

    def test_missing_parent_quarantines_bucket(self) -> None:
        bars = aggregate_m1(fixture_bars(missing_index=7), clock="15M", side="BID", admissible_cutoff_utc=self.cutoff)
        self.assertEqual(bars[0].quality_state, "QUARANTINED_INCOMPLETE_PARENT_SET")
        self.assertIsNone(bars[0].close)

    def test_binding_is_non_activating(self) -> None:
        source_hash = "a" * 64
        binding = build_replay_binding(
            source_slice_id="RPS.DUKASCOPY.GBPUSD.FIXTURE.v1",
            source_manifest_sha256=source_hash,
            compute_run_id="RPS.RUN.FIXTURE",
            eligible_data_through_utc=self.cutoff,
            deterministic_replay=True,
            lineage_complete=True,
            gap_state="COMPLETE",
        )
        validate_non_activating(binding)
        self.assertEqual(binding.status, "ACCEPTED_FOR_REPLAY")
        self.assertEqual(binding.release_eligibility, "NONE")
        self.assertEqual(binding.selector_eligibility, "NONE")
        self.assertEqual(binding.r2_publication, "DENIED")
        self.assertIsNone(binding.active_triage_started_at_utc)

    def test_cursor_restart_is_idempotent(self) -> None:
        cursor = advance_cursor(None, source_slice_id="SLICE", interval_end_utc=self.cutoff, transition_id="T1")
        replay = advance_cursor(cursor, source_slice_id="SLICE", interval_end_utc=self.cutoff, transition_id="T1")
        self.assertEqual(cursor, replay)
        reconcile_cursor(replay, cursor.state_hash)
        with self.assertRaisesRegex(ValueError, "state hash"):
            reconcile_cursor(replay, "0" * 64)

    def test_c2_rows_never_join_historical_release(self) -> None:
        bars = aggregate_m1(fixture_bars(), clock="15M", side="BID", admissible_cutoff_utc=self.cutoff)
        rows = build_c2_records(build_c1_records(bars), active_model_release_id=ACTIVE_C2_RELEASE)
        self.assertTrue(rows)
        self.assertTrue(all(row["historical_release_membership"] is False for row in rows))
        self.assertTrue(all(row["operation_mode"] == "TIME_GATED_REPLAY" for row in rows))


if __name__ == "__main__":
    unittest.main()
