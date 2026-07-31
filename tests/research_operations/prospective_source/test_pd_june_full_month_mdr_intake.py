from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from ovc.research_operations.prospective_source import dukascopy_full_month_mdr as subject


class PDJuneFullMonthMDRIntakeTests(unittest.TestCase):
    def test_provider_request_plan_is_exact_and_bounded(self) -> None:
        plan = subject.provider_request_plan()
        self.assertEqual(plan["gate"], "PD-JUNE-FM-G1")
        self.assertEqual(
            plan["slice_id"],
            "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1",
        )
        self.assertEqual(plan["provider_object_count"], 72)
        m1_bid = [item for item in plan["objects"] if item["logical_stream"] == "M1_BID"]
        h1_ask = [item for item in plan["objects"] if item["logical_stream"] == "H1_ASK"]
        self.assertEqual(len(m1_bid), 34)
        self.assertEqual(len(h1_ask), 2)
        self.assertEqual(m1_bid[0]["partition_start_utc"], "2026-05-30T00:00:00Z")
        self.assertEqual(m1_bid[-1]["partition_start_utc"], "2026-07-02T00:00:00Z")
        self.assertEqual(
            [item["partition_start_utc"] for item in h1_ask],
            ["2026-05-01T00:00:00Z", "2026-06-01T00:00:00Z"],
        )
        self.assertFalse(
            any(
                item["relative_provider_path"].endswith("2026/06/ASK_candles_hour_1.bi5")
                for item in plan["objects"]
            )
        )
        self.assertEqual(
            plan["native_july_h1_transport"],
            "WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE",
        )
        self.assertEqual(
            plan["post_target_h1_context"],
            "M1_DERIVED_FROM_COMPLETE_JULY_CONTEXT_BARS",
        )
        self.assertEqual(plan["provider_execution_in_ci"], "DENIED")

    def test_preflight_uses_only_external_artifact_root(self) -> None:
        with tempfile.TemporaryDirectory() as repository, tempfile.TemporaryDirectory() as external:
            result = subject.preflight(
                repository_root=Path(repository),
                environ={"OVC_EXTERNAL_ARTIFACT_ROOT": external},
            )
            self.assertEqual(result["status"], "READY_FOR_OPERATOR_LOCAL_EXECUTION")
            self.assertEqual(result["provider_object_count"], 72)
            self.assertFalse(result["provider_network_access_performed"])
            self.assertEqual(result["provider_execution_location"], "OPERATOR_LOCAL_ONLY")
            self.assertEqual(
                result["native_july_h1_transport"],
                "WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE",
            )

    def test_preflight_refuses_existing_material(self) -> None:
        with tempfile.TemporaryDirectory() as repository, tempfile.TemporaryDirectory() as external:
            destination = Path(external) / "prospective-source" / "intake" / subject.APPROVED_SLICE_ID
            destination.mkdir(parents=True)
            (destination / "existing.txt").write_text("do not overwrite", encoding="utf-8")
            with self.assertRaisesRegex(subject.IntakeError, "already contains material"):
                subject.preflight(
                    repository_root=Path(repository),
                    environ={"OVC_EXTERNAL_ARTIFACT_ROOT": external},
                )

    def test_execute_requires_exact_gate_and_operator_local_context(self) -> None:
        with tempfile.TemporaryDirectory() as repository, tempfile.TemporaryDirectory() as external:
            with self.assertRaisesRegex(subject.IntakeError, "exact operator approval"):
                subject.execute_intake(
                    repository_root=Path(repository),
                    gate="WRONG-GATE",
                    environ={"OVC_EXTERNAL_ARTIFACT_ROOT": external},
                )
            with self.assertRaisesRegex(subject.IntakeError, "prohibited in CI"):
                subject.execute_intake(
                    repository_root=Path(repository),
                    gate="PD-JUNE-FM-G1",
                    environ={"OVC_EXTERNAL_ARTIFACT_ROOT": external, "CI": "true"},
                )

    @staticmethod
    def _row(timestamp: datetime) -> subject.CandleRow:
        return subject.CandleRow(
            timestamp_utc=timestamp,
            open=Decimal("1.25000"),
            high=Decimal("1.25100"),
            low=Decimal("1.24900"),
            close=Decimal("1.25050"),
            volume=Decimal("1"),
        )

    def _weekday_h1_rows(self) -> list[subject.CandleRow]:
        rows: list[subject.CandleRow] = []
        cursor = subject.APPROVED_START
        while cursor < subject.APPROVED_END:
            if cursor.weekday() < 5:
                rows.append(self._row(cursor))
            cursor += timedelta(hours=1)
        return rows

    def test_coverage_accepts_explicit_weekend_boundaries_and_gaps(self) -> None:
        rows = self._weekday_h1_rows()
        audit = subject._coverage_audit(rows, clock="H1", side="BID")
        self.assertEqual(audit["qa_state"], "PASS")
        self.assertTrue(audit["start_boundary_accepted"])
        self.assertTrue(audit["end_boundary_accepted"])
        self.assertGreater(len(audit["weekend_spanning_discontinuities"]), 0)
        self.assertEqual(audit["unexpected_intra_session_gaps"], [])

    def test_coverage_blocks_unrecorded_intra_session_gap(self) -> None:
        rows = self._weekday_h1_rows()
        missing = datetime(2026, 6, 10, 12, tzinfo=timezone.utc)
        rows = [row for row in rows if row.timestamp_utc != missing]
        audit = subject._coverage_audit(rows, clock="H1", side="ASK")
        self.assertEqual(audit["qa_state"], "BLOCK")
        self.assertEqual(len(audit["unexpected_intra_session_gaps"]), 1)

    def test_post_target_h1_is_derived_from_complete_july_m1_context(self) -> None:
        rows: list[subject.CandleRow] = []
        cursor = subject.TARGET_END
        while cursor < subject.APPROVED_END:
            rows.append(self._row(cursor))
            cursor += timedelta(minutes=1)
        derived, audit = subject._post_target_h1_audit(rows, side="BID")
        self.assertEqual(audit["qa_state"], "PASS")
        self.assertEqual(audit["expected_complete_hour_count"], 48)
        self.assertEqual(audit["derived_complete_hour_count"], 48)
        self.assertEqual(len(derived), 48)
        self.assertEqual(derived[0].timestamp_utc, subject.TARGET_END)
        self.assertEqual(derived[-1].timestamp_utc, subject.APPROVED_END - timedelta(hours=1))


if __name__ == "__main__":
    unittest.main()
