from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import lzma
import math
import os
import struct
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from ovc.opt_a.provider_population import source_specs_for_month, write_json


BASE_URLS = (
    "https://datafeed.dukascopy.com/datafeed",
    "https://www.dukascopy.com/datafeed",
    "http://datafeed.dukascopy.com/datafeed",
)
USER_AGENT = "ovc-replay-wp4/1.0 (+https://github.com/owenguobadia24s-collab/ovc-replay)"
CANDLE = struct.Struct(">5If")
PRICE_SCALE = Decimal("100000")


class DownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchResult:
    status: str
    url: str
    body: bytes
    sha256: str | None
    size_bytes: int
    etag: str | None
    last_modified: str | None


def _request(relative_path: str, *, allow_missing: bool) -> FetchResult:
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
                            return FetchResult("NOT_PRESENT", url, b"", None, 0, None, None)
                        raise DownloadError(f"empty required provider object: {url}")
                    return FetchResult(
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
                    return FetchResult("NOT_PRESENT", url, b"", None, 0, None, None)
                errors.append(f"{url}: HTTP {exc.code}")
                if exc.code not in (408, 425, 429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                errors.append(f"{url}: {type(exc).__name__}: {exc}")
        if attempt < 5:
            time.sleep(min(2 ** (attempt - 1), 8))
    raise DownloadError("provider fetch failed after bounded retries: " + " | ".join(errors[-12:]))


def _decompress(body: bytes, *, identity: str) -> bytes:
    try:
        data = lzma.decompress(body)
    except lzma.LZMAError as exc:
        raise DownloadError(f"invalid BI5/LZMA object: {identity}") from exc
    if len(data) % CANDLE.size:
        raise DownloadError(
            f"invalid candle record length for {identity}: {len(data)} is not divisible by {CANDLE.size}"
        )
    return data


def _format_price(value: int) -> str:
    return format(Decimal(value) / PRICE_SCALE, ".5f")


def _format_volume(value: float) -> str:
    if not math.isfinite(value) or value < 0:
        raise DownloadError(f"invalid provider volume: {value!r}")
    return format(value, ".10g")


def _records(data: bytes, *, base: datetime, interval_end: datetime, identity: str) -> list[list[str]]:
    rows: list[list[str]] = []
    previous: datetime | None = None
    for offset in range(0, len(data), CANDLE.size):
        seconds, open_raw, high_raw, low_raw, close_raw, volume = CANDLE.unpack_from(data, offset)
        timestamp = base + timedelta(seconds=seconds)
        if not (base <= timestamp < interval_end):
            raise DownloadError(f"provider candle outside partition for {identity}: {timestamp.isoformat()}")
        if previous is not None and timestamp <= previous:
            raise DownloadError(f"provider candle timestamps not strictly increasing for {identity}")
        if high_raw < max(open_raw, low_raw, close_raw) or low_raw > min(open_raw, high_raw, close_raw):
            raise DownloadError(f"invalid provider OHLC ordering for {identity} at {timestamp.isoformat()}")
        rows.append(
            [
                str(int(timestamp.timestamp() * 1000)),
                _format_price(open_raw),
                _format_price(high_raw),
                _format_price(low_raw),
                _format_price(close_raw),
                _format_volume(volume),
            ]
        )
        previous = timestamp
    return rows


def _m1_relative(year: int, zero_month: int, day: int, side: str) -> str:
    return f"GBPUSD/{year:04d}/{zero_month:02d}/{day:02d}/{side}_candles_min_1.bi5"


def _h1_relative(year: int, zero_month: int, side: str) -> str:
    return f"GBPUSD/{year:04d}/{zero_month:02d}/{side}_candles_hour_1.bi5"


def _write_csv(path: Path, rows: Iterable[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise DownloadError(f"refusing to overwrite provider object: {path}")
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        writer.writerows(rows)


def _store_raw(cache_root: Path, relative_path: str, result: FetchResult) -> Path | None:
    if result.status != "DOWNLOADED":
        return None
    target = cache_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise DownloadError(f"refusing to overwrite provider transport object: {target}")
    target.write_bytes(result.body)
    return target


def download_month(workspace: Path, year_month: str) -> dict[str, object]:
    specs = source_specs_for_month(year_month)
    year, month = (int(part) for part in year_month.split("-"))
    zero_month = month - 1
    days = calendar.monthrange(year, month)[1]
    cache_root = workspace / "transport_cache" / "dukascopy-bi5"
    object_receipts: list[dict[str, object]] = []

    for spec in specs:
        side = spec.price_side
        rows: list[list[str]] = []
        chunks: list[dict[str, object]] = []
        if spec.native_timeframe == "M1":
            for day in range(1, days + 1):
                relative = _m1_relative(year, zero_month, day, side)
                result = _request(relative, allow_missing=True)
                raw_path = _store_raw(cache_root, relative, result)
                chunk: dict[str, object] = {
                    "relative_provider_path": relative,
                    "status": result.status,
                    "url": result.url,
                    "sha256": result.sha256,
                    "size_bytes": result.size_bytes,
                    "etag": result.etag,
                    "last_modified": result.last_modified,
                    "cached_path": (
                        raw_path.relative_to(workspace).as_posix() if raw_path is not None else None
                    ),
                    "row_count": 0,
                }
                if result.status == "DOWNLOADED":
                    day_start = datetime(year, month, day, tzinfo=timezone.utc)
                    parsed = _records(
                        _decompress(result.body, identity=relative),
                        base=day_start,
                        interval_end=day_start + timedelta(days=1),
                        identity=relative,
                    )
                    chunk["row_count"] = len(parsed)
                    rows.extend(parsed)
                chunks.append(chunk)
                time.sleep(0.05)
        else:
            relative = _h1_relative(year, zero_month, side)
            result = _request(relative, allow_missing=False)
            raw_path = _store_raw(cache_root, relative, result)
            parsed = _records(
                _decompress(result.body, identity=relative),
                base=spec.interval_start,
                interval_end=spec.interval_end,
                identity=relative,
            )
            rows.extend(parsed)
            chunks.append(
                {
                    "relative_provider_path": relative,
                    "status": result.status,
                    "url": result.url,
                    "sha256": result.sha256,
                    "size_bytes": result.size_bytes,
                    "etag": result.etag,
                    "last_modified": result.last_modified,
                    "cached_path": raw_path.relative_to(workspace).as_posix() if raw_path else None,
                    "row_count": len(parsed),
                }
            )

        rows.sort(key=lambda item: int(item[0]))
        if not rows:
            raise DownloadError(f"no provider candles accepted for {spec.source_object_id}")
        for left, right in zip(rows, rows[1:]):
            if int(right[0]) <= int(left[0]):
                raise DownloadError(f"duplicate or non-monotonic monthly rows for {spec.source_object_id}")
        output = workspace / spec.relative_csv_path
        _write_csv(output, rows)
        object_receipts.append(
            {
                "source_object_id": spec.source_object_id,
                "native_timeframe": spec.native_timeframe,
                "price_side": side,
                "research_role": spec.research_role,
                "target_release_id": spec.target_release_id,
                "output_path": output.relative_to(workspace).as_posix(),
                "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "output_size_bytes": output.stat().st_size,
                "row_count": len(rows),
                "transport_chunks": chunks,
            }
        )
        print(
            f"WP4 provider object complete {spec.source_object_id} "
            f"rows={len(rows)} bytes={output.stat().st_size}",
            flush=True,
        )

    receipt = {
        "schema": "ovc-opt-a-wp4-downloader-receipt/v2",
        "provider": "DUKASCOPY",
        "adapter": "OVC_DIRECT_BI5_CANDLE_ADAPTER",
        "adapter_version": "1.0.0",
        "instrument_id": "GBPUSD",
        "year_month": year_month,
        "interval_start": specs[0].interval_start.isoformat().replace("+00:00", "Z"),
        "interval_end": specs[0].interval_end.isoformat().replace("+00:00", "Z"),
        "research_role": specs[0].research_role,
        "source_object_count": len(object_receipts),
        "objects": object_receipts,
        "raw_transport_cache_retained": True,
        "market_authority": "NONE",
        "release_parent": "DENIED_UNTIL_FREEZE",
        "selector_input": "DENIED",
        "validation_consumption": (
            "LOCKED_UNCONSUMED" if specs[0].research_role == "VALIDATION" else "NOT_APPLICABLE"
        ),
    }
    receipt_path = workspace / "records" / "downloader" / f"{year_month}.json"
    if receipt_path.exists():
        raise DownloadError(f"refusing to overwrite downloader receipt: {receipt_path}")
    write_json(receipt_path, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year-month", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    arguments = parser.parse_args()
    workspace = arguments.workspace.resolve(strict=True)
    receipt = download_month(workspace, arguments.year_month)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
