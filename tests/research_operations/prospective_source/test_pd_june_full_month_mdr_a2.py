from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from ovc.research_operations.prospective_source import (
    dukascopy_full_month_mdr_a2 as subject,
)


class PDJuneFullMonthMDRA2Tests(unittest.TestCase):
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

    def test_profile_and_plan_record_a2_authority(self) -> None:
        profile = subject.source_profile()
        plan = subject.provider_request_plan()
        self.assertEqual(
            profile["plan_amendment"],
            "PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE",
        )
        self.assertEqual(profile["plan_version"], "0.1+A1+A2")
        self.assertEqual(plan["provider_object_count"], 72)
        self.assertEqual(
            plan["paired_sparse_m1_policy"],
            "ACCEPT_EXACTLY_PAIRED_PROVIDER_ABSENCE_WITH_EXPLICIT_CENSORING",
        )
        self.assertEqual(plan["provider_execution_in_ci"], "DENIED")

    def test_coverage_accepts_explicit_sparse_rows_without_repair(self) -> None:
        start = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
        rows = [self._row(start + timedelta(minutes=index)) for index in range(10)]
        rows.pop(4)
        audit = subject._coverage_audit(rows, clock="M1", side="BID")
        self.assertEqual(audit["qa_state"], "PASS")
        self.assertEqual(audit["gap_run_count"], 1)
        self.assertEqual(audit["absent_timestamp_count"], 1)
        self.assertTrue(audit["gaps_require_exact_other_side_match"])
        self.assertEqual(
            audit["downstream_policy"],
            "INCOMPLETE_REQUIRED_MEMBERSHIP_NOT_EVALUABLE_NO_BRIDGING",
        )

    def test_post_target_missing_hours_are_censored_not_repaired(self) -> None:
        rows = []
        cursor = subject.a1.TARGET_END
        end = subject.a1.APPROVED_END
        missing_hour = subject.a1.TARGET_END + timedelta(hours=21)
        while cursor < end:
            if not (missing_hour <= cursor < missing_hour + timedelta(hours=1)):
                rows.append(self._row(cursor))
            cursor += timedelta(minutes=1)
        derived, audit = subject._post_target_h1_audit(rows, side="ASK")
        self.assertEqual(audit["qa_state"], "PASS")
        self.assertIn(
            missing_hour.strftime("%Y-%m-%dT%H:%M:%SZ"),
            audit["censored_hours_utc"],
        )
        self.assertEqual(len(derived), 47)
        self.assertEqual(audit["incomplete_hours_disposition"], "CENSORED_NOT_REPAIRED")

    def test_exact_bid_ask_pairing_remains_required(self) -> None:
        start = datetime(2026, 6, 1, tzinfo=timezone.utc)
        bid = [self._row(start), self._row(start + timedelta(minutes=2))]
        ask = [self._row(start)]
        audit = subject.a1.base._bid_ask_audit(bid, ask, clock="M1")
        self.assertEqual(audit["qa_state"], "BLOCK")
        self.assertEqual(
            audit["missing_ask_timestamps"],
            ["2026-06-01T00:02:00Z"],
        )

    def test_execute_requires_both_operator_bindings_before_network(self) -> None:
        with tempfile.TemporaryDirectory() as repository, tempfile.TemporaryDirectory() as external:
            with self.assertRaisesRegex(subject.IntakeError, "exact A2 operator approval"):
                subject.execute_intake(
                    repository_root=Path(repository),
                    gate="PD-JUNE-FM-G1",
                    amendment_gate="WRONG",
                    environ={"OVC_EXTERNAL_ARTIFACT_ROOT": external},
                )
            with self.assertRaisesRegex(subject.IntakeError, "prohibited in CI"):
                subject.execute_intake(
                    repository_root=Path(repository),
                    gate="PD-JUNE-FM-G1",
                    amendment_gate=(
                        "PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE"
                    ),
                    environ={
                        "OVC_EXTERNAL_ARTIFACT_ROOT": external,
                        "GITHUB_ACTIONS": "true",
                    },
                )

    def test_preflight_is_read_only_and_records_censoring_policy(self) -> None:
        with tempfile.TemporaryDirectory() as repository, tempfile.TemporaryDirectory() as external:
            result = subject.preflight(
                repository_root=Path(repository),
                environ={"OVC_EXTERNAL_ARTIFACT_ROOT": external},
            )
        self.assertEqual(result["status"], "READY_FOR_OPERATOR_LOCAL_EXECUTION")
        self.assertFalse(result["provider_network_access_performed"])
        self.assertEqual(
            result["amendment_gate"],
            "PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE",
        )
        self.assertEqual(
            result["downstream_incomplete_membership_policy"],
            "INCOMPLETE_REQUIRED_MEMBERSHIP_NOT_EVALUABLE_NO_BRIDGING",
        )


if __name__ == "__main__":
    unittest.main()
