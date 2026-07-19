from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from datetime import datetime
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, sha256, verify_seal  # noqa: E402
from ovc_opt_b import expected_15m_open_times, measure_neutral_path  # noqa: E402
from run_complete_opt_b_replay import canonical_hash  # noqa: E402


MEASUREMENT_VERSION = "OPT-C-MEASURE-0.1.1"
MEASURED_HORIZONS = (1, 2, 4, 8, 12)
EVENT_CLOCKS = ("15M", "2H")


def verify_manifest(root: Path, name: str) -> dict[str, object]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError(f"manifest self-hash mismatch: {name}")
    return manifest


def load_gzip(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def canonical_stream_hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            digest.update((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
            count += 1
    return digest.hexdigest(), count


def compact_state(row: dict[str, object]) -> dict[str, object]:
    return {
        "acceptance_event_state": row["acceptance_event_state"],
        "acceptance_frontier_summary": row["acceptance_frontier_summary"],
        "displacement_state": row["displacement_state"],
        "compression_state": row["compression_state"],
        "interaction_state": row["interaction_state"],
        "quality_state": row["quality_state"],
    }


def expected_transition_lineage(anchor_time, endpoint_time, times, transitions):
    start = bisect_right(times, anchor_time)
    end = bisect_right(times, endpoint_time)
    selected = transitions[start:end]
    ids = [item["transition_record_id"] for item in selected]
    return {
        "timeframe": "15M",
        "transition_count": len(selected),
        "counts_by_axis": dict(sorted(Counter(item["axis"] for item in selected).items())),
        "transition_record_ids_hash": canonical_hash(ids),
    }


def recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return {str(key).lower() for key in value} | set().union(
            *(recursive_keys(item) for item in value.values())
        )
    if isinstance(value, list):
        return set().union(*(recursive_keys(item) for item in value)) if value else set()
    return set()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--coverage-root", type=Path, required=True)
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    ledger_root = args.ledger_root.resolve()
    coverage_root = args.coverage_root.resolve()
    seal_root = args.seal_root.resolve()
    state_root = args.state_root.resolve()

    manifest = verify_manifest(root, "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json")
    ledger_manifest = verify_manifest(ledger_root, "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    coverage_manifest = verify_manifest(coverage_root, "OPT_C_FORWARD_PATH_COVERAGE_MANIFEST.json")
    state_manifest = verify_manifest(state_root, "B_STATE_0_3B_RATIFIED_MANIFEST.json")
    seal = verify_seal(seal_root)
    if manifest["measurement_contract_version"] != MEASUREMENT_VERSION:
        raise ValueError("wrong measurement contract version")
    if manifest["event_ledger_manifest_hash"] != ledger_manifest["manifest_hash"]:
        raise ValueError("event-ledger lineage mismatch")
    if manifest["coverage_manifest_hash"] != coverage_manifest["manifest_hash"]:
        raise ValueError("coverage lineage mismatch")
    if manifest["b_state_manifest_hash"] != state_manifest["manifest_hash"]:
        raise ValueError("B-state lineage mismatch")
    if manifest["opt_a_seal_hash"] != seal["seal_hash"]:
        raise ValueError("OPT-A lineage mismatch")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

    bars = {
        clock: read_canonical_bars(seal_root / f"canonical/accepted_{clock.lower()}.csv")
        for clock in EVENT_CLOCKS
    }
    path_bars = {bar.open_time: bar for bar in bars["15M"]}
    event_bar_by_id = {clock: {bar.bar_id: bar for bar in items} for clock, items in bars.items()}
    states = load_gzip(state_root / "ratified_parallel_axis_state_stream_15m.jsonl.gz")
    state_by_time = {datetime.fromisoformat(row["close_time"]): row for row in states}
    transitions = load_gzip(state_root / "ratified_parallel_axis_transitions_15m.jsonl.gz")
    transitions.sort(key=lambda row: (row["at"], row["transition_record_id"]))
    transition_times = [datetime.fromisoformat(row["at"]) for row in transitions]

    prohibited = {"profit", "pnl", "win", "loss", "trade", "execution", "edge", "recommendation"}
    stream_checks = []
    total = 0
    for clock in EVENT_CLOCKS:
        anchors = {
            row["event_anchor_id"]: row
            for row in load_gzip(ledger_root / f"opt_c_event_anchor_ledger_{clock.lower()}.jsonl.gz")
        }
        coverage_rows = load_gzip(coverage_root / f"opt_c_forward_path_coverage_{clock.lower()}.jsonl.gz")
        eligible_coverage = {
            row["coverage_record_id"]: row
            for row in coverage_rows
            if row["coverage_status"] == "COMPLETE" and row["horizon_hours"] in MEASURED_HORIZONS
        }
        censored_ids = {
            row["coverage_record_id"] for row in coverage_rows if row["coverage_status"] == "CENSORED"
        }
        outcome_path = root / f"opt_c_neutral_outcomes_{clock.lower()}.jsonl.gz"
        records = load_gzip(outcome_path)
        stream_hash, stream_count = canonical_stream_hash(outcome_path)
        if stream_hash != manifest["results"][clock]["outcome_stream_canonical_jsonl_hash"]:
            raise ValueError(f"canonical stream hash mismatch in {clock}")
        if stream_count != len(eligible_coverage) or len(records) != len(eligible_coverage):
            raise ValueError(f"outcome cardinality mismatch in {clock}")
        seen_coverage = set()
        horizon_counts = Counter()
        for row in records:
            coverage_id = row["coverage_record_id"]
            if coverage_id in seen_coverage or coverage_id not in eligible_coverage:
                raise ValueError(f"duplicate or ineligible coverage record in {clock}")
            if coverage_id in censored_ids:
                raise ValueError(f"censored path received outcome row in {clock}")
            seen_coverage.add(coverage_id)
            coverage = eligible_coverage[coverage_id]
            anchor = anchors[row["event_anchor_id"]]
            if row["horizon_hours"] not in MEASURED_HORIZONS or row["horizon_hours"] in (24, 48):
                raise ValueError(f"unapproved horizon measured in {clock}")
            anchor_time = datetime.fromisoformat(anchor["anchor_time"])
            expected_opens = expected_15m_open_times(anchor_time, row["horizon_hours"])
            exact_path = tuple(path_bars[at] for at in expected_opens)
            if canonical_hash([bar.bar_id for bar in exact_path]) != row["path_bar_ids_hash"]:
                raise ValueError(f"ordered path hash mismatch in {clock}")
            expected_measurements = measure_neutral_path(
                anchor_time=anchor_time,
                anchor_price=Decimal(anchor["anchor_price"]),
                event_direction_value=anchor["event_direction"],
                event_bar_high=event_bar_by_id[clock][anchor["anchor_bar_id"]].high,
                event_bar_low=event_bar_by_id[clock][anchor["anchor_bar_id"]].low,
                path_bars=exact_path,
                frontier_summary=anchor["b_state_snapshot"]["acceptance_frontier_summary"],
            )
            if row["measurements"] != expected_measurements:
                raise ValueError(f"neutral measurement mismatch in {clock}")
            endpoint = datetime.fromisoformat(row["endpoint_time"])
            endpoint_state = state_by_time.get(endpoint)
            if endpoint_state is None or row["endpoint_b_state_record_id"] != endpoint_state["state_record_id"]:
                raise ValueError(f"endpoint B-state mismatch in {clock}")
            if row["endpoint_b_state_snapshot"] != compact_state(endpoint_state):
                raise ValueError(f"endpoint B-state snapshot mismatch in {clock}")
            expected_lineage = expected_transition_lineage(
                anchor_time, endpoint, transition_times, transitions
            )
            if row["transition_lineage"] != expected_lineage:
                raise ValueError(f"transition lineage mismatch in {clock}")
            if row["overlap"] != coverage["overlap"]:
                raise ValueError(f"overlap metadata mismatch in {clock}")
            core = {key: value for key, value in row.items() if key != "neutral_outcome_record_id"}
            if row["neutral_outcome_record_id"] != f"opt-c-neutral:{canonical_hash(core)}":
                raise ValueError(f"outcome record ID mismatch in {clock}")
            if recursive_keys(row).intersection(prohibited):
                raise ValueError(f"prohibited semantic key entered outcome record in {clock}")
            horizon_counts[str(row["horizon_hours"])] += 1
        if seen_coverage != set(eligible_coverage):
            raise ValueError(f"eligible complete paths missing outcomes in {clock}")
        for horizon in MEASURED_HORIZONS:
            declared = manifest["results"][clock]["horizons"][str(horizon)]["records"]
            if horizon_counts[str(horizon)] != declared:
                raise ValueError(f"horizon summary mismatch in {clock}:{horizon}")
        total += len(records)
        stream_checks.append({
            "event_timeframe": clock,
            "rows": len(records),
            "unique_coverage_records": len(seen_coverage),
            "horizon_counts": dict(sorted(horizon_counts.items(), key=lambda item: int(item[0]))),
            "canonical_jsonl_hash": stream_hash,
            "gzip_integrity": "PASS",
            "all_measurements_recomputed": True,
        })
    if total != manifest["total_outcome_records"] or total != 14979:
        raise ValueError("release-wide outcome row count mismatch")

    determinism = {"checked": False}
    if args.determinism_root:
        other = verify_manifest(args.determinism_root.resolve(), "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json")
        comparisons = {
            clock: other["results"][clock]["outcome_stream_canonical_jsonl_hash"]
            == manifest["results"][clock]["outcome_stream_canonical_jsonl_hash"]
            for clock in EVENT_CLOCKS
        }
        if other["manifest_hash"] != manifest["manifest_hash"] or not all(comparisons.values()):
            raise ValueError("determinism mismatch")
        determinism = {"checked": True, "manifest_hash_match": True, "stream_hashes_match": comparisons}

    result = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "total_outcome_records": total,
        "artifact_checks": artifact_checks,
        "stream_checks": stream_checks,
        "determinism": determinism,
        "gate_controls": {
            "complete_paths_only": True,
            "censored_paths_have_no_outcome_rows": True,
            "24h_coverage_only": True,
            "48h_blocked": True,
            "ordered_path_hashes_replayed": True,
            "neutral_measurements_recomputed": True,
            "endpoint_states_replayed": True,
            "transition_lineage_replayed": True,
            "overlap_metadata_preserved": True,
            "prohibited_outcome_semantics_absent": True,
        },
        "authority_boundary": "Neutral descriptive measurements only; no edge, recommendation, risk, trade or execution authority.",
    }
    (root / "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_VALIDATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# OPT-C Neutral Outcome Measurement Validation",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
        f"**Independent determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        f"All **{total:,}** saved measurements were recomputed from exact sealed bars. Ordered path hashes, endpoint B-states, intervening transition hashes, overlap metadata, artifact hashes and record IDs passed.",
        "",
        "No censored path, 24h path or 48h path received an outcome row. The validated release remains descriptive only.",
    ]
    (root / "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_VALIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS", "rows": total, "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
