from __future__ import annotations

import hashlib
import json
import lzma
import struct
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from ovc.research_operations.prospective_source import dukascopy_intake as original
from ovc.research_operations.prospective_source import dukascopy_intake_rps_g1a as intake

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

    for day_offset in range(3):
        day = start + timedelta(days=day_offset)
        rows: list[tuple[datetime, float, float, float, float, float]] = []
        for minute in range(24 * 60):
            timestamp = day + timedelta(minutes=minute)
            sequence = day_offset * 24 * 60 + minute
            base_price = 1.26000 + sequence * 0.000001
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
    for hour_offset in range(72):
        hour = start + timedelta(hours=hour_offset)
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
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.calls: list[tuple[str, bool]] = []
        for side in ("BID", "ASK"):
            daily, h1 = _provider_payloads(side)
            for day, body in daily.items():
                self.objects[intake._m1_relative(day, side)] = body
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


class RpsG1AJuneProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.repository = root / "repo"
        self.repository.mkdir()
        self.external = root / "external"
        self.external.mkdir()
        self.environ = {"OVC_EXTERNAL_ARTIFACT_ROOT": str(self.external)}

    def test_preflight_is_exact_and_no_network(self) -> None:
        result = intake.preflight(
            repository_root=self.repository,
            environ=self.environ,
        )
        self.assertEqual(result["gate"], "RPS-G1A")
        self.assertEqual(
            result["slice_id"],
            "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1",
        )
        self.assertEqual(
            result["source_window_start_utc"],
            "2026-06-22T00:00:00Z",
        )
        self.assertEqual(
            result["source_window_end_utc"],
            "2026-06-25T00:00:00Z",
        )
        self.assertEqual(
            result["streams"],
            ["M1_BID", "M1_ASK", "H1_BID", "H1_ASK"],
        )
        self.assertIs(result["provider_network_access_performed"], False)

    def test_fake_provider_freezes_exact_replacement_slice(self) -> None:
        fetcher = FakeFetcher()
        result = intake.execute_intake(
            repository_root=self.repository,
            gate="RPS-G1A",
            environ=self.environ,
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
            (final_root / "source-slice-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["slice_id"],
            "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1",
        )
        self.assertEqual(manifest["source_window_start_utc"], "2026-06-22T00:00:00Z")
        self.assertEqual(manifest["source_window_end_utc"], "2026-06-25T00:00:00Z")
        self.assertEqual(len(manifest["source_objects"]), 4)
        self.assertTrue(
            all("20260622_20260625" in item["object_id"] for item in manifest["source_objects"])
        )
        self.assertEqual(manifest["coverage_state"], "COMPLETE")
        self.assertIs(manifest["frozen"], True)
        self.assertEqual(len(fetcher.calls), 8)

    def test_profile_does_not_mutate_original_july_constants(self) -> None:
        intake.preflight(repository_root=self.repository, environ=self.environ)
        self.assertEqual(original.APPROVED_GATE, "RPS-G1")
        self.assertEqual(
            original.APPROVED_SLICE_ID,
            "RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1",
        )
        self.assertEqual(original.APPROVED_START.month, 7)

    def test_provider_execution_is_denied_in_ci(self) -> None:
        with self.assertRaisesRegex(intake.IntakeError, "prohibited in CI"):
            intake.execute_intake(
                repository_root=self.repository,
                gate="RPS-G1A",
                environ={
                    "OVC_EXTERNAL_ARTIFACT_ROOT": str(self.external),
                    "CI": "true",
                },
                fetcher=FakeFetcher(),
            )

    def test_exact_amendment_gate_is_required(self) -> None:
        with self.assertRaisesRegex(intake.IntakeError, "exact operator approval"):
            intake.execute_intake(
                repository_root=self.repository,
                gate="RPS-G1",
                environ=self.environ,
                fetcher=FakeFetcher(),
            )


if __name__ == "__main__":
    unittest.main()
