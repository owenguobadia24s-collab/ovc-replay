from __future__ import annotations

import hashlib
import json
import lzma
import shutil
import struct
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from ovc.research_operations.prospective_source import (
    dukascopy_gapped_recovery as recovery,
)
from ovc.research_operations.prospective_source import (
    gapped_source_contract as contract,
)
from ovc.research_operations.prospective_source import (
    gapped_source_qa as qa,
)

CANDLE = struct.Struct(">5If")


def _raw(value: float) -> int:
    return int(round(value * 100000))


def _pack(
    base: datetime,
    rows: list[
        tuple[
            datetime,
            float,
            float,
            float,
            float,
            float,
        ]
    ],
) -> bytes:
    payload = bytearray()
    for timestamp, open_price, high, low, close, volume in rows:
        payload.extend(
            CANDLE.pack(
                int((timestamp - base).total_seconds()),
                _raw(open_price),
                _raw(close),
                _raw(low),
                _raw(high),
                float(volume),
            )
        )
    return lzma.compress(bytes(payload))


def _missing_minutes() -> set[datetime]:
    # Twenty-four disjoint runs across eight complete hours;
    # eleven runs have two minutes and thirteen have one minute.
    hours = [21, 22, 23, 45, 46, 47, 69, 70]
    lengths = [2] * 11 + [1] * 13
    result: set[datetime] = set()
    run_index = 0
    for hour in hours:
        for minute in (3, 17, 39):
            length = lengths[run_index]
            run_index += 1
            start = recovery.START + timedelta(
                hours=hour,
                minutes=minute,
            )
            for offset in range(length):
                result.add(start + timedelta(minutes=offset))
    assert len(result) == 35
    return result


def _all_rows(
    side: str,
) -> list[
    tuple[datetime, float, float, float, float, float]
]:
    spread = 0.0001 if side == "ASK" else 0.0
    rows = []
    cursor = recovery.START
    index = 0
    while cursor < recovery.END:
        price = 1.25000 + index * 0.000001 + spread
        rows.append(
            (
                cursor,
                price,
                price + 0.0002,
                price - 0.0002,
                price + 0.0001,
                1.0,
            )
        )
        cursor += timedelta(minutes=1)
        index += 1
    return rows


def _h1_rows(rows):
    result = []
    cursor = recovery.START
    by_timestamp = {item[0]: item for item in rows}
    while cursor < recovery.END:
        members = [
            by_timestamp[cursor + timedelta(minutes=index)]
            for index in range(60)
        ]
        result.append(
            (
                cursor,
                members[0][1],
                max(item[2] for item in members),
                min(item[3] for item in members),
                members[-1][4],
                60.0,
            )
        )
        cursor += timedelta(hours=1)
    return result


class GappedRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.repository = root / "repo"
        self.repository.mkdir()
        self.external = root / "external"
        self.external.mkdir()
        self.quarantine = (
            self.external
            / "prospective-source"
            / "intake"
            / "quarantine"
            / recovery.QUARANTINE_ID
        )
        self.quarantine.mkdir(parents=True)
        self.sizes = self._write_quarantine()
        self.root_patch = patch.object(
            recovery.base,
            "_resolve_root",
            return_value=self.external,
        )
        self.size_patch = patch.object(
            contract,
            "EXPECTED_SIZES",
            self.sizes,
        )
        self.root_patch.start()
        self.size_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.size_patch.stop)

    def _write_quarantine(
        self,
        *,
        extra_ask_gap: bool = False,
    ) -> dict[str, int]:
        missing = _missing_minutes()
        sizes: dict[str, int] = {}
        for side in ("BID", "ASK"):
            full = _all_rows(side)
            side_missing = set(missing)
            if extra_ask_gap and side == "ASK":
                side_missing.add(
                    recovery.START
                    + timedelta(hours=10, minutes=10)
                )
            accepted = [
                item
                for item in full
                if item[0] not in side_missing
            ]
            for day_offset in range(3):
                day = recovery.START + timedelta(days=day_offset)
                daily = [
                    item
                    for item in accepted
                    if day
                    <= item[0]
                    < day + timedelta(days=1)
                ]
                relative = recovery.base._m1_relative(day, side)
                path = (
                    self.quarantine
                    / "transport"
                    / "dukascopy-bi5"
                    / relative
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(_pack(day, daily))
                sizes[
                    path.relative_to(self.quarantine).as_posix()
                ] = path.stat().st_size
            month_start = recovery.START.replace(day=1)
            relative = recovery.base._h1_relative(
                recovery.START,
                side,
            )
            path = (
                self.quarantine
                / "transport"
                / "dukascopy-bi5"
                / relative
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_pack(month_start, _h1_rows(full)))
            sizes[
                path.relative_to(self.quarantine).as_posix()
            ] = path.stat().st_size
        (self.quarantine / "incident.json").write_text(
            json.dumps(
                {
                    "slice_id": recovery.SLICE_ID,
                    "accepted_source_slice_created": False,
                    "reason": "source QA did not pass",
                }
            ),
            encoding="utf-8",
        )
        return sizes

    def test_exact_gapped_quarantine_freezes_without_network_or_mutation(
        self,
    ) -> None:
        before = {
            path.relative_to(self.quarantine).as_posix(): (
                hashlib.sha256(path.read_bytes()).hexdigest()
            )
            for path in self.quarantine.rglob("*")
            if path.is_file()
        }
        inventory = recovery.build_inventory(
            repository_root=self.repository,
            environ={},
        )
        self.assertEqual(
            inventory["status"],
            "CHECKSUM_INVENTORY_FROZEN",
        )
        result = recovery.freeze(
            repository_root=self.repository,
            gate="RPS-G1B",
            environ={},
        )
        self.assertEqual(
            result["status"],
            "FROZEN_LOCAL_GAPPED_SOURCE_SLICE",
        )
        self.assertEqual(result["coverage_state"], "GAPPED")
        self.assertIs(
            result["provider_network_access_performed"],
            False,
        )
        final = (
            self.external
            / "prospective-source"
            / "intake"
            / recovery.SLICE_ID
        )
        manifest = json.loads(
            (final / "source-slice-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["coverage_state"], "GAPPED")
        gap = json.loads(
            (
                final
                / "receipts"
                / "gap-and-duplicate-qa.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(gap["qa_state"], "PASS_GAPPED")
        self.assertEqual(
            gap["m1_results"][0]["missing_timestamp_count"],
            35,
        )
        self.assertEqual(
            gap["m1_results"][0]["gap_run_count"],
            24,
        )
        coverage = json.loads(
            (
                final
                / "receipts"
                / "downstream-coverage-propagation.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            coverage["qa_state"],
            "PASS_GAPPED_EXCLUSION",
        )
        self.assertTrue(
            all(
                item["unavailable_parent_count"] > 0
                for item in coverage["results"]
            )
        )
        blocked_parent = coverage["results"][0][
            "unavailable_parents"
        ][0]["parent_start_utc"]
        with self.assertRaisesRegex(
            recovery.RecoveryError,
            "must be excluded",
        ):
            qa.assert_parent_available(
                coverage["results"][0],
                blocked_parent,
            )
        after = {
            path.relative_to(self.quarantine).as_posix(): (
                hashlib.sha256(path.read_bytes()).hexdigest()
            )
            for path in self.quarantine.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_mismatched_bid_ask_gaps_write_qa_before_quarantine(
        self,
    ) -> None:
        shutil.rmtree(self.quarantine)
        self.quarantine.mkdir(parents=True)
        self.sizes.clear()
        self.sizes.update(
            self._write_quarantine(extra_ask_gap=True)
        )
        recovery.build_inventory(
            repository_root=self.repository,
            environ={},
        )
        with self.assertRaisesRegex(
            recovery.RecoveryError,
            "acceptance conditions",
        ):
            recovery.freeze(
                repository_root=self.repository,
                gate="RPS-G1B",
                environ={},
            )
        quarantine_parent = (
            self.external
            / "prospective-source"
            / "intake"
            / "quarantine"
        )
        attempts = [
            path
            for path in quarantine_parent.iterdir()
            if ".rps-g1b-recovery." in path.name
        ]
        self.assertEqual(len(attempts), 1)
        receipts = attempts[0] / "receipts"
        self.assertTrue(
            (receipts / "gap-and-duplicate-qa.json").is_file()
        )
        self.assertTrue(
            (receipts / "bid-ask-reconciliation.json").is_file()
        )
        self.assertTrue(
            (
                receipts
                / "downstream-coverage-propagation.json"
            ).is_file()
        )
        self.assertFalse(
            (
                self.external
                / "prospective-source"
                / "intake"
                / recovery.SLICE_ID
            ).exists()
        )

    def test_checksum_change_after_inventory_is_rejected(self) -> None:
        recovery.build_inventory(
            repository_root=self.repository,
            environ={},
        )
        target = next(
            path
            for path in self.quarantine.rglob("*.bi5")
            if "min_1" in path.name
        )
        payload = bytearray(target.read_bytes())
        payload[-1] ^= 1
        target.write_bytes(bytes(payload))
        with self.assertRaisesRegex(
            recovery.RecoveryError,
            "changed after checksum",
        ):
            recovery.freeze(
                repository_root=self.repository,
                gate="RPS-G1B",
                environ={},
            )

    def test_freeze_is_denied_in_ci_and_requires_exact_gate(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            recovery.RecoveryError,
            "RPS-G1B",
        ):
            recovery.freeze(
                repository_root=self.repository,
                gate="",
                environ={},
            )
        with self.assertRaisesRegex(
            recovery.RecoveryError,
            "prohibited in CI",
        ):
            recovery.freeze(
                repository_root=self.repository,
                gate="RPS-G1B",
                environ={"CI": "true"},
            )


if __name__ == "__main__":
    unittest.main()
