from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import median

from ovc_opt_b import aggregate_bars, read_dukascopy_csv, replay_unlevelled_terms


def write_bars(path: Path, bars) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "bar_id", "instrument_id", "timeframe", "open_time_utc", "close_time_utc",
            "open", "high", "low", "close", "price_side", "source_id", "source_release_id",
        ])
        for bar in bars:
            writer.writerow([
                bar.bar_id, bar.instrument_id, bar.timeframe, bar.open_time.isoformat(), bar.close_time.isoformat(),
                bar.open, bar.high, bar.low, bar.close, bar.price_side, bar.source_id, bar.source_release_id,
            ])


def write_records(path: Path, records) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            payload = {
                "term_record_id": record.term_record_id,
                "term_id": record.term_id,
                "term_version": record.term_version,
                "instrument_id": record.instrument_id,
                "timeframe": record.timeframe,
                "direction": record.direction.value,
                "anchor_time": record.anchor_time.isoformat(),
                "first_valid_time": record.first_valid_time.isoformat(),
                "status": record.status.value,
                "measurements": dict(record.measurements),
                "reference_level_id": record.reference_level_id,
                "input_bar_ids": list(record.input_bar_ids),
                "source_release_id": record.source_release_id,
                "parameter_set_id": record.parameter_set_id,
                "reason_codes": list(record.reason_codes),
            }
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()

    source_hash = hashlib.sha256(args.input_csv.read_bytes()).hexdigest()
    release_id = f"dukascopy-gbpusd-bid-{source_hash[:16]}"
    output = args.output_directory
    output.mkdir(parents=True, exist_ok=True)

    raw = read_dukascopy_csv(args.input_csv, source_release_id=release_id)
    gaps = []
    for left, right in zip(raw, raw[1:]):
        if right.open_time != left.close_time:
            missing = int((right.open_time - left.close_time).total_seconds() // 60)
            gaps.append({
                "start_utc": left.close_time.isoformat(),
                "end_utc": right.open_time.isoformat(),
                "missing_minutes": missing,
            })
    closure_like_gaps = [gap for gap in gaps if gap["missing_minutes"] >= 360]
    sparse_gaps = [gap for gap in gaps if gap["missing_minutes"] < 360]
    fifteen = aggregate_bars(raw, target_timeframe="15M")
    two_hour = aggregate_bars(fifteen.accepted, target_timeframe="2H")
    replay_15m = replay_unlevelled_terms(fifteen.accepted)
    replay_2h = replay_unlevelled_terms(two_hour.accepted)
    confirmed_records = [record for record in replay_15m.records if record.status.value == "CONFIRMED"]
    confirmed_2h_records = [record for record in replay_2h.records if record.status.value == "CONFIRMED"]

    report = {
        "report_version": "OVC-INGEST-0.2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "provider": "DUKASCOPY_HISTORICAL_EXPORT",
            "instrument": "GBPUSD",
            "price_side": "BID",
            "input_filename": args.input_csv.name,
            "sha256": source_hash,
            "source_release_id": release_id,
            "observed_rows": len(raw),
            "first_open_utc": raw[0].open_time.isoformat(),
            "last_close_utc": raw[-1].close_time.isoformat(),
        },
        "minute_gaps": gaps,
        "missing_minutes_total": sum(gap["missing_minutes"] for gap in gaps),
        "gap_summary": {
            "classification_rule": (
                "Gaps of at least 360 minutes are closure-like discontinuities; shorter gaps are sparse "
                "provider intervals. This is a structural classification, not an economic-session calendar."
            ),
            "closure_like": {
                "count": len(closure_like_gaps),
                "missing_minutes": sum(gap["missing_minutes"] for gap in closure_like_gaps),
            },
            "sparse": {
                "count": len(sparse_gaps),
                "missing_minutes": sum(gap["missing_minutes"] for gap in sparse_gaps),
            },
        },
        "aggregation": {
            "15M": {
                "accepted": len(fifteen.accepted),
                "rejected": [asdict(item) | {"bucket_start": item.bucket_start.isoformat()} for item in fifteen.rejected],
            },
            "2H": {
                "accepted": len(two_hour.accepted),
                "rejected": [asdict(item) | {"bucket_start": item.bucket_start.isoformat()} for item in two_hour.rejected],
            },
        },
        "unlevelled_replay": {
            "15M": {"segment_lengths": replay_15m.segment_lengths, "status_counts": replay_15m.status_counts},
            "2H": {"segment_lengths": replay_2h.segment_lengths, "status_counts": replay_2h.status_counts},
            "confirmed_15M": [
                {
                    "term_record_id": record.term_record_id,
                    "term_id": record.term_id,
                    "first_valid_time": record.first_valid_time.isoformat(),
                    "direction": record.direction.value,
                    "measurements": dict(record.measurements),
                }
                for record in confirmed_records
            ],
            "excluded_terms": [
                "REFERENCE_LEVEL_BREACH_AND_RESPONSE", "RECLAIM", "ACCEPTANCE", "REJECTION", "TRANSITION"
            ],
            "exclusion_reason": "No versioned reference-level registry or resolved state stream exists for this source release.",
        },
    }
    (output / "ingestion_report.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    write_bars(output / "accepted_15m.csv", fifteen.accepted)
    write_bars(output / "accepted_2h.csv", two_hour.accepted)
    write_records(output / "opt_b_unlevelled_records_15m.jsonl", replay_15m.records)
    write_records(output / "opt_b_unlevelled_records_2h.jsonl", replay_2h.records)

    confirmed = {
        key.removeprefix("B.TERM.").removesuffix(".v0.1:CONFIRMED"): value
        for key, value in replay_15m.status_counts.items()
        if key.endswith(":CONFIRMED")
    }
    segment_lengths = list(replay_15m.segment_lengths)
    segment_summary = (
        f"{len(segment_lengths)} segments; min {min(segment_lengths)}, median {median(segment_lengths):g}, "
        f"max {max(segment_lengths)} bars"
        if segment_lengths else "none"
    )
    total_15m_buckets = len(fifteen.accepted) + len(fifteen.rejected)
    total_2h_buckets = len(two_hour.accepted) + len(two_hour.rejected)
    accepted_15m_rate = len(fifteen.accepted) / total_15m_buckets if total_15m_buckets else 0
    accepted_2h_rate = len(two_hour.accepted) / total_2h_buckets if total_2h_buckets else 0
    markdown = f"""# OVC Dukascopy Minute-Source Ingestion Report

**Status:** INGESTED WITH QUARANTINED GAPS — RESEARCH ONLY  
**Source release:** `{release_id}`  
**Source SHA-256:** `{source_hash}`

## Result

- Source rows: {len(raw):,}
- UTC coverage: `{raw[0].open_time.isoformat()}` to `{raw[-1].close_time.isoformat()}`
- Long closure-like discontinuities: {len(closure_like_gaps)} containing {sum(gap['missing_minutes'] for gap in closure_like_gaps):,} absent minutes
- Short sparse intervals: {len(sparse_gaps)} containing {sum(gap['missing_minutes'] for gap in sparse_gaps):,} absent minutes
- Accepted 15M bars: {len(fifteen.accepted):,} ({accepted_15m_rate:.2%})
- Rejected 15M buckets: {len(fifteen.rejected):,}
- Accepted complete 2H bars: {len(two_hour.accepted):,} ({accepted_2h_rate:.2%})
- Rejected/partial 2H buckets: {len(two_hour.rejected):,}
- Contiguous 15M coverage: {segment_summary}
- Confirmed unlevelled OPT-B terms: {confirmed or 'none'}
- Confirmed 2H unlevelled OPT-B terms: {len(confirmed_2h_records)}

## Interpretation boundary

Only `COMPRESSION` and `DISPLACEMENT` were eligible for replay. Level-dependent terms and `TRANSITION` were not run because no versioned reference-level registry or resolved state stream exists. Rejected buckets were not repaired, no flat candles were manufactured, and no classifier window crossed a gap. The JSON report retains every gap and rejected-bucket record; the JSONL files retain the full replay evidence.

The long/short gap split is a deterministic structural classification: gaps of at least six hours are closure-like. It does not claim that a versioned economic-session calendar has been applied.

The 2H replay uses only complete `1M -> 15M -> 2H` chains. Its results therefore remain isolated from the separate hourly-source replay.
"""
    (output / "OVC_DUKASCOPY_M1_INGESTION_REPORT.md").write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
