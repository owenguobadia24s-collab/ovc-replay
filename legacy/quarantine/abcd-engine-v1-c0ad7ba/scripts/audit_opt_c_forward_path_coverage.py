from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from datetime import datetime
import gzip
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, sha256, verify_seal  # noqa: E402
from ovc_opt_b import OPT_C_HORIZONS_HOURS, assess_15m_path_coverage  # noqa: E402
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402


COVERAGE_VERSION = "OPT-C-COVERAGE-0.1"
PARENT_CONTRACT = "OPT-C-OUTCOME-0.1"


def verify_manifest(root: Path, name: str) -> dict[str, object]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError(f"manifest self-hash mismatch: {name}")
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        if sha256(path) != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
    return manifest


def load_anchors(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def overlap_metadata(
    anchor: dict[str, object],
    endpoint: datetime,
    *,
    all_times: list[datetime],
    all_ids: list[str],
    clock_times: list[datetime],
) -> dict[str, object]:
    at = datetime.fromisoformat(anchor["anchor_time"])
    same_start = bisect_left(all_times, at)
    same_end = bisect_right(all_times, at)
    same_ids = [item for item in all_ids[same_start:same_end] if item != anchor["event_anchor_id"]]
    future_start = same_end
    future_end = bisect_right(all_times, endpoint)
    future_ids = all_ids[future_start:future_end]
    same_clock_future = bisect_right(clock_times, endpoint) - bisect_right(clock_times, at)
    overlap_ids = sorted((*same_ids, *future_ids))
    return {
        "same_time_other_anchor_count": len(same_ids),
        "subsequent_overlap_anchor_count_all_clocks": len(future_ids),
        "subsequent_overlap_anchor_count_same_clock": same_clock_future,
        "overlap_present": bool(overlap_ids),
        "overlap_anchor_ids_hash": canonical_hash(overlap_ids) if overlap_ids else None,
    }


def assessment_dict(assessment) -> dict[str, object]:
    return {
        "coverage_status": assessment.coverage_status,
        "censor_reasons": list(assessment.censor_reasons),
        "endpoint_time": assessment.endpoint_time.isoformat(),
        "expected_bar_count": assessment.expected_bar_count,
        "available_bar_count": assessment.available_bar_count,
        "missing_interval_count": assessment.missing_interval_count,
        "missing_run_count": assessment.missing_run_count,
        "max_missing_run_bars": assessment.max_missing_run_bars,
        "first_missing_open_time": (
            assessment.first_missing_open_time.isoformat() if assessment.first_missing_open_time else None
        ),
        "last_missing_open_time": (
            assessment.last_missing_open_time.isoformat() if assessment.last_missing_open_time else None
        ),
        "missing_open_times_hash": assessment.missing_open_times_hash,
        "available_bar_ids_hash": assessment.available_bar_ids_hash,
        "path_bar_ids_hash": assessment.path_bar_ids_hash,
    }


def audit_timeframe(
    *,
    timeframe: str,
    anchors: list[dict[str, object]],
    output: Path,
    bar_ids_by_open_time: dict[datetime, str],
    source_last_close_time: datetime,
    all_times: list[datetime],
    all_ids: list[str],
    clock_times: list[datetime],
) -> tuple[dict[str, object], dict[str, object]]:
    path = output / f"opt_c_forward_path_coverage_{timeframe.lower()}.jsonl.gz"
    writer = DeterministicJsonlGzipWriter(path)
    horizon_summary = {
        str(horizon): {
            "records": 0,
            "complete": 0,
            "censored": 0,
            "censor_reason_counts": Counter(),
            "missing_intervals": 0,
            "missing_runs": 0,
            "max_missing_run_bars": 0,
            "overlap_records": 0,
        }
        for horizon in OPT_C_HORIZONS_HOURS
    }
    family_summary = defaultdict(
        lambda: {
            str(horizon): {"records": 0, "complete": 0, "censored": 0}
            for horizon in OPT_C_HORIZONS_HOURS
        }
    )
    for anchor in anchors:
        anchor_time = datetime.fromisoformat(anchor["anchor_time"])
        for horizon in OPT_C_HORIZONS_HOURS:
            assessment = assess_15m_path_coverage(
                anchor_time,
                horizon,
                bar_ids_by_open_time=bar_ids_by_open_time,
                source_last_close_time=source_last_close_time,
            )
            overlap = overlap_metadata(
                anchor,
                assessment.endpoint_time,
                all_times=all_times,
                all_ids=all_ids,
                clock_times=clock_times,
            )
            core = {
                "event_anchor_id": anchor["event_anchor_id"],
                "instrument_id": anchor["instrument_id"],
                "event_timeframe": timeframe,
                "anchor_time": anchor["anchor_time"],
                "event_direction": anchor["event_direction"],
                "event_families": anchor["event_families"],
                "horizon_hours": horizon,
                **assessment_dict(assessment),
                "overlap": overlap,
                "coverage_contract_version": COVERAGE_VERSION,
                "parent_opt_c_contract_version": PARENT_CONTRACT,
                "event_ledger_manifest_role": "MANIFEST_BOUND_PARENT",
            }
            record = {**core, "coverage_record_id": f"opt-c-coverage:{canonical_hash(core)}"}
            writer.write(record)
            item = horizon_summary[str(horizon)]
            item["records"] += 1
            item[assessment.coverage_status.lower()] += 1
            item["censor_reason_counts"].update(assessment.censor_reasons)
            item["missing_intervals"] += assessment.missing_interval_count
            item["missing_runs"] += assessment.missing_run_count
            item["max_missing_run_bars"] = max(item["max_missing_run_bars"], assessment.max_missing_run_bars)
            item["overlap_records"] += int(overlap["overlap_present"])
            for family in anchor["event_families"]:
                family_item = family_summary[family][str(horizon)]
                family_item["records"] += 1
                family_item[assessment.coverage_status.lower()] += 1
    writer.close()

    normalized_horizons = {}
    for horizon, item in horizon_summary.items():
        normalized_horizons[horizon] = {
            **{key: value for key, value in item.items() if key != "censor_reason_counts"},
            "complete_rate_pct": round(item["complete"] * 100 / item["records"], 4) if item["records"] else 0.0,
            "censored_rate_pct": round(item["censored"] * 100 / item["records"], 4) if item["records"] else 0.0,
            "overlap_rate_pct": round(item["overlap_records"] * 100 / item["records"], 4) if item["records"] else 0.0,
            "censor_reason_counts": dict(sorted(item["censor_reason_counts"].items())),
        }
    normalized_families = {
        family: {
            horizon: {
                **item,
                "complete_rate_pct": round(item["complete"] * 100 / item["records"], 4) if item["records"] else 0.0,
            }
            for horizon, item in horizons.items()
        }
        for family, horizons in sorted(family_summary.items())
    }
    summary = {
        "anchors": len(anchors),
        "coverage_records": writer.count,
        "horizons": normalized_horizons,
        "family_horizon_coverage": normalized_families,
        "coverage_stream_canonical_jsonl_hash": writer.canonical_jsonl_hash,
    }
    artifact = {"path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size}
    return summary, artifact


def write_report(output: Path, results: dict[str, object]) -> Path:
    complete_24h = sum(results[timeframe]["horizons"]["24"]["complete"] for timeframe in ("15M", "2H"))
    complete_48h = sum(results[timeframe]["horizons"]["48"]["complete"] for timeframe in ("15M", "2H"))
    lines = [
        "# OVC OPT-C Strict Forward-Path Coverage and Censoring Audit",
        "",
        "**Status:** `AUDIT COMPLETE — PARTIAL MEASUREMENT READINESS — 48H BLOCKED`  ",
        f"**Coverage contract:** `{COVERAGE_VERSION}`  ",
        "**Forward price values read:** `NO`",
        "",
        "## Coverage by horizon",
        "",
        "| Clock | Horizon | Complete | Censored | Complete rate | Overlap rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for timeframe in ("15M", "2H"):
        for horizon in OPT_C_HORIZONS_HOURS:
            item = results[timeframe]["horizons"][str(horizon)]
            lines.append(
                f"| {timeframe} | {horizon}h | {item['complete']:,} | {item['censored']:,} | "
                f"{item['complete_rate_pct']:.2f}% | {item['overlap_rate_pct']:.2f}% |"
            )
    lines.extend([
        "",
        "## Censoring evidence",
        "",
        "| Clock | Horizon | Missing intervals | Missing runs | Longest missing run | Source-end truncations |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for timeframe in ("15M", "2H"):
        for horizon in OPT_C_HORIZONS_HOURS:
            item = results[timeframe]["horizons"][str(horizon)]
            lines.append(
                f"| {timeframe} | {horizon}h | {item['missing_intervals']:,} | {item['missing_runs']:,} | "
                f"{item['max_missing_run_bars']:,} bars | "
                f"{item['censor_reason_counts'].get('SOURCE_END_TRUNCATION', 0):,} |"
            )
    lines.extend([
        "",
        "A complete record has every exact 15M interval and an endpoint inside the sealed source. Every other record remains in the dataset with explicit censor evidence; no path was repaired or dropped.",
        "",
        "## Gate decision",
        "",
        "The neutral outcome engine may now measure only records marked `COMPLETE`. Censored records must receive no return, excursion or path-shape value. Overlap flags must travel with every measured outcome.",
        "",
        f"The 24h horizon has only **{complete_24h:,}** complete observations across both clocks and is not broad enough for cohort claims. The 48h horizon has **{complete_48h:,}** complete observations and is blocked from measurement. This is a sealed-source path-completeness constraint, not a B-STATE classification failure.",
    ])
    path = output / "OVC_OPT_C_FORWARD_PATH_COVERAGE_CENSORING_AUDIT_REPORT_v0_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ledger_root = args.ledger_root.resolve()
    seal_root = args.seal_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "OPT_C_FORWARD_PATH_COVERAGE_MANIFEST.json").exists():
        raise FileExistsError("OPT-C coverage audit already finalized")
    ledger_manifest = verify_manifest(ledger_root, "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    seal = verify_seal(seal_root)
    if ledger_manifest["opt_a_seal_hash"] != seal["seal_hash"]:
        raise ValueError("event ledger/OPT-A seal lineage mismatch")
    bars = read_canonical_bars(seal_root / "canonical/accepted_15m.csv")
    bar_ids_by_open_time = {bar.open_time: bar.bar_id for bar in bars}
    source_last_close_time = max(bar.close_time for bar in bars)
    anchors = {
        timeframe: load_anchors(ledger_root / f"opt_c_event_anchor_ledger_{timeframe.lower()}.jsonl.gz")
        for timeframe in ("15M", "2H")
    }
    all_entries = sorted(
        (
            datetime.fromisoformat(anchor["anchor_time"]),
            anchor["event_anchor_id"],
        )
        for items in anchors.values()
        for anchor in items
    )
    all_times = [item[0] for item in all_entries]
    all_ids = [item[1] for item in all_entries]
    clock_times = {
        timeframe: sorted(datetime.fromisoformat(anchor["anchor_time"]) for anchor in items)
        for timeframe, items in anchors.items()
    }

    results = {}
    artifacts = []
    for timeframe in ("15M", "2H"):
        print(f"{timeframe}: auditing {len(anchors[timeframe]):,} anchors × 7 horizons", flush=True)
        results[timeframe], artifact = audit_timeframe(
            timeframe=timeframe,
            anchors=anchors[timeframe],
            output=output,
            bar_ids_by_open_time=bar_ids_by_open_time,
            source_last_close_time=source_last_close_time,
            all_times=all_times,
            all_ids=all_ids,
            clock_times=clock_times[timeframe],
        )
        artifacts.append(artifact)

    summary_path = output / "opt_c_forward_path_coverage_summary.json"
    summary_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    report_path = write_report(output, results)
    artifacts.append({"path": report_path.name, "sha256": sha256(report_path), "size_bytes": report_path.stat().st_size})
    for source in (
        ROOT / "contracts/OVC_OPT_C_FORWARD_PATH_COVERAGE_CENSORING_CONTRACT_v0_1.md",
        ROOT / "contracts/OVC_OPT_C_NEUTRAL_FORWARD_OUTCOME_CONTRACT_v0_1.md",
        ROOT / "contracts/OPT_C_OUTCOME_0_1_APPROVAL_RECORD.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    manifest_core = {
        "release_id": "OPT-C-COVERAGE-GBPUSD-2026H1-v0.1",
        "status": "COVERAGE_AUDIT_COMPLETE_PARTIAL_MEASUREMENT_READINESS_48H_BLOCKED",
        "generated_date": "2026-07-19",
        "coverage_contract_version": COVERAGE_VERSION,
        "parent_opt_c_contract_version": PARENT_CONTRACT,
        "event_ledger_manifest_hash": ledger_manifest["manifest_hash"],
        "opt_a_seal_hash": seal["seal_hash"],
        "source_last_15m_close_time": source_last_close_time.isoformat(),
        "horizons_hours": list(OPT_C_HORIZONS_HOURS),
        "results": results,
        "artifacts": artifacts,
        "implementation_hashes": {
            "opt_c.py": sha256(ROOT / "src/ovc_opt_b/opt_c.py"),
            "audit_opt_c_forward_path_coverage.py": sha256(Path(__file__).resolve()),
            "test_opt_c.py": sha256(ROOT / "tests/test_opt_c.py"),
        },
        "authority_boundary": "Timestamp/bar-ID coverage evidence only. No forward OHLC value, outcome, edge, recommendation, risk or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    (output / "OPT_C_FORWARD_PATH_COVERAGE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": manifest["status"], "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
