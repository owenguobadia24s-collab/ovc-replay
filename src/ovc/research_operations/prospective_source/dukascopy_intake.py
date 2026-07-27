from __future__ import annotations

import argparse
import csv
import hashlib
import json
import lzma
import math
import os
import shutil
import struct
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ovc_evidence_store.external_root import resolve_external_root
from ovc_evidence_store.manifest import EvidenceStoreError

APPROVED_GATE = "RPS-G1"
APPROVED_SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1"
APPROVED_START = datetime(2026, 7, 24, tzinfo=timezone.utc)
APPROVED_END = datetime(2026, 7, 27, tzinfo=timezone.utc)
COMPRESSED_BYTE_LIMIT = 25 * 1024 * 1024
EXPANDED_BYTE_LIMIT = 100 * 1024 * 1024
PROVIDER = "DUKASCOPY"
INSTRUMENT = "GBPUSD"
ADAPTER = "OVC_DIRECT_BI5_CANDLE_ADAPTER"
ADAPTER_VERSION = "1.1.0-rps-wp2"
ORDERED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
LOGICAL_TYPES = ("unix_ms", "decimal", "decimal", "decimal", "decimal", "decimal")
BASE_URLS = (
    "https://datafeed.dukascopy.com/datafeed",
    "https://www.dukascopy.com/datafeed",
    "http://datafeed.dukascopy.com/datafeed",
)
USER_AGENT = "ovc-replay-rps-wp2/1.1 (+https://github.com/owenguobadia24s-collab/ovc-replay)"
CANDLE = struct.Struct(">5If")
PRICE_SCALE = Decimal("100000")


class IntakeError(RuntimeError):
    """Raised when bounded RPS-WP2 intake cannot lawfully complete."""


@dataclass(frozen=True)
class FetchResult:
    relative_path: str
    status: str
    url: str
    body: bytes
    sha256: str | None
    size_bytes: int
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True)
class CandleRow:
    timestamp_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @property
    def timestamp_ms(self) -> int:
        return int(self.timestamp_utc.timestamp() * 1000)

    def csv_row(self) -> tuple[str, ...]:
        return (
            str(self.timestamp_ms),
            format(self.open, ".5f"),
            format(self.high, ".5f"),
            format(self.low, ".5f"),
            format(self.close, ".5f"),
            _format_non_negative_decimal(self.volume),
        )


Fetcher = Callable[[str, bool], FetchResult]


def _utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise IntakeError(f"refusing to overwrite compact receipt: {path}")
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _format_non_negative_decimal(value: Decimal) -> str:
    if not value.is_finite() or value < 0:
        raise IntakeError(f"invalid non-negative decimal: {value!r}")
    normalized = value.normalize()
    result = format(normalized, "f")
    return "0" if result in {"-0", ""} else result


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _assert_operator_local(environ: Mapping[str, str]) -> None:
    if _is_truthy(environ.get("CI")) or _is_truthy(environ.get("GITHUB_ACTIONS")):
        raise IntakeError("provider execution is prohibited in CI/GitHub Actions")


