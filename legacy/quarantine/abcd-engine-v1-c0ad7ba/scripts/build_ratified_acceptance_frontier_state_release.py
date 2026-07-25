from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import gzip
import json
from itertools import zip_longest
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402
from run_parallel_axis_state_replay import MetricTracker  # noqa: E402


CONTRACT_VERSION = "B-STATE-0.3b"
RATIFICATION_ID = "B-STATE-0.3b-FRONTIER-ACTIVE-RESEARCH"
EXPECTED_STEP = {"15M": timedelta(minutes=15), "2H": timedelta(hours=2)}


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


def is_active(state: str) -> bool:
    return state not in ("NONE", "CONFLICTING")


def pct(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) * 100 / float(denominator), 4) if denominator else 0.0


def transition_record(timeframe: str, at: str, axis: str, old: str, new: str) -> dict[str, object]:
    core = {
        "timeframe": timeframe,
        "at": at,
        "axis": axis,
        "from_state": old,
        "to_state": new,
        "state_contract_version": CONTRACT_VERSION,
        "ratification_id": RATIFICATION_ID,
    }
    return {**core, "transition_record_id": f"ratified-axis-transition:{canonical_hash(core)}"}


def state_record(review: dict[str, object]) -> dict[str, object]:
    core = {
        "instrument_id": review["instrument_id"],
        "timeframe": review["timeframe"],
        "close_time": review["close_time"],
        "acceptance_event_state": review["frontier_advance_event_state"],
        "acceptance_event_components": review["frontier_advance_components"],
        "acceptance_frontier_summary": review["acceptance_frontier_summary"],
        "full_relation_inventory_hash": review["full_relation_inventory_hash"],
        "parent_v03a_state_record_id": review["parent_state_record_id"],
        "semantic_review_state_record_id": review["review_state_record_id"],
        "displacement_state": review["displacement_state"],
        "compression_state": review["compression_state"],
        "interaction_state": review["interaction_state"],
        "interaction_components": review["interaction_components"],
        "quality_state": review["quality_state"],
        "genuine_conflict": bool(review["source_genuine_conflict"] or review["review_genuine_conflict"]),
        "state_contract_version": CONTRACT_VERSION,
        "ratification_id": RATIFICATION_ID,
    }
    return {**core, "state_record_id": f"ratified-frontier-state:{canonical_hash(core)}"}


def event_record(state: dict[str, object]) -> dict[str, object]:
    core = {
        "instrument_id": state["instrument_id"],
        "timeframe": state["timeframe"],
        "at": state["close_time"],
        "acceptance_event_state": state["acceptance_event_state"],
        "acceptance_event_components": state["acceptance_event_components"],
        "full_relation_inventory_hash": state["full_relation_inventory_hash"],
        "state_record_id": state["state_record_id"],
        "state_contract_version": CONTRACT_VERSION,
        "ratification_id": RATIFICATION_ID,
    }
    return {**core, "acceptance_event_record_id": f"ratified-frontier-event:{canonical_hash(core)}"}


