from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

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
            handle.write(json.dumps({
                "term_record_id": record.term_record_id,
                "term_id": record.term_id,
                "term_version": record.term_version,
                "direction": record.direction.value,
                "anchor_time": record.anchor_time.isoformat(),
                "first_valid_time": record.first_valid_time.isoformat(),
                "status": record.status.value,
                "measurements": dict(record.measurements),
                "input_bar_ids": list(record.input_bar_ids),
                "source_release_id": record.source_release_id,
                "parameter_set_id": record.parameter_set_id,
                "reason_codes": list(record.reason_codes),
            }, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("input_csv", nargs="+", type=Path)
    args = parser.parse_args()

    files = sorted(args.input_csv)
    file_hashes = [(path.name, hashlib.sha256(path.read_bytes()).hexdigest()) for path in files]
    combined_hash = hashlib.sha256("\n".join(f"{name}:{digest}" for name, digest in file_hashes).encode()).hexdigest()
    release_id = f"dukascopy-gbpusd-bid-1h-{combined_hash[:16]}"
    hourly = []
    for path in files:
        hourly.extend(read_dukascopy_csv(path, source_release_id=release_id, source_timeframe="1H"))
    hourly.sort(key=lambda bar: bar.open_time)
    for left, right in zip(hourly, hourly[1:]):
        if right.open_time <= left.open_time:
            raise ValueError(f"duplicate/non-monotonic combined timestamp: {right.open_time.isoformat()}")

    discontinuities = []
    for left, right in zip(hourly, hourly[1:]):
        if right.open_time != left.close_time:
            hours = int((right.open_time - left.close_time).total_seconds() // 3600)
            discontinuities.append({
                "start_utc": left.close_time.isoformat(),
                "end_utc": right.open_time.isoformat(),
                "missing_hours": hours,
                "classification": "EXPECTED_WEEKEND_OR_CLOSURE" if hours >= 24 else "UNEXPLAINED_INTRAWEEK_GAP",
            })

    two_hour = aggregate_bars(hourly, target_timeframe="2H")
    replay = replay_unlevelled_terms(two_hour.accepted)
    confirmed = [record for record in replay.records if record.status.value == "CONFIRMED"]
    by_month: dict[str, Counter] = defaultdict(Counter)
    evaluated_by_month: dict[str, Counter] = defaultdict(Counter)
    for record in replay.records:
        evaluated_by_month[record.first_valid_time.strftime("%Y-%m")][record.term_id] += 1
    for record in confirmed:
        by_month[record.first_valid_time.strftime("%Y-%m")][record.term_id] += 1

    output = args.output_directory
    output.mkdir(parents=True, exist_ok=True)
    write_bars(output / "accepted_2h.csv", two_hour.accepted)
    write_records(output / "opt_b_unlevelled_records_2h.jsonl", replay.records)

    report = {
        "report_version": "OVC-INGEST-0.1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_release_id": release_id,
        "combined_manifest_sha256": combined_hash,
        "source_files": [{"filename": name, "sha256": digest} for name, digest in file_hashes],
        "source_rows_1H": len(hourly),
        "coverage": {"first_open_utc": hourly[0].open_time.isoformat(), "last_close_utc": hourly[-1].close_time.isoformat()},
        "discontinuities": discontinuities,
        "unexplained_intraweek_gap_count": sum(item["classification"] == "UNEXPLAINED_INTRAWEEK_GAP" for item in discontinuities),
        "aggregation_2H": {
            "accepted": len(two_hour.accepted),
            "rejected": [asdict(item) | {"bucket_start": item.bucket_start.isoformat()} for item in two_hour.rejected],
        },
        "replay": {
            "segment_lengths": replay.segment_lengths,
            "status_counts": replay.status_counts,
            "confirmed_by_month": {month: dict(sorted(counts.items())) for month, counts in sorted(by_month.items())},
            "evaluated_by_month": {month: dict(sorted(counts.items())) for month, counts in sorted(evaluated_by_month.items())},
            "confirmed_records": [{
                "term_record_id": record.term_record_id,
                "term_id": record.term_id,
                "first_valid_time": record.first_valid_time.isoformat(),
                "direction": record.direction.value,
                "measurements": dict(record.measurements),
            } for record in confirmed],
        },
        "scope_boundary": "1H source supports 2H replay only; no 15M series was reconstructed.",
    }
    (output / "ingestion_report.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    status_rows = "\n".join(f"| {key} | {value} |" for key, value in replay.status_counts.items())
    months = sorted(set(by_month) | set(evaluated_by_month))
    month_rows = "\n".join(
        "| {month} | {dc}/{de} | {dr:.2%} | {cc}/{ce} | {cr:.2%} |".format(
            month=month,
            dc=by_month[month].get("B.TERM.DISPLACEMENT.v0.1", 0),
            de=evaluated_by_month[month].get("B.TERM.DISPLACEMENT.v0.1", 0),
            dr=(by_month[month].get("B.TERM.DISPLACEMENT.v0.1", 0) / evaluated_by_month[month].get("B.TERM.DISPLACEMENT.v0.1", 1)),
            cc=by_month[month].get("B.TERM.COMPRESSION.v0.1", 0),
            ce=evaluated_by_month[month].get("B.TERM.COMPRESSION.v0.1", 0),
            cr=(by_month[month].get("B.TERM.COMPRESSION.v0.1", 0) / evaluated_by_month[month].get("B.TERM.COMPRESSION.v0.1", 1)),
        )
        for month in months
    )
    markdown = f"""# OVC Dukascopy 2H Replay Report — January to June 2026

**Status:** HISTORICAL 2H REPLAY COMPLETED — RESEARCH ONLY  
**Source release:** `{release_id}`  
**Manifest SHA-256:** `{combined_hash}`

## Ingestion result

- Source files: {len(files)}
- Accepted 1H rows: {len(hourly):,}
- UTC coverage: `{hourly[0].open_time.isoformat()}` to `{hourly[-1].close_time.isoformat()}`
- Discontinuities: {len(discontinuities)}
- Unexplained intraweek gaps: {report['unexplained_intraweek_gap_count']}
- Accepted complete 2H bars: {len(two_hour.accepted):,}
- Rejected 2H buckets: {len(two_hour.rejected)}
- Contiguous weekly/closure-separated segments: {list(replay.segment_lengths)}

## Replay counts

| Term and status | Count |
|---|---:|
{status_rows}

## Confirmed terms by month

| Month | Displacement confirmed/evaluated | Rate | Compression confirmed/evaluated | Rate |
|---|---:|---:|---:|---:|
{month_rows}

The `2026-07` row is the close timestamp of the final `[2026-06-30 22:00, 2026-07-01 00:00)` UTC bucket; it does not represent a July source file.

## Boundary

The source resolution is 1H. It supports direct 2H aggregation but cannot reconstruct 15M detail. Level-dependent terms and `TRANSITION` remain excluded until the reference-level registry and resolved state stream are implemented. Confirmed terms are structural classifications, not signals or evidence of edge.
"""
    (output / "OVC_DUKASCOPY_2H_REPLAY_REPORT_2026_H1.md").write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