def _request(relative_path: str, allow_missing: bool) -> FetchResult:
    errors: list[str] = []
    for attempt in range(1, 6):
        for base in BASE_URLS:
            url = f"{base}/{relative_path}"
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/octet-stream,*/*;q=0.8",
                    "Connection": "close",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    body = response.read()
                    if not body:
                        if allow_missing:
                            return FetchResult(
                                relative_path,
                                "NOT_PRESENT",
                                url,
                                b"",
                                None,
                                0,
                            )
                        raise IntakeError(f"empty required provider object: {url}")
                    return FetchResult(
                        relative_path=relative_path,
                        status="DOWNLOADED",
                        url=url,
                        body=body,
                        sha256=hashlib.sha256(body).hexdigest(),
                        size_bytes=len(body),
                        etag=response.headers.get("ETag"),
                        last_modified=response.headers.get("Last-Modified"),
                    )
            except urllib.error.HTTPError as exc:
                if exc.code in (404, 410) and allow_missing:
                    return FetchResult(
                        relative_path,
                        "NOT_PRESENT",
                        url,
                        b"",
                        None,
                        0,
                    )
                errors.append(f"{url}: HTTP {exc.code}")
                if exc.code not in (408, 425, 429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                errors.append(f"{url}: {type(exc).__name__}: {exc}")
        if attempt < 5:
            time.sleep(min(2 ** (attempt - 1), 8))
    raise IntakeError(
        "provider fetch failed after bounded retries: "
        + " | ".join(errors[-12:])
    )


def _decompress(body: bytes, *, identity: str) -> bytes:
    try:
        data = lzma.decompress(body)
    except lzma.LZMAError as exc:
        raise IntakeError(f"invalid BI5/LZMA object: {identity}") from exc
    if len(data) % CANDLE.size:
        raise IntakeError(
            f"invalid candle record length for {identity}: "
            f"{len(data)} is not divisible by {CANDLE.size}"
        )
    return data


def _decode_candles(
    data: bytes,
    *,
    base: datetime,
    partition_end: datetime,
    identity: str,
    accepted_start: datetime,
    accepted_end: datetime,
) -> list[CandleRow]:
    rows: list[CandleRow] = []
    previous: datetime | None = None
    for offset in range(0, len(data), CANDLE.size):
        seconds, open_raw, close_raw, low_raw, high_raw, volume_raw = CANDLE.unpack_from(
            data,
            offset,
        )
        timestamp = base + timedelta(seconds=seconds)
        if not (base <= timestamp < partition_end):
            raise IntakeError(
                f"provider candle outside transport partition for {identity}: "
                f"{_utc(timestamp)}"
            )
        if previous is not None and timestamp <= previous:
            raise IntakeError(
                f"provider candle timestamps not strictly increasing for {identity}"
            )
        previous = timestamp
        if not math.isfinite(volume_raw) or volume_raw < 0:
            raise IntakeError(
                f"invalid provider volume for {identity} at {_utc(timestamp)}"
            )
        if volume_raw == 0 and open_raw == close_raw == low_raw == high_raw:
            continue
        if high_raw < max(open_raw, low_raw, close_raw) or low_raw > min(
            open_raw,
            high_raw,
            close_raw,
        ):
            raise IntakeError(
                f"invalid provider OHLC ordering for {identity} at {_utc(timestamp)}"
            )
        if accepted_start <= timestamp < accepted_end:
            rows.append(
                CandleRow(
                    timestamp_utc=timestamp,
                    open=Decimal(open_raw) / PRICE_SCALE,
                    high=Decimal(high_raw) / PRICE_SCALE,
                    low=Decimal(low_raw) / PRICE_SCALE,
                    close=Decimal(close_raw) / PRICE_SCALE,
                    volume=Decimal(str(volume_raw)),
                )
            )
    return rows


def _m1_relative(day: datetime, side: str) -> str:
    return (
        f"GBPUSD/{day.year:04d}/{day.month - 1:02d}/{day.day:02d}/"
        f"{side}_candles_min_1.bi5"
    )


def _h1_relative(start: datetime, side: str) -> str:
    return (
        f"GBPUSD/{start.year:04d}/{start.month - 1:02d}/"
        f"{side}_candles_hour_1.bi5"
    )


def _transport_target(root: Path, relative_path: str) -> Path:
    return root / "transport" / "dukascopy-bi5" / Path(relative_path)


def _store_transport(root: Path, result: FetchResult) -> str | None:
    if result.status != "DOWNLOADED":
        return None
    target = _transport_target(root, result.relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise IntakeError(
            f"refusing to overwrite provider transport object: {target}"
        )
    target.write_bytes(result.body)
    return target.relative_to(root).as_posix()


def _workspace_size(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _enforce_limits(*, compressed_bytes: int, expanded_bytes: int) -> None:
    if compressed_bytes > COMPRESSED_BYTE_LIMIT:
        raise IntakeError(
            f"compressed-byte limit exceeded: "
            f"{compressed_bytes} > {COMPRESSED_BYTE_LIMIT}"
        )
    if expanded_bytes > EXPANDED_BYTE_LIMIT:
        raise IntakeError(
            f"expanded-byte limit exceeded: "
            f"{expanded_bytes} > {EXPANDED_BYTE_LIMIT}"
        )


def _write_csv(
    root: Path,
    *,
    clock: str,
    side: str,
    rows: Sequence[CandleRow],
) -> tuple[Path, bytes]:
    filename = f"GBPUSD_{clock}_{side}_20260724_20260727_UTC.csv"
    path = root / "source-objects" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise IntakeError(f"refusing to overwrite source object: {path}")
    lines = [",".join(ORDERED_COLUMNS)]
    lines.extend(",".join(row.csv_row()) for row in rows)
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(payload)
    return path, payload


def _source_object_id(clock: str, side: str) -> str:
    return (
        f"SRC.DUKASCOPY.GBPUSD.{clock}.{side}."
        "20260724_20260727.v1"
    )


def _schema_fingerprint() -> str:
    return _canonical_sha256(
        {
            "ordered_columns": ORDERED_COLUMNS,
            "logical_types": LOGICAL_TYPES,
            "timestamp_unit": "unix_ms",
            "timezone": "UTC",
            "decimal_authority": "base10_text",
            "flat_candle_policy": "DROP_ONLY_ZERO_VOLUME_EQUAL_OHLC",
            "parser_contract": "ovc-rps-wp2-bounded-bi5/v1",
        }
    )


def _crosses_weekend(left: datetime, right: datetime) -> bool:
    cursor = left.date()
    while cursor <= right.date():
        day = datetime(
            cursor.year,
            cursor.month,
            cursor.day,
            tzinfo=timezone.utc,
        )
        if day.weekday() >= 5:
            return True
        cursor += timedelta(days=1)
    return False


def _gap_audit(
    rows: Sequence[CandleRow],
    *,
    clock: str,
    side: str,
) -> dict[str, object]:
    step = timedelta(minutes=1 if clock == "M1" else 60)
    duplicates = 0
    non_monotonic = 0
    weekend_discontinuities: list[dict[str, object]] = []
    unexpected_gaps: list[dict[str, object]] = []
    for left, right in zip(rows, rows[1:]):
        delta = right.timestamp_utc - left.timestamp_utc
        if delta == timedelta(0):
            duplicates += 1
            continue
        if delta < timedelta(0):
            non_monotonic += 1
            continue
        if delta > step:
            item = {
                "after_utc": _utc(left.timestamp_utc),
                "before_utc": _utc(right.timestamp_utc),
                "duration_seconds": int(delta.total_seconds()),
            }
            if _crosses_weekend(left.timestamp_utc, right.timestamp_utc):
                weekend_discontinuities.append(item)
            else:
                unexpected_gaps.append(item)
    expected_first = APPROVED_START
    expected_last = APPROVED_END - step
    observed_first = rows[0].timestamp_utc if rows else None
    observed_last = rows[-1].timestamp_utc if rows else None
    boundary_complete = (
        observed_first == expected_first and observed_last == expected_last
    )
    state = (
        "PASS"
        if rows
        and not duplicates
        and not non_monotonic
        and not unexpected_gaps
        and boundary_complete
        else "BLOCK"
    )
    return {
        "clock": clock,
        "side": side,
        "row_count": len(rows),
        "duplicates": duplicates,
        "non_monotonic": non_monotonic,
        "expected_first_timestamp_utc": _utc(expected_first),
        "observed_first_timestamp_utc": (
            _utc(observed_first) if observed_first else None
        ),
        "expected_last_timestamp_utc": _utc(expected_last),
        "observed_last_timestamp_utc": (
            _utc(observed_last) if observed_last else None
        ),
        "boundary_complete": boundary_complete,
        "weekend_spanning_discontinuities": weekend_discontinuities,
        "unexpected_intra_session_gaps": unexpected_gaps,
        "qa_state": state,
    }


def _bid_ask_audit(
    bid_rows: Sequence[CandleRow],
    ask_rows: Sequence[CandleRow],
    *,
    clock: str,
) -> dict[str, object]:
    bid = {row.timestamp_utc: row for row in bid_rows}
    ask = {row.timestamp_utc: row for row in ask_rows}
    missing_ask = sorted(set(bid) - set(ask))
    missing_bid = sorted(set(ask) - set(bid))
    inverted: list[dict[str, object]] = []
    spreads: list[Decimal] = []
    for timestamp in sorted(set(bid) & set(ask)):
        left, right = bid[timestamp], ask[timestamp]
        if any(
            ask_value < bid_value
            for bid_value, ask_value in (
                (left.open, right.open),
                (left.high, right.high),
                (left.low, right.low),
                (left.close, right.close),
            )
        ):
            inverted.append({"timestamp_utc": _utc(timestamp)})
        spreads.append(right.close - left.close)
    state = (
        "PASS"
        if not missing_ask and not missing_bid and not inverted
        else "BLOCK"
    )
    return {
        "clock": clock,
        "paired_row_count": len(set(bid) & set(ask)),
        "missing_ask_timestamps": [_utc(value) for value in missing_ask],
        "missing_bid_timestamps": [_utc(value) for value in missing_bid],
        "inverted_price_rows": inverted,
        "minimum_close_spread": (
            _format_non_negative_decimal(min(spreads)) if spreads else None
        ),
        "maximum_close_spread": (
            _format_non_negative_decimal(max(spreads)) if spreads else None
        ),
        "qa_state": state,
    }


def _aggregate_complete_h1(
    rows: Sequence[CandleRow],
) -> dict[datetime, CandleRow]:
    grouped: dict[datetime, list[CandleRow]] = {}
    for row in rows:
        bucket = row.timestamp_utc.replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        grouped.setdefault(bucket, []).append(row)
    result: dict[datetime, CandleRow] = {}
    for bucket, members in grouped.items():
        members = sorted(members, key=lambda item: item.timestamp_utc)
        expected = {
            bucket + timedelta(minutes=index) for index in range(60)
        }
        observed = {member.timestamp_utc for member in members}
        if len(members) != 60 or observed != expected:
            continue
        result[bucket] = CandleRow(
            timestamp_utc=bucket,
            open=members[0].open,
            high=max(member.high for member in members),
            low=min(member.low for member in members),
            close=members[-1].close,
            volume=sum(
                (member.volume for member in members),
                Decimal("0"),
            ),
        )
    return result


def _h1_reconciliation(
    m1_rows: Sequence[CandleRow],
    native_rows: Sequence[CandleRow],
    *,
    side: str,
) -> dict[str, object]:
    derived = _aggregate_complete_h1(m1_rows)
    native = {row.timestamp_utc: row for row in native_rows}
    missing_native: list[str] = []
    mismatches: list[dict[str, object]] = []
    compared = 0
    for timestamp, row in sorted(derived.items()):
        other = native.get(timestamp)
        if other is None:
            missing_native.append(_utc(timestamp))
            continue
        compared += 1
        differing = [
            name
            for name in ("open", "high", "low", "close")
            if getattr(row, name) != getattr(other, name)
        ]
        if differing:
            mismatches.append(
                {
                    "timestamp_utc": _utc(timestamp),
                    "fields": differing,
                }
            )
    state = (
        "PASS"
        if compared > 0 and not missing_native and not mismatches
        else "BLOCK"
    )
    return {
        "side": side,
        "complete_m1_derived_h1_count": len(derived),
        "native_h1_count": len(native),
        "compared_count": compared,
        "missing_native_timestamps": missing_native,
        "ohlc_mismatches": mismatches,
        "volume_comparison_authority": "INFORMATIONAL_ONLY",
        "qa_state": state,
    }


def _logical_manifest(
    source_objects: Sequence[dict[str, object]],
) -> dict[str, object]:
    base: dict[str, object] = {
        "slice_id": APPROVED_SLICE_ID,
        "instrument": INSTRUMENT,
        "provider": PROVIDER,
        "source_window_start_utc": _utc(APPROVED_START),
        "source_window_end_utc": _utc(APPROVED_END),
        "source_objects": [
            {
                "object_id": item["object_id"],
                "clock": item["clock"],
                "side": item["side"],
                "sha256": item["sha256"],
            }
            for item in sorted(
                source_objects,
                key=lambda value: (
                    str(value["clock"]),
                    str(value["side"]),
                ),
            )
        ],
        "coverage_state": "COMPLETE",
        "frozen": True,
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
    }
    base["manifest_sha256"] = _canonical_sha256(base)
    return base


def _quarantine(staging: Path, *, reason: str) -> Path | None:
    if not staging.exists():
        return None
    quarantine_root = staging.parent / "quarantine"
    quarantine_root.mkdir(parents=True, exist_ok=True)
    target = quarantine_root / (
        f"{APPROVED_SLICE_ID}."
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}."
        f"{uuid.uuid4().hex[:8]}"
    )
    try:
        _write_json(
            staging / "incident.json",
            {
                "schema": "ovc-rps-wp2-intake-incident/v1",
                "slice_id": APPROVED_SLICE_ID,
                "reason": reason,
                "accepted_source_slice_created": False,
                "authority": "NONE",
            },
        )
    except Exception:
        pass
    staging.rename(target)
    return target


def _resolve_root(
    repository_root: Path,
    environ: Mapping[str, str],
) -> Path:
    try:
        return resolve_external_root(
            repository_root=repository_root,
            environ=environ,
            create=True,
        )
    except EvidenceStoreError as exc:
        raise IntakeError(str(exc)) from exc


def preflight(
    *,
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    values = os.environ if environ is None else environ
    root = _resolve_root(repository_root, values)
    final_root = (
        root
        / "prospective-source"
        / "intake"
        / APPROVED_SLICE_ID
    )
    if final_root.exists() and any(final_root.iterdir()):
        raise IntakeError(
            f"approved slice destination already contains material: {final_root}"
        )
    return {
        "status": "READY_FOR_OPERATOR_LOCAL_EXECUTION",
        "gate": APPROVED_GATE,
        "slice_id": APPROVED_SLICE_ID,
        "source_window_start_utc": _utc(APPROVED_START),
        "source_window_end_utc": _utc(APPROVED_END),
        "streams": ["M1_BID", "M1_ASK", "H1_BID", "H1_ASK"],
        "compressed_byte_limit": COMPRESSED_BYTE_LIMIT,
        "expanded_byte_limit": EXPANDED_BYTE_LIMIT,
        "provider_network_access_performed": False,
        "final_destination_exists_empty": final_root.exists(),
    }


def execute_intake(
    *,
    repository_root: Path,
    gate: str,
    environ: Mapping[str, str] | None = None,
    fetcher: Fetcher = _request,
) -> dict[str, object]:
    values = os.environ if environ is None else environ
    if gate != APPROVED_GATE:
        raise IntakeError(
            f"exact operator approval binding required: --gate {APPROVED_GATE}"
        )
    _assert_operator_local(values)
    root = _resolve_root(repository_root, values)
    intake_parent = root / "prospective-source" / "intake"
    intake_parent.mkdir(parents=True, exist_ok=True)
    final_root = intake_parent / APPROVED_SLICE_ID
    if final_root.exists():
        if any(final_root.iterdir()):
            raise IntakeError(
                f"refusing to overwrite existing intake destination: {final_root}"
            )
        final_root.rmdir()
    staging = intake_parent / (
        f".{APPROVED_SLICE_ID}.staging.{uuid.uuid4().hex}"
    )
    staging.mkdir(parents=False, exist_ok=False)

    compressed_bytes = 0
    expanded_bytes = 0
    transport_receipts: list[dict[str, object]] = []
    rows_by_stream: dict[tuple[str, str], list[CandleRow]] = {}
    try:
        for side in ("BID", "ASK"):
            combined: list[CandleRow] = []
            day = APPROVED_START
            while day < APPROVED_END:
                relative = _m1_relative(day, side)
                result = fetcher(relative, True)
                if result.status == "DOWNLOADED":
                    compressed_bytes += result.size_bytes
                    _enforce_limits(
                        compressed_bytes=compressed_bytes,
                        expanded_bytes=expanded_bytes,
                    )
                    cached = _store_transport(staging, result)
                    data = _decompress(result.body, identity=relative)
                    expanded_bytes += len(data)
                    _enforce_limits(
                        compressed_bytes=compressed_bytes,
                        expanded_bytes=expanded_bytes,
                    )
                    combined.extend(
                        _decode_candles(
                            data,
                            base=day,
                            partition_end=day + timedelta(days=1),
                            identity=relative,
                            accepted_start=APPROVED_START,
                            accepted_end=APPROVED_END,
                        )
                    )
                else:
                    cached = None
                transport_receipts.append(
                    {
                        "logical_stream": f"M1_{side}",
                        "relative_provider_path": relative,
                        "status": result.status,
                        "url": result.url,
                        "sha256": result.sha256,
                        "size_bytes": result.size_bytes,
                        "etag": result.etag,
                        "last_modified": result.last_modified,
                        "cached_relative_path": cached,
                    }
                )
                day += timedelta(days=1)
            rows_by_stream[("M1", side)] = sorted(
                combined,
                key=lambda row: row.timestamp_utc,
            )

        month_start = APPROVED_START.replace(day=1)
        if (
            APPROVED_END.month != APPROVED_START.month
            or APPROVED_END.year != APPROVED_START.year
        ):
            raise IntakeError(
                "approved RPS-WP2 H1 transport implementation supports "
                "one calendar month only"
            )
        if month_start.month == 12:
            month_end = month_start.replace(
                year=month_start.year + 1,
                month=1,
            )
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        for side in ("BID", "ASK"):
            relative = _h1_relative(APPROVED_START, side)
            result = fetcher(relative, False)
            if result.status != "DOWNLOADED":
                raise IntakeError(
                    f"required native H1 provider object unavailable: {relative}"
                )
            compressed_bytes += result.size_bytes
            _enforce_limits(
                compressed_bytes=compressed_bytes,
                expanded_bytes=expanded_bytes,
            )
            cached = _store_transport(staging, result)
            data = _decompress(result.body, identity=relative)
            expanded_bytes += len(data)
            _enforce_limits(
                compressed_bytes=compressed_bytes,
                expanded_bytes=expanded_bytes,
            )
            rows_by_stream[("H1", side)] = _decode_candles(
                data,
                base=month_start,
                partition_end=month_end,
                identity=relative,
                accepted_start=APPROVED_START,
                accepted_end=APPROVED_END,
            )
            transport_receipts.append(
                {
                    "logical_stream": f"H1_{side}",
                    "relative_provider_path": relative,
                    "status": result.status,
                    "url": result.url,
                    "sha256": result.sha256,
                    "size_bytes": result.size_bytes,
                    "etag": result.etag,
                    "last_modified": result.last_modified,
                    "cached_relative_path": cached,
                    "accepted_interval_is_bounded_subset_of_monthly_transport": True,
                }
            )

        if any(not rows for rows in rows_by_stream.values()):
            missing = [
                f"{clock}_{side}"
                for (clock, side), rows in rows_by_stream.items()
                if not rows
            ]
            raise IntakeError(
                "one or more logical streams contain no accepted rows: "
                + ", ".join(missing)
            )

        gap_results = [
            _gap_audit(rows, clock=clock, side=side)
            for (clock, side), rows in sorted(rows_by_stream.items())
        ]
        pair_results = [
            _bid_ask_audit(
                rows_by_stream[(clock, "BID")],
                rows_by_stream[(clock, "ASK")],
                clock=clock,
            )
            for clock in ("M1", "H1")
        ]
        h1_results = [
            _h1_reconciliation(
                rows_by_stream[("M1", side)],
                rows_by_stream[("H1", side)],
                side=side,
            )
            for side in ("BID", "ASK")
        ]
        if any(
            item["qa_state"] != "PASS"
            for item in gap_results + pair_results + h1_results
        ):
            raise IntakeError(
                "source QA did not pass; workspace must be quarantined"
            )

        source_objects: list[dict[str, object]] = []
        for (clock, side), rows in sorted(rows_by_stream.items()):
            path, payload = _write_csv(
                staging,
                clock=clock,
                side=side,
                rows=rows,
            )
            expanded_bytes += len(payload)
            _enforce_limits(
                compressed_bytes=compressed_bytes,
                expanded_bytes=expanded_bytes,
            )
            source_objects.append(
                {
                    "object_id": _source_object_id(clock, side),
                    "clock": clock,
                    "side": side,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                    "row_count": len(rows),
                    "first_timestamp_utc": _utc(rows[0].timestamp_utc),
                    "last_timestamp_utc": _utc(rows[-1].timestamp_utc),
                    "schema_fingerprint": _schema_fingerprint(),
                    "relative_path": path.relative_to(staging).as_posix(),
                }
            )

        request_receipt = {
            "schema": "ovc-rps-wp2-provider-request-receipt/v1",
            "gate": APPROVED_GATE,
            "slice_id": APPROVED_SLICE_ID,
            "provider": PROVIDER,
            "adapter": ADAPTER,
            "adapter_version": ADAPTER_VERSION,
            "instrument": INSTRUMENT,
            "source_window_start_utc": _utc(APPROVED_START),
            "source_window_end_utc": _utc(APPROVED_END),
            "logical_streams": [
                "M1_BID",
                "M1_ASK",
                "H1_BID",
                "H1_ASK",
            ],
            "transport_objects": transport_receipts,
            "compressed_bytes": compressed_bytes,
            "compressed_byte_limit": COMPRESSED_BYTE_LIMIT,
            "expanded_bytes_before_receipts": expanded_bytes,
            "expanded_byte_limit": EXPANDED_BYTE_LIMIT,
            "provider_network_location": "OPERATOR_LOCAL_ONLY",
            "ci_network_access": "DENIED",
        }
        _write_json(
            staging / "receipts" / "provider-request-receipt.json",
            request_receipt,
        )
        _write_json(
            staging / "receipts" / "source-object-inventory.json",
            {
                "schema": "ovc-rps-wp2-source-object-inventory/v1",
                "slice_id": APPROVED_SLICE_ID,
                "source_object_count": len(source_objects),
                "source_objects": source_objects,
            },
        )
        _write_json(
            staging / "receipts" / "gap-and-duplicate-qa.json",
            {
                "schema": "ovc-rps-wp2-gap-duplicate-qa/v1",
                "slice_id": APPROVED_SLICE_ID,
                "results": gap_results,
                "qa_state": "PASS",
                "repair_performed": False,
            },
        )
        _write_json(
            staging / "receipts" / "bid-ask-reconciliation.json",
            {
                "schema": "ovc-rps-wp2-bid-ask-reconciliation/v1",
                "slice_id": APPROVED_SLICE_ID,
                "results": pair_results,
                "qa_state": "PASS",
            },
        )
        _write_json(
            staging / "receipts" / "native-h1-reconciliation.json",
            {
                "schema": "ovc-rps-wp2-native-h1-reconciliation/v1",
                "slice_id": APPROVED_SLICE_ID,
                "results": h1_results,
                "qa_state": "PASS",
                "repair_authority": "NONE",
            },
        )
        manifest = _logical_manifest(source_objects)
        manifest_path = staging / "source-slice-manifest.json"
        _write_json(manifest_path, manifest)
        manifest_file_sha = hashlib.sha256(
            manifest_path.read_bytes()
        ).hexdigest()
        expanded_before_freeze_receipt = _workspace_size(staging)
        _enforce_limits(
            compressed_bytes=compressed_bytes,
            expanded_bytes=expanded_before_freeze_receipt,
        )
        _write_json(
            staging / "receipts" / "freeze-receipt.json",
            {
                "schema": "ovc-rps-wp2-freeze-receipt/v1",
                "slice_id": APPROVED_SLICE_ID,
                "manifest_sha256": manifest["manifest_sha256"],
                "manifest_file_sha256": manifest_file_sha,
                "source_object_count": 4,
                "compressed_bytes": compressed_bytes,
                "expanded_bytes_excluding_freeze_receipt": (
                    expanded_before_freeze_receipt
                ),
                "frozen": True,
                "release_status": "NOT_A_RELEASE",
                "selector_eligibility": "NONE",
                "r2_publication": "DENIED",
                "validation_consumption": "DENIED",
                "live_prospective_append": "DENIED",
            },
        )
        expanded_final = _workspace_size(staging)
        _enforce_limits(
            compressed_bytes=compressed_bytes,
            expanded_bytes=expanded_final,
        )
        staging.rename(final_root)
        return {
            "status": "FROZEN_LOCAL_SOURCE_SLICE",
            "slice_id": APPROVED_SLICE_ID,
            "manifest_sha256": manifest["manifest_sha256"],
            "manifest_file_sha256": manifest_file_sha,
            "source_object_count": 4,
            "compressed_bytes": compressed_bytes,
            "expanded_bytes": expanded_final,
            "final_root": str(final_root),
            "release_status": "NOT_A_RELEASE",
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
        }
    except Exception as exc:
        quarantined = _quarantine(staging, reason=str(exc))
        suffix = (
            f"; quarantined at {quarantined}"
            if quarantined is not None
            else ""
        )
        if isinstance(exc, IntakeError):
            raise IntakeError(str(exc) + suffix) from exc
        raise IntakeError(
            f"unexpected intake failure: {exc}{suffix}"
        ) from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Operator-local exact RPS-WP2 Dukascopy intake; "
            "provider execution is denied in CI."
        )
    )
    parser.add_argument("command", choices=("preflight", "execute"))
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path.cwd(),
    )
    parser.add_argument(
        "--gate",
        default=None,
        help=f"Required for execute; must equal {APPROVED_GATE}.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        repository_root = arguments.repository_root.resolve(strict=True)
        if arguments.command == "preflight":
            result = preflight(repository_root=repository_root)
        else:
            result = execute_intake(
                repository_root=repository_root,
                gate=arguments.gate or "",
            )
    except IntakeError as exc:
        print(f"RPS-WP2 intake blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
