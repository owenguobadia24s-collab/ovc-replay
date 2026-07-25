from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import gzip
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, sha256, verify_seal  # noqa: E402
from ovc_opt_b import expected_15m_open_times, measure_neutral_path  # noqa: E402
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402


MEASUREMENT_VERSION = "OPT-C-MEASURE-0.1.1"
MEASURED_HORIZONS = (1, 2, 4, 8, 12)
EVENT_CLOCKS = ("15M", "2H")


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


def load_jsonl_gzip(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def percentile(values: list[Decimal], fraction: Decimal) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return str(ordered[0])
    position = fraction * Decimal(len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - Decimal(lower)
    return str(ordered[lower] + (ordered[upper] - ordered[lower]) * weight)


def distribution(values: list[Decimal]) -> dict[str, object]:
    return {
        "count": len(values),
        "p10": percentile(values, Decimal("0.10")),
        "median": percentile(values, Decimal("0.50")),
        "p90": percentile(values, Decimal("0.90")),
    }


def compact_state(row: dict[str, object]) -> dict[str, object]:
    return {
        "acceptance_event_state": row["acceptance_event_state"],
        "acceptance_frontier_summary": row["acceptance_frontier_summary"],
        "displacement_state": row["displacement_state"],
        "compression_state": row["compression_state"],
        "interaction_state": row["interaction_state"],
        "quality_state": row["quality_state"],
    }


def transition_lineage(
    anchor_time: datetime,
    endpoint_time: datetime,
    *,
    transition_times: list[datetime],
    transitions: list[dict[str, object]],
) -> dict[str, object]:
    start = bisect_right(transition_times, anchor_time)
    end = bisect_right(transition_times, endpoint_time)
    selected = transitions[start:end]
    ids = [item["transition_record_id"] for item in selected]
    return {
        "timeframe": "15M",
        "transition_count": len(selected),
        "counts_by_axis": dict(sorted(Counter(item["axis"] for item in selected).items())),
        "transition_record_ids_hash": canonical_hash(ids),
    }


def summarize(records: list[dict[str, object]]) -> dict[str, object]:
    directions = Counter(row["event_direction"] for row in records)
    horizons: dict[str, object] = {}
    for horizon in MEASURED_HORIZONS:
        subset = [row for row in records if row["horizon_hours"] == horizon]
        directional = [row for row in subset if row["measurements"]["direction_normalization_status"] == "DIRECTIONAL"]
        frontier = [row for row in directional if row["measurements"]["primary_frontier_type"] is not None]
        horizons[str(horizon)] = {
            "records": len(subset),
            "overlap_records": sum(bool(row["overlap"]["overlap_present"]) for row in subset),
            "directional_records": len(directional),
            "raw_return_pips": distribution([Decimal(row["measurements"]["raw_return_pips"]) for row in subset]),
            "maximum_upward_excursion_pips": distribution(
                [Decimal(row["measurements"]["maximum_upward_excursion_pips"]) for row in subset]
            ),
            "maximum_downward_excursion_pips": distribution(
                [Decimal(row["measurements"]["maximum_downward_excursion_pips"]) for row in subset]
            ),
            "direction_normalized_endpoint_return_pips": distribution(
                [Decimal(row["measurements"]["direction_normalized_endpoint_return_pips"]) for row in directional]
            ),
            "direction_normalized_favorable_excursion_pips": distribution(
                [Decimal(row["measurements"]["direction_normalized_favorable_excursion_pips"]) for row in directional]
            ),
            "direction_normalized_adverse_excursion_pips": distribution(
                [Decimal(row["measurements"]["direction_normalized_adverse_excursion_pips"]) for row in directional]
            ),
            "continued_beyond_event_extreme_count": sum(
                row["measurements"]["continued_beyond_event_extreme"] is True for row in directional
            ),
            "primary_frontier_applicable_count": len(frontier),
            "primary_frontier_retested_count": sum(
                row["measurements"]["primary_frontier_retested"] is True for row in frontier
            ),
            "primary_frontier_lost_on_close_count": sum(
                row["measurements"]["primary_frontier_lost_on_close"] is True for row in frontier
            ),
        }
    return {
        "outcome_records": len(records),
        "direction_counts": dict(sorted(directions.items())),
        "horizons": horizons,
    }


def make_record(
    coverage: dict[str, object],
    anchor: dict[str, object],
    *,
    path_bars: tuple[object, ...],
    anchor_bar: object,
    endpoint_state: dict[str, object],
    transition_lineage_value: dict[str, object],
) -> dict[str, object]:
    measurements = measure_neutral_path(
        anchor_time=datetime.fromisoformat(anchor["anchor_time"]),
        anchor_price=Decimal(anchor["anchor_price"]),
        event_direction_value=anchor["event_direction"],
        event_bar_high=anchor_bar.high,
        event_bar_low=anchor_bar.low,
        path_bars=path_bars,
        frontier_summary=anchor["b_state_snapshot"]["acceptance_frontier_summary"],
    )
    core = {
        "event_anchor_id": anchor["event_anchor_id"],
        "coverage_record_id": coverage["coverage_record_id"],
        "instrument_id": anchor["instrument_id"],
        "event_timeframe": anchor["event_timeframe"],
        "anchor_time": anchor["anchor_time"],
        "endpoint_time": coverage["endpoint_time"],
        "horizon_hours": coverage["horizon_hours"],
        "event_direction": anchor["event_direction"],
        "event_families": anchor["event_families"],
        "anchor_price": anchor["anchor_price"],
        "price_side": "BID",
        "pip_size": "0.0001",
        "path_bar_count": len(path_bars),
        "path_bar_ids_hash": coverage["path_bar_ids_hash"],
        "overlap": coverage["overlap"],
        "measurements": measurements,
        "endpoint_b_state_timeframe": "15M",
        "endpoint_b_state_record_id": endpoint_state["state_record_id"],
        "endpoint_b_state_snapshot": compact_state(endpoint_state),
        "transition_lineage": transition_lineage_value,
        "outcome_status": "MEASURED_COMPLETE_PATH",
        "measurement_contract_version": MEASUREMENT_VERSION,
        "parent_opt_c_contract_version": "OPT-C-OUTCOME-0.1",
        "coverage_contract_version": "OPT-C-COVERAGE-0.1",
        "authority": "DESCRIPTIVE_NEUTRAL_MEASUREMENT_ONLY",
    }
    return {**core, "neutral_outcome_record_id": f"opt-c-neutral:{canonical_hash(core)}"}


def write_report(output: Path, results: dict[str, object]) -> Path:
    total = sum(results[clock]["outcome_records"] for clock in EVENT_CLOCKS)
    lines = [
        "# OVC OPT-C Neutral Forward-Outcome Measurement Report v0.1",
        "",
        "**Status:** `MEASUREMENT COMPLETE — DESCRIPTIVE ONLY — NOT AN EDGE CLAIM`  ",
        f"**Measurement contract:** `{MEASUREMENT_VERSION}`  ",
        f"**Measured complete event–horizon pairs:** **{total:,}**",
        "",
        "## Strict measured coverage",
        "",
        "| Event clock | 1h | 2h | 4h | 8h | 12h | Total |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for clock in EVENT_CLOCKS:
        counts = [results[clock]["horizons"][str(h)]["records"] for h in MEASURED_HORIZONS]
        lines.append(f"| {clock} | " + " | ".join(f"{value:,}" for value in counts) + f" | {sum(counts):,} |")
    lines.extend([
        "",
        "Only coverage records marked `COMPLETE` at 1h, 2h, 4h, 8h and 12h were measured. Censored paths received no outcome row. The 24h horizon remains coverage-only and 48h remains blocked.",
        "",
        "## Neutral descriptive medians",
        "",
        "| Event clock | Horizon | Raw return | Up excursion | Down excursion | Direction-normalized return |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for clock in EVENT_CLOCKS:
        for horizon in MEASURED_HORIZONS:
            item = results[clock]["horizons"][str(horizon)]
            lines.append(
                f"| {clock} | {horizon}h | {item['raw_return_pips']['median']} pips | "
                f"{item['maximum_upward_excursion_pips']['median']} pips | "
                f"{item['maximum_downward_excursion_pips']['median']} pips | "
                f"{item['direction_normalized_endpoint_return_pips']['median']} pips |"
            )
    lines.extend([
        "",
        "These are overlapping structural-event observations. They are not independent samples and are not wins, losses, trades, expected returns or evidence of profitability.",
        "",
        "## Lineage and reproducibility",
        "",
        "Every row binds the event anchor, coverage record, ordered 15M path, endpoint ratified 15M B-state and all intervening 15M state transitions. All prices are sealed provider BID values; no missing interval was filled.",
        "",
        "## Next gate",
        "",
        "Run the independent semantic sanity review: verify measure distributions, overlap strata, family/direction support and frontier applicability before any OPT-D cohort construction.",
    ])
    path = output / "OVC_OPT_C_NEUTRAL_FORWARD_OUTCOME_MEASUREMENT_REPORT_v0_1_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--coverage-root", type=Path, required=True)
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ledger_root = args.ledger_root.resolve()
    coverage_root = args.coverage_root.resolve()
    seal_root = args.seal_root.resolve()
    state_root = args.state_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json").exists():
        raise FileExistsError("OPT-C neutral outcome release already finalized")

    seal = verify_seal(seal_root)
    ledger_manifest = verify_manifest(ledger_root, "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    coverage_manifest = verify_manifest(coverage_root, "OPT_C_FORWARD_PATH_COVERAGE_MANIFEST.json")
    state_manifest = verify_manifest(state_root, "B_STATE_0_3B_RATIFIED_MANIFEST.json")
    if coverage_manifest["event_ledger_manifest_hash"] != ledger_manifest["manifest_hash"]:
        raise ValueError("coverage/event-ledger lineage mismatch")
    if ledger_manifest["b_state_manifest_hash"] != state_manifest["manifest_hash"]:
        raise ValueError("event-ledger/B-state lineage mismatch")
    if {ledger_manifest["opt_a_seal_hash"], coverage_manifest["opt_a_seal_hash"]} != {seal["seal_hash"]}:
        raise ValueError("OPT-A seal lineage mismatch")

    bars = {
        clock: read_canonical_bars(seal_root / f"canonical/accepted_{clock.lower()}.csv")
        for clock in EVENT_CLOCKS
    }
    path_bars_by_open = {bar.open_time: bar for bar in bars["15M"]}
    event_bar_by_id = {clock: {bar.bar_id: bar for bar in items} for clock, items in bars.items()}
    states = list(load_jsonl_gzip(state_root / "ratified_parallel_axis_state_stream_15m.jsonl.gz"))
    state_by_time = {datetime.fromisoformat(row["close_time"]): row for row in states}
    transitions = list(load_jsonl_gzip(state_root / "ratified_parallel_axis_transitions_15m.jsonl.gz"))
    transitions.sort(key=lambda item: (item["at"], item["transition_record_id"]))
    transition_times = [datetime.fromisoformat(item["at"]) for item in transitions]

    artifacts = []
    results = {}
    expected_total = 0
    for clock in EVENT_CLOCKS:
        anchors = {
            row["event_anchor_id"]: row
            for row in load_jsonl_gzip(ledger_root / f"opt_c_event_anchor_ledger_{clock.lower()}.jsonl.gz")
        }
        records = []
        output_path = output / f"opt_c_neutral_outcomes_{clock.lower()}.jsonl.gz"
        writer = DeterministicJsonlGzipWriter(output_path)
        for coverage in load_jsonl_gzip(
            coverage_root / f"opt_c_forward_path_coverage_{clock.lower()}.jsonl.gz"
        ):
            if coverage["horizon_hours"] not in MEASURED_HORIZONS or coverage["coverage_status"] != "COMPLETE":
                continue
            anchor = anchors[coverage["event_anchor_id"]]
            anchor_time = datetime.fromisoformat(anchor["anchor_time"])
            expected_opens = expected_15m_open_times(anchor_time, coverage["horizon_hours"])
            path_bars = tuple(path_bars_by_open[at] for at in expected_opens)
            if canonical_hash([bar.bar_id for bar in path_bars]) != coverage["path_bar_ids_hash"]:
                raise ValueError("coverage path hash mismatch during measurement")
            endpoint_time = datetime.fromisoformat(coverage["endpoint_time"])
            endpoint_state = state_by_time.get(endpoint_time)
            if endpoint_state is None:
                raise ValueError("complete path has no exact ratified 15M endpoint state")
            record = make_record(
                coverage,
                anchor,
                path_bars=path_bars,
                anchor_bar=event_bar_by_id[clock][anchor["anchor_bar_id"]],
                endpoint_state=endpoint_state,
                transition_lineage_value=transition_lineage(
                    anchor_time,
                    endpoint_time,
                    transition_times=transition_times,
                    transitions=transitions,
                ),
            )
            writer.write(record)
            records.append(record)
        writer.close()
        expected_total += writer.count
        results[clock] = {
            **summarize(records),
            "outcome_stream_canonical_jsonl_hash": writer.canonical_jsonl_hash,
        }
        artifacts.append({"path": output_path.name, "sha256": sha256(output_path), "size_bytes": output_path.stat().st_size})
        print(f"{clock}: measured {writer.count:,} complete event–horizon pairs", flush=True)

    summary_path = output / "opt_c_neutral_outcome_measurement_summary.json"
    summary_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    report_path = write_report(output, results)
    artifacts.append({"path": report_path.name, "sha256": sha256(report_path), "size_bytes": report_path.stat().st_size})
    for source in (
        ROOT / "contracts/OVC_OPT_C_NEUTRAL_MEASUREMENT_IMPLEMENTATION_CONTRACT_v0_1_1.md",
        ROOT / "contracts/OPT_C_MEASURE_0_1_1_FRONTIER_NULLABILITY_REPAIR_RECORD.md",
        ROOT / "contracts/OVC_OPT_C_FORWARD_PATH_COVERAGE_CENSORING_CONTRACT_v0_1.md",
        ROOT / "contracts/OVC_OPT_C_NEUTRAL_FORWARD_OUTCOME_CONTRACT_v0_1.md",
        ROOT / "contracts/OPT_C_OUTCOME_0_1_APPROVAL_RECORD.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    manifest_core = {
        "release_id": "OPT-C-NEUTRAL-MEASUREMENTS-GBPUSD-2026H1-v0.1.1",
        "status": "NEUTRAL_OUTCOME_MEASUREMENT_COMPLETE_DESCRIPTIVE_ONLY",
        "generated_date": "2026-07-19",
        "measurement_contract_version": MEASUREMENT_VERSION,
        "parent_opt_c_contract_version": "OPT-C-OUTCOME-0.1",
        "coverage_contract_version": "OPT-C-COVERAGE-0.1",
        "opt_a_seal_hash": seal["seal_hash"],
        "b_state_manifest_hash": state_manifest["manifest_hash"],
        "event_ledger_manifest_hash": ledger_manifest["manifest_hash"],
        "coverage_manifest_hash": coverage_manifest["manifest_hash"],
        "measured_horizons_hours": list(MEASURED_HORIZONS),
        "coverage_only_horizons_hours": [24],
        "blocked_horizons_hours": [48],
        "censored_path_policy": "NO_OUTCOME_ROW",
        "total_outcome_records": expected_total,
        "results": results,
        "artifacts": artifacts,
        "implementation_hashes": {
            "opt_c.py": sha256(ROOT / "src/ovc_opt_b/opt_c.py"),
            "measure_opt_c_neutral_outcomes.py": sha256(Path(__file__).resolve()),
            "test_opt_c.py": sha256(ROOT / "tests/test_opt_c.py"),
        },
        "authority_boundary": "Neutral descriptive measurements on complete sealed BID paths only. No edge, recommendation, risk, trade or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    (output / "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": manifest["status"], "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
