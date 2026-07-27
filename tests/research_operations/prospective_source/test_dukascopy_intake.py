from __future__ import annotations

import hashlib
import json
import lzma
import struct
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from ovc.research_operations.prospective_source import dukascopy_intake as intake

CANDLE = struct.Struct(">5If")


def _raw_price(value: float) -> int:
    return int(round(value * 100000))


def _pack_partition(
    base: datetime,
    rows: list[tuple[datetime, float, float, float, float, float]],
) -> bytes:
    payload = bytearray()
    for timestamp, open_price, high, low, close, volume in rows:
        seconds = int((timestamp - base).total_seconds())
        payload.extend(
            CANDLE.pack(
                seconds,
                _raw_price(open_price),
                _raw_price(close),
                _raw_price(low),
                _raw_price(high),
                float(volume),
            )
        )
    return lzma.compress(bytes(payload))


def _provider_payloads(side: str) -> tuple[dict[datetime, bytes], bytes]:
    spread = 0.0001 if side == "ASK" else 0.0
    start = intake.APPROVED_START
    daily: dict[datetime, bytes] = {}
    all_m1: list[tuple[datetime, float, float, float, float, float]] = []

    for day in (start, start + timedelta(days=2)):
        rows: list[tuple[datetime, float, float, float, float, float]] = []
        minute_start = 0 if day == start else 22 * 60
        minute_end = 2 * 60 if day == start else 24 * 60
        for minute in range(minute_start, minute_end):
            timestamp = day + timedelta(minutes=minute)
            base_price = 1.25000 + len(all_m1) * 0.000001
            row = (
                timestamp,
                base_price + spread,
                base_price + spread + 0.00020,
                base_price + spread - 0.00020,
                base_price + spread + 0.00010,
                1.0,
            )
            rows.append(row)
            all_m1.append(row)
        daily[day] = _pack_partition(day, rows)

    h1_rows: list[tuple[datetime, float, float, float, float, float]] = []
    for hour in (
        start,
        start + timedelta(hours=1),
        start + timedelta(days=2, hours=22),
        start + timedelta(days=2, hours=23),
    ):
        members = [
            row
            for row in all_m1
            if hour <= row[0] < hour + timedelta(hours=1)
        ]
        h1_rows.append(
            (
                hour,
                members[0][1],
                max(row[2] for row in members),
                min(row[3] for row in members),
                members[-1][4],
                60.0,
            )
        )
    month_start = start.replace(day=1)
    return daily, _pack_partition(month_start, h1_rows)


class FakeFetcher:
    def __init__(self, *, mismatched_ask_h1: bool = False) -> None:
        self.objects: dict[str, bytes] = {}
        self.calls: list[tuple[str, bool]] = []
        for side in ("BID", "ASK"):
            daily, h1 = _provider_payloads(side)
            for day, body in daily.items():
                self.objects[intake._m1_relative(day, side)] = body
            if mismatched_ask_h1 and side == "ASK":
                _, h1 = _provider_payloads("BID")
            self.objects[intake._h1_relative(intake.APPROVED_START, side)] = h1

    def __call__(self, relative_path: str, allow_missing: bool) -> intake.FetchResult:
        self.calls.append((relative_path, allow_missing))
        body = self.objects.get(relative_path)
        if body is None:
            if allow_missing:
                return intake.FetchResult(
                    relative_path=relative_path,
                    status="NOT_PRESENT",
                    url=f"fake://{relative_path}",
                    body=b"",
                    sha256=None,
                    size_bytes=0,
                )
            raise intake.IntakeError(f"required fake object missing: {relative_path}")
        return intake.FetchResult(
            relative_path=relative_path,
            status="DOWNLOADED",
            url=f"fake://{relative_path}",
            body=body,
            sha256=hashlib.sha256(body).hexdigest(),
            size_bytes=len(body),
        )


class BoundedDukascopyIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.repository = root / "repo"
        self.repository.mkdir()
        self.external = root / "external"
        self.external.mkdir()

    def _root_patch(self):
        return patch.object(
            intake,
            "resolve_external_root",
            return_value=self.external,
        )

    def test_preflight_is_exact_and_does_not_call_provider(self) -> None:
        with self._root_patch():
            result = intake.preflight(
                repository_root=self.repository,
                environ={},
            )
        self.assertEqual(
            result["slice_id"],
            "RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1",
        )
        self.assertEqual(
            result["source_window_start_utc"],
            "2026-07-24T00:00:00Z",
        )
        self.assertEqual(
            result["source_window_end_utc"],
            "2026-07-27T00:00:00Z",
        )
        self.assertEqual(
            result["streams"],
            ["M1_BID", "M1_ASK", "H1_BID", "H1_ASK"],
        )
        self.assertIs(result["provider_network_access_performed"], False)

    def test_fake_provider_builds_exact_frozen_local_slice(self) -> None:
        fetcher = FakeFetcher()
        with self._root_patch():
            result = intake.execute_intake(
                repository_root=self.repository,
                gate="RPS-G1",
                environ={},
                fetcher=fetcher,
            )
        self.assertEqual(result["status"], "FROZEN_LOCAL_SOURCE_SLICE")
        self.assertEqual(result["source_object_count"], 4)
        self.assertEqual(result["release_status"], "NOT_A_RELEASE")
        self.assertEqual(result["selector_eligibility"], "NONE")
        self.assertEqual(result["r2_publication"], "DENIED")
        self.assertEqual(result["validation_consumption"], "DENIED")

        final_root = (
            self.external
            / "prospective-source"
            / "intake"
            / intake.APPROVED_SLICE_ID
        )
        manifest = json.loads(
            (final_root / "source-slice-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(manifest["source_objects"]), 4)
        self.assertEqual(
            {(item["clock"], item["side"]) for item in manifest["source_objects"]},
            {("M1", "BID"), ("M1", "ASK"), ("H1", "BID"), ("H1", "ASK")},
        )
        self.assertEqual(manifest["coverage_state"], "COMPLETE")
        self.assertIs(manifest["frozen"], True)
        self.assertEqual(manifest["release_status"], "NOT_A_RELEASE")

        expected_receipts = {
            "provider-request-receipt.json",
            "source-object-inventory.json",
            "gap-and-duplicate-qa.json",
            "bid-ask-reconciliation.json",
            "native-h1-reconciliation.json",
            "freeze-receipt.json",
        }
        self.assertEqual(
            {path.name for path in (final_root / "receipts").iterdir()},
            expected_receipts,
        )
        compact_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (final_root / "receipts").glob("*.json")
        )
        self.assertNotIn(str(self.external), compact_text)
        self.assertEqual(len(fetcher.calls), 8)

    def test_provider_execution_is_denied_in_ci(self) -> None:
        with self.assertRaisesRegex(intake.IntakeError, "prohibited in CI"):
            intake.execute_intake(
                repository_root=self.repository,
                gate="RPS-G1",
                environ={"CI": "true"},
                fetcher=FakeFetcher(),
            )

    def test_exact_gate_binding_is_required(self) -> None:
        with self.assertRaisesRegex(intake.IntakeError, "exact operator approval"):
            intake.execute_intake(
                repository_root=self.repository,
                gate="",
                environ={},
                fetcher=FakeFetcher(),
            )

    def test_reconciliation_failure_quarantines_without_accepting_slice(self) -> None:
        with self._root_patch():
            with self.assertRaisesRegex(intake.IntakeError, "source QA did not pass"):
                intake.execute_intake(
                    repository_root=self.repository,
                    gate="RPS-G1",
                    environ={},
                    fetcher=FakeFetcher(mismatched_ask_h1=True),
                )
        final_root = (
            self.external
            / "prospective-source"
            / "intake"
            / intake.APPROVED_SLICE_ID
        )
        quarantine = self.external / "prospective-source" / "intake" / "quarantine"
        self.assertFalse(final_root.exists())
        self.assertTrue(quarantine.is_dir())
        self.assertEqual(len(list(quarantine.iterdir())), 1)

    def test_byte_limit_breach_quarantines(self) -> None:
        with self._root_patch(), patch.object(
            intake,
            "COMPRESSED_BYTE_LIMIT",
            1,
        ):
            with self.assertRaisesRegex(intake.IntakeError, "compressed-byte limit"):
                intake.execute_intake(
                    repository_root=self.repository,
                    gate="RPS-G1",
                    environ={},
                    fetcher=FakeFetcher(),
                )
        final_root = (
            self.external
            / "prospective-source"
            / "intake"
            / intake.APPROVED_SLICE_ID
        )
        self.assertFalse(final_root.exists())

    def test_existing_nonempty_destination_is_never_overwritten(self) -> None:
        final_root = (
            self.external
            / "prospective-source"
            / "intake"
            / intake.APPROVED_SLICE_ID
        )
        final_root.mkdir(parents=True)
        marker = final_root / "existing.txt"
        marker.write_text("preserve", encoding="utf-8")
        with self._root_patch():
            with self.assertRaisesRegex(intake.IntakeError, "refusing to overwrite"):
                intake.execute_intake(
                    repository_root=self.repository,
                    gate="RPS-G1",
                    environ={},
                    fetcher=FakeFetcher(),
                )
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
