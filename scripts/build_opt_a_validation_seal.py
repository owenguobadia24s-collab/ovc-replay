from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ovc_opt_b import aggregate_bars, contiguous_segments, read_dukascopy_csv  # noqa: E402
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402
from build_reference_level_registry import sha256  # noqa: E402


SEAL_VERSION = "A-SEAL-VALIDATION-1.0"
START = datetime(2025, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 1, 1, tzinfo=timezone.utc)


def write_bars(path: Path, bars: list | tuple) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([
            "bar_id", "instrument_id", "timeframe", "open_time_utc", "close_time_utc",
            "open", "high", "low", "close", "price_side", "source_id", "source_release_id",
        ])
        for bar in bars:
            writer.writerow([
                bar.bar_id, bar.instrument_id, bar.timeframe,
                bar.open_time.astimezone(timezone.utc).isoformat(),
                bar.close_time.astimezone(timezone.utc).isoformat(),
                str(bar.open), str(bar.high), str(bar.low), str(bar.close),
                bar.price_side, bar.source_id, bar.source_release_id,
            ])


def gap_ledger(raw: tuple, *, start: datetime = START, end: datetime = END) -> list[dict[str, object]]:
    records = []
    if raw[0].open_time > start:
        records.append({
            "gap_start_utc": start.isoformat(),
            "gap_end_utc": raw[0].open_time.isoformat(),
            "missing_minutes": int((raw[0].open_time - start).total_seconds() // 60),
            "position": "LEFT_BOUNDARY",
            "classification": "BOUNDARY_ABSENCE",
        })
    for left, right in zip(raw, raw[1:]):
        if right.open_time == left.close_time:
            continue
        missing = int((right.open_time - left.close_time).total_seconds() // 60)
        records.append({
            "gap_start_utc": left.close_time.isoformat(),
            "gap_end_utc": right.open_time.isoformat(),
            "missing_minutes": missing,
            "position": "INTERNAL",
            "classification": "CLOSURE_LIKE" if missing >= 360 else "SPARSE_PROVIDER_INTERVAL",
        })
    if raw[-1].close_time < end:
        records.append({
            "gap_start_utc": raw[-1].close_time.isoformat(),
            "gap_end_utc": end.isoformat(),
            "missing_minutes": int((end - raw[-1].close_time).total_seconds() // 60),
            "position": "RIGHT_BOUNDARY",
            "classification": "BOUNDARY_ABSENCE",
        })
    return records


def rejected_record(item) -> dict[str, object]:
    return {
        **asdict(item),
        "bucket_start": item.bucket_start.astimezone(timezone.utc).isoformat(),
    }


def volume_audit(path: Path) -> dict[str, int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        counts = Counter()
        for row in reader:
            value = Decimal(row["volume"])
            counts["rows"] += 1
            if value == 0:
                counts["zero_volume_rows"] += 1
            if value < 0:
                counts["negative_volume_rows"] += 1
    return {key: counts[key] for key in ("rows", "zero_volume_rows", "negative_volume_rows")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-m1", type=Path, required=True)
    parser.add_argument("--package-lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw_path = args.raw_m1.resolve()
    package_lock = args.package_lock.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"OPT-A validation seal target exists: {output}")
    output.mkdir(parents=True)
    (output / "sources/m1").mkdir(parents=True)
    (output / "canonical").mkdir()
    (output / "quality").mkdir()
    (output / "retrieval").mkdir()

    raw_hash = sha256(raw_path)
    source_release_id = f"dukascopy-gbpusd-bid-{raw_hash[:16]}"
    raw = read_dukascopy_csv(raw_path, source_release_id=source_release_id)
    volumes = volume_audit(raw_path)
    if volumes["rows"] != len(raw) or volumes["negative_volume_rows"]:
        raise ValueError("provider volume audit failed")
    if raw[0].open_time < START or raw[-1].close_time > END:
        raise ValueError("provider rows fall outside the approved holdout interval")
    if any(bar.open_time.second or bar.open_time.microsecond for bar in raw):
        raise ValueError("provider minute timestamps are not minute aligned")
    gaps = gap_ledger(raw)
    expected_minutes = int((END - START).total_seconds() // 60)
    missing_minutes = sum(int(item["missing_minutes"]) for item in gaps)
    if len(raw) + missing_minutes != expected_minutes:
        raise AssertionError("minute coverage conservation failed")

    fifteen = aggregate_bars(raw, target_timeframe="15M")
    two_hour = aggregate_bars(fifteen.accepted, target_timeframe="2H")
    raw_destination = output / "sources/m1" / raw_path.name
    shutil.copy2(raw_path, raw_destination)
    accepted_15m = output / "canonical/accepted_15m.csv"
    accepted_2h = output / "canonical/accepted_2h.csv"
    write_bars(accepted_15m, fifteen.accepted)
    write_bars(accepted_2h, two_hour.accepted)

    writers = {
        "gaps": DeterministicJsonlGzipWriter(output / "quality/minute_gap_ledger.jsonl.gz"),
        "rejected_15m": DeterministicJsonlGzipWriter(output / "quality/rejected_15m_buckets.jsonl.gz"),
        "rejected_2h": DeterministicJsonlGzipWriter(output / "quality/rejected_2h_context_buckets.jsonl.gz"),
    }
    for row in gaps:
        writers["gaps"].write(row)
    for item in fifteen.rejected:
        writers["rejected_15m"].write(rejected_record(item))
    for item in two_hour.rejected:
        writers["rejected_2h"].write(rejected_record(item))
    stream_metadata = {}
    for name, writer in writers.items():
        writer.close()
        stream_metadata[f"{name}_records"] = writer.count
        stream_metadata[f"{name}_canonical_jsonl_hash"] = writer.canonical_jsonl_hash

    retrieval = {
        "retrieval_contract": "DUKASCOPY_PROVIDER_DIRECT_M1_NO_FLATS_v0.1",
        "provider": "Dukascopy Bank SA historical data feed",
        "official_exporter": "https://www.dukascopy.com/swiss/english/marketwatch/historical/",
        "instrument": "GBPUSD",
        "timeframe": "m1",
        "price_type": "bid",
        "utc_offset_minutes": 0,
        "include_volumes": True,
        "volume_units": "units",
        "include_flats": False,
        "date_from": "2025-01-01",
        "date_to_exclusive": "2026-01-01",
        "format": "csv",
        "retrieval_client": "dukascopy-node",
        "retrieval_client_version": "1.49.0",
        "package_lock_sha256": sha256(package_lock),
        "retry_policy": {"failed_artifact_retries": 5, "retry_pause_ms": 1000, "retry_on_empty": False},
        "raw_filename": raw_path.name,
        "raw_sha256": raw_hash,
        "raw_size_bytes": raw_path.stat().st_size,
        "provider_returned_rows": len(raw),
        "provider_zero_volume_rows": volumes["zero_volume_rows"],
        "provider_negative_volume_rows": volumes["negative_volume_rows"],
    }
    retrieval_path = output / "retrieval/DUKASCOPY_RETRIEVAL_MANIFEST.json"
    retrieval_path.write_text(json.dumps(retrieval, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    class_counts = Counter(item["classification"] for item in gaps)
    segment_lengths = [len(segment) for segment in contiguous_segments(fifteen.accepted)]
    summary = {
        "interval": "[2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z)",
        "raw_m1_rows": len(raw),
        "raw_zero_volume_rows": volumes["zero_volume_rows"],
        "expected_interval_minutes": expected_minutes,
        "absent_minutes": missing_minutes,
        "first_provider_open_utc": raw[0].open_time.isoformat(),
        "last_provider_close_utc": raw[-1].close_time.isoformat(),
        "gap_records": len(gaps),
        "gap_classification_counts": dict(sorted(class_counts.items())),
        "internal_closure_like_missing_minutes": sum(
            item["missing_minutes"] for item in gaps if item["classification"] == "CLOSURE_LIKE"
        ),
        "internal_sparse_missing_minutes": sum(
            item["missing_minutes"] for item in gaps if item["classification"] == "SPARSE_PROVIDER_INTERVAL"
        ),
        "boundary_absent_minutes": sum(
            item["missing_minutes"] for item in gaps if item["classification"] == "BOUNDARY_ABSENCE"
        ),
        "accepted_15m_bars": len(fifteen.accepted),
        "rejected_touched_15m_buckets": len(fifteen.rejected),
        "expected_interval_15m_buckets": expected_minutes // 15,
        "accepted_2h_context_bars": len(two_hour.accepted),
        "rejected_touched_2h_context_buckets": len(two_hour.rejected),
        "expected_interval_2h_buckets": expected_minutes // 120,
        "contiguous_15m_segments": len(segment_lengths),
        "minimum_15m_segment_bars": min(segment_lengths),
        "maximum_15m_segment_bars": max(segment_lengths),
        "stream_metadata": stream_metadata,
    }
    summary_path = output / "quality/OPT_A_VALIDATION_INGESTION_SUMMARY.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = f"""# OVC OPT-A GBP/USD 2025 Validation Ingestion and Seal

**Status:** `SEALED 15M HOLDOUT RESEARCH AUTHORITY`  
**Seal ID:** `OPT-A.GBPUSD.2025.v1`  
**Execution authority:** `NONE`

## Provider release

- Interval: `[2025-01-01, 2026-01-01)` UTC
- Provider-returned GBP/USD BID minutes: {len(raw):,}
- Source SHA-256: `{raw_hash}`
- First provider minute: `{raw[0].open_time.isoformat()}`
- Last provider close: `{raw[-1].close_time.isoformat()}`
- Synthetic flat minutes: `PROHIBITED / NOT REQUESTED`

## Strict coverage

- Absent interval minutes retained: {missing_minutes:,}
- Internal closure-like gaps: {class_counts['CLOSURE_LIKE']:,}
- Internal sparse gaps: {class_counts['SPARSE_PROVIDER_INTERVAL']:,}
- Boundary absences: {class_counts['BOUNDARY_ABSENCE']:,}
- Complete accepted 15M bars: {len(fifteen.accepted):,}
- Touched but incomplete 15M buckets quarantined: {len(fifteen.rejected):,}
- Contiguous 15M segments: {len(segment_lengths):,}

## Authority boundary

The complete 15M bars are the sole holdout story authority. The {len(two_hour.accepted):,}
complete minute-chain 2H bars are retained only as validation context and grant no
2H OPT-D hypothesis authority. Missing minutes, untouched buckets and incomplete
buckets were not filled, repaired or inferred. This holdout may not alter the
ratified H1 hypotheses or their thresholds.
"""
    report_path = output / "OPT_A_GBPUSD_2025_VALIDATION_SEAL_REPORT.md"
    report_path.write_text(report, encoding="utf-8")

    artifacts = []
    for path, role in (
        (raw_destination, "RAW_M1_PROVIDER_RELEASE"),
        (retrieval_path, "RETRIEVAL_MANIFEST"),
        (accepted_15m, "CANONICAL_15M_HOLDOUT_AUTHORITY"),
        (accepted_2h, "M1_CHAIN_2H_CONTEXT_ONLY"),
        (writers["gaps"].path, "MINUTE_GAP_LEDGER"),
        (writers["rejected_15m"].path, "REJECTED_15M_BUCKET_LEDGER"),
        (writers["rejected_2h"].path, "REJECTED_2H_CONTEXT_BUCKET_LEDGER"),
        (summary_path, "INGESTION_SUMMARY"),
        (report_path, "HUMAN_READABLE_REPORT"),
    ):
        artifacts.append({
            "path": path.relative_to(output).as_posix(),
            "role": role,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        })
    manifest_core = {
        "seal_id": "OPT-A.GBPUSD.2025.v1",
        "seal_version": SEAL_VERSION,
        "sealed_date": "2026-07-19",
        "status": "SEALED_VALIDATION_RESEARCH_AUTHORITY",
        "scope": {
            "instrument_id": "GBPUSD",
            "price_side": "BID",
            "interval": summary["interval"],
            "timezone": "UTC",
            "canonical_timeframes": ["15M"],
            "context_only_timeframes": ["2H"],
        },
        "authority": {
            "15M": "Provider-returned M1 candles aggregated only from 15 exact records",
            "2H": "M1-chain context only; no OPT-D hypothesis authority",
            "synthetic_flat_candles": "PROHIBITED",
            "incomplete_15M": "QUARANTINED",
            "execution_authority": "NONE",
        },
        "counts": summary,
        "operator_authorization": "Operator approved 2025 Dukascopy ingestion for OPT-D-VALIDATE-0.1",
        "immutability_rule": "Any byte change creates a new seal ID/version; this release is never overwritten.",
        "artifacts": artifacts,
        "implementation_hashes": {
            "build_opt_a_validation_seal.py": sha256(Path(__file__).resolve()),
            "dukascopy.py": sha256(ROOT / "src/ovc_opt_b/providers/dukascopy.py"),
        },
    }
    manifest = {**manifest_core, "seal_hash": canonical_hash(manifest_core)}
    (output / "OPT_A_SEAL_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": manifest["status"],
        "seal_hash": manifest["seal_hash"],
        "raw_rows": len(raw),
        "accepted_15m": len(fifteen.accepted),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