def compile_timeframe(
    review_root: Path,
    parent_root: Path,
    output: Path,
    timeframe: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    review_path = review_root / f"acceptance_frontier_review_state_stream_{timeframe.lower()}.jsonl.gz"
    parent_path = parent_root / f"acceptance_relation_state_stream_{timeframe.lower()}.jsonl.gz"
    state_path = output / f"ratified_parallel_axis_state_stream_{timeframe.lower()}.jsonl.gz"
    event_path = output / f"ratified_acceptance_frontier_events_{timeframe.lower()}.jsonl.gz"
    transition_path = output / f"ratified_parallel_axis_transitions_{timeframe.lower()}.jsonl.gz"
    state_writer = DeterministicJsonlGzipWriter(state_path)
    event_writer = DeterministicJsonlGzipWriter(event_path)
    transition_writer = DeterministicJsonlGzipWriter(transition_path)
    axes = ("acceptance", "displacement", "compression", "interaction", "quality")
    trackers = {axis: MetricTracker() for axis in axes}
    acceptance_active = MetricTracker()
    any_axis_active = MetricTracker()
    monthly: dict[str, dict[str, int]] = {}
    previous_time = None
    previous_states = None
    projection_hash_checks = axis_checks = conflicts = 0

    with gzip.open(review_path, "rt", encoding="utf-8") as review_handle:
        with gzip.open(parent_path, "rt", encoding="utf-8") as parent_handle:
            for review_line, parent_line in zip_longest(review_handle, parent_handle):
                if review_line is None or parent_line is None:
                    raise ValueError("review/parent row cardinality mismatch")
                review = json.loads(review_line)
                parent = json.loads(parent_line)
                if review["close_time"] != parent["close_time"]:
                    raise ValueError("review/parent timestamp mismatch")
                if review["parent_state_record_id"] != parent["state_record_id"]:
                    raise ValueError("review/parent state-record lineage mismatch")
                if review["full_relation_inventory_hash"] != canonical_hash(parent["acceptance_relation_inventory"]):
                    raise ValueError("compact projection/full inventory hash mismatch")
                projection_hash_checks += 1
                for field in (
                    "displacement_state",
                    "compression_state",
                    "interaction_state",
                    "interaction_components",
                    "quality_state",
                ):
                    if review[field] != parent[field]:
                        raise ValueError(f"non-acceptance axis mismatch: {field}")
                axis_checks += 1

                record = state_record(review)
                state_writer.write(record)
                if is_active(record["acceptance_event_state"]):
                    event_writer.write(event_record(record))
                conflicts += int(record["genuine_conflict"])

                at = datetime.fromisoformat(record["close_time"])
                contiguous = previous_time is not None and at - previous_time == EXPECTED_STEP[timeframe]
                states = {
                    "acceptance": record["acceptance_event_state"],
                    "displacement": record["displacement_state"],
                    "compression": record["compression_state"],
                    "interaction": record["interaction_state"],
                    "quality": record["quality_state"],
                }
                for axis, value in states.items():
                    changed = trackers[axis].observe(value, contiguous=contiguous)
                    if changed and previous_states is not None:
                        transition_writer.write(
                            transition_record(timeframe, record["close_time"], axis.upper(), previous_states[axis], value)
                        )
                acceptance_active.observe(
                    "ACTIVE" if is_active(record["acceptance_event_state"]) else "INACTIVE",
                    contiguous=contiguous,
                )
                active = (
                    is_active(record["acceptance_event_state"])
                    or record["displacement_state"] != "NONE"
                    or record["compression_state"] != "NORMAL"
                    or record["interaction_state"] != "NONE"
                )
                any_axis_active.observe("ACTIVE" if active else "INACTIVE", contiguous=contiguous)
                month = (at - EXPECTED_STEP[timeframe]).strftime("%Y-%m")
                monthly.setdefault(month, {"bars": 0, "events": 0})
                monthly[month]["bars"] += 1
                monthly[month]["events"] += int(is_active(record["acceptance_event_state"]))
                previous_time = at
                previous_states = states

    for writer in (state_writer, event_writer, transition_writer):
        writer.close()
    for tracker in (*trackers.values(), acceptance_active, any_axis_active):
        tracker.finish()
    monthly_rates = {
        month: {
            **item,
            "event_rate_pct": pct(item["events"], item["bars"]),
        }
        for month, item in sorted(monthly.items())
    }
    result = {
        "source_bars": state_writer.count,
        "state_records": state_writer.count,
        "acceptance_event_records": event_writer.count,
        "transition_records": transition_writer.count,
        "axis_metrics": {axis: tracker.summary() for axis, tracker in trackers.items()},
        "acceptance_active_metrics": acceptance_active.summary(),
        "any_axis_active_metrics": any_axis_active.summary(),
        "monthly_event_rates": monthly_rates,
        "projection_hash_checks": projection_hash_checks,
        "non_acceptance_axis_checks": axis_checks,
        "genuine_conflict_bars": conflicts,
        "genuine_conflict_pct": pct(conflicts, state_writer.count),
        "state_stream_canonical_jsonl_hash": state_writer.canonical_jsonl_hash,
        "event_stream_canonical_jsonl_hash": event_writer.canonical_jsonl_hash,
        "transition_stream_canonical_jsonl_hash": transition_writer.canonical_jsonl_hash,
    }
    artifacts = [
        {"path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size}
        for path in (state_path, event_path, transition_path)
    ]
    return result, artifacts


def write_report(output: Path, results: dict[str, object]) -> Path:
    lines = [
        "# OVC B-STATE-0.3b Ratified H1 State Release",
        "",
        "**Status:** `RATIFIED FOR ACTIVE OPT-B RESEARCH STATE`  ",
        f"**Ratification ID:** `{RATIFICATION_ID}`  ",
        "**Outcome / execution authority:** `NONE`",
        "",
        "## Ratified state metrics",
        "",
        "| Clock | Bars | Frontier events | Event occupancy | Median duration | P90 duration | Any-axis active | Genuine conflict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for timeframe in ("15M", "2H"):
        item = results[timeframe]
        active = item["acceptance_active_metrics"]
        duration = active["duration_by_state_bars"].get(
            "ACTIVE",
            {"median_bars": 0.0, "p90_bars": 0.0, "max_bars": 0},
        )
        lines.append(
            f"| {timeframe} | {item['source_bars']:,} | {item['acceptance_event_records']:,} | "
            f"{active['occupancy_pct'].get('ACTIVE', 0):.2f}% | {duration['median_bars']:.2f} | "
            f"{duration['p90_bars']:.2f} | "
            f"{item['any_axis_active_metrics']['occupancy_pct'].get('ACTIVE', 0):.2f}% | "
            f"{item['genuine_conflict_pct']:.2f}% |"
        )
    lines.extend([
        "",
        "Every compact state row was verified against the canonical hash of its complete parent relation inventory. Displacement, compression, interaction and quality matched the parent row exactly.",
        "",
        "## Authority boundary",
        "",
        "This release activates descriptive OPT-B research state only. Raw confirmations remain audit evidence, boundary confirmations remain diagnostic evidence, and no outcome, edge, recommendation, risk, production or execution authority is granted.",
    ])
    path = output / "OVC_OPT_B_STATE_v0_3B_RATIFIED_H1_RELEASE_REPORT.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    review_root = args.review_root.resolve()
    parent_root = args.parent_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "B_STATE_0_3B_RATIFIED_MANIFEST.json").exists():
        raise FileExistsError("ratified B-STATE-0.3b release already finalized")
    review_manifest = verify_manifest(review_root, "B_STATE_0_3B_REVIEW_MANIFEST.json")
    parent_manifest = verify_manifest(parent_root, "B_STATE_0_3A_REPLAY_MANIFEST.json")
    if review_manifest["parent_v03a_manifest_hash"] != parent_manifest["manifest_hash"]:
        raise ValueError("review/parent authority lineage mismatch")

    results = {}
    artifacts = []
    for timeframe in ("15M", "2H"):
        print(f"{timeframe}: compiling ratified frontier state", flush=True)
        results[timeframe], produced = compile_timeframe(review_root, parent_root, output, timeframe)
        if results[timeframe]["acceptance_event_records"] != review_manifest["results"][timeframe]["frontier_event_records"]:
            raise ValueError("ratified frontier-event count differs from approved review")
        artifacts.extend(produced)

    summary_path = output / "b_state_0_3b_ratified_summary.json"
    summary_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    report_path = write_report(output, results)
    artifacts.append({"path": report_path.name, "sha256": sha256(report_path), "size_bytes": report_path.stat().st_size})
    for source in (
        ROOT / "contracts/B_STATE_0_3A_REPRESENTATION_RATIFICATION_RECORD.md",
        ROOT / "contracts/B_STATE_0_3B_RATIFICATION_RECORD.md",
        ROOT / "contracts/OVC_OPT_B_ACCEPTANCE_FRONTIER_STATE_CONTRACT_v0_3b.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    manifest_core = {
        "release_id": "B-STATE-GBPUSD-2026H1-v0.3b-RATIFIED",
        "status": "RATIFIED_ACTIVE_OPT_B_RESEARCH_STATE",
        "generated_date": "2026-07-19",
        "ratification_id": RATIFICATION_ID,
        "state_contract_version": CONTRACT_VERSION,
        "semantic_review_manifest_hash": review_manifest["manifest_hash"],
        "parent_v03a_manifest_hash": parent_manifest["manifest_hash"],
        "results": results,
        "artifacts": artifacts,
        "implementation_hashes": {
            "state_v03b.py": sha256(ROOT / "src/ovc_opt_b/state_v03b.py"),
            "build_ratified_acceptance_frontier_state_release.py": sha256(Path(__file__).resolve()),
        },
        "authority_boundary": "Active descriptive OPT-B research state only; no OPT-C outcome, edge, recommendation, risk, production or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    (output / "B_STATE_0_3B_RATIFIED_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": manifest["status"], "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
