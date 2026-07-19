from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, sha256, verify_seal  # noqa: E402
from ovc_opt_b import (  # noqa: E402
    LevelRegistry,
    ReferenceLevel,
    contiguous_segments,
    replay_complete_terms,
    state_to_dict,
    term_record_to_dict,
)


def canonical_hash(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_registry(registry_root: Path, timeframe: str) -> tuple[LevelRegistry, dict[str, object]]:
    manifest = json.loads((registry_root / "REFERENCE_LEVEL_REGISTRY_MANIFEST.json").read_text(encoding="utf-8"))
    expected_manifest_hash = manifest.pop("manifest_hash")
    if canonical_hash(manifest) != expected_manifest_hash:
        raise ValueError("reference registry manifest hash mismatch")
    path = registry_root / f"reference_levels_{timeframe.lower()}.jsonl"
    levels: list[ReferenceLevel] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            levels.append(
                ReferenceLevel(
                    level_id=row["reference_level_id"],
                    level_type=row["level_type"],
                    price=Decimal(row["price"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    first_valid_time=datetime.fromisoformat(row["first_valid_time"]),
                    construction_rule_id=row["construction_rule_id"],
                    construction_rule_version=row["construction_rule_version"],
                    source_bar_ids=tuple(row["source_bar_ids"]),
                    instrument_id=row["instrument_id"],
                    timeframe=row["timeframe"],
                    source_release_id=row["source_release_id"],
                    price_side=row["price_side"],
                    status=row["status"],
                    retired_at=datetime.fromisoformat(row["retired_at"]) if row["retired_at"] else None,
                )
            )
    details = manifest["timeframes"][timeframe]
    return (
        LevelRegistry(
            registry_id=manifest["registry_id"],
            registry_version=manifest["registry_version"],
            instrument_id=manifest["instrument_id"],
            timeframe=timeframe,
            source_release_id=details["source_release_id"],
            levels=tuple(levels),
            registry_hash=details["registry_hash"],
        ),
        {**manifest, "manifest_hash": expected_manifest_hash},
    )


class DeterministicJsonlGzipWriter:
    """Stream canonical JSONL while hashing the uncompressed canonical bytes."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._raw = path.open("wb")
        self._compressed = gzip.GzipFile(
            filename="", mode="wb", fileobj=self._raw, mtime=0, compresslevel=1
        )
        self._text = io.TextIOWrapper(self._compressed, encoding="utf-8", newline="\n")
        self._hash = hashlib.sha256()
        self.count = 0

    def write(self, record: dict[str, object]) -> None:
        line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        self._hash.update(line.encode("utf-8"))
        self._text.write(line)
        self.count += 1

    def close(self) -> None:
        self._text.close()
        # GzipFile deliberately does not close a caller-owned fileobj. Close the
        # raw file explicitly so its final buffered bytes are present before
        # artifact hashing and size inspection.
        self._raw.close()

    @property
    def canonical_jsonl_hash(self) -> str:
        return self._hash.hexdigest()


def exact_pair_coverage(bars: list, registry: LevelRegistry) -> Counter:
    valid_all = sorted(level.first_valid_time for level in registry.levels)
    valid_high = sorted(level.first_valid_time for level in registry.levels if level.level_type.endswith("HIGH"))
    valid_low = sorted(level.first_valid_time for level in registry.levels if level.level_type.endswith("LOW"))
    counts = Counter()
    for segment in contiguous_segments(bars):
        for index in range(21, len(segment)):
            at = segment[index].open_time
            eligible_all = bisect_right(valid_all, at)
            eligible_high = bisect_right(valid_high, at)
            eligible_low = bisect_right(valid_low, at)
            counts["SWEEP_UP"] += eligible_high
            counts["SWEEP_DOWN"] += eligible_low
            counts["REJECTION_DOWN"] += eligible_high
            counts["REJECTION_UP"] += eligible_low
            counts["RECLAIM_UP"] += eligible_all
            counts["RECLAIM_DOWN"] += eligible_all
            if index >= 24:
                acceptance_at = segment[index - 3].open_time
                eligible_at_window = bisect_right(valid_all, acceptance_at)
                counts["ACCEPTANCE_UP"] += eligible_at_window
                counts["ACCEPTANCE_DOWN"] += eligible_at_window
    return counts


def replay_timeframe_streaming(
    bars: list,
    registry: LevelRegistry,
    output: Path,
    timeframe: str,
) -> tuple[dict[str, object], list[Path]]:
    tf = timeframe.lower()
    term_path = output / f"term_records_{tf}.jsonl.gz"
    transition_path = output / f"transition_records_{tf}.jsonl.gz"
    state_path = output / f"resolved_state_stream_{tf}.jsonl.gz"
    coverage_path = output / f"coverage_{tf}.json"
    sample_path = output / f"review_samples_{tf}.jsonl"
    ambiguous_path = output / f"ambiguous_clusters_{tf}.jsonl"
    term_writer = DeterministicJsonlGzipWriter(term_path)
    transition_writer = DeterministicJsonlGzipWriter(transition_path)
    state_writer = DeterministicJsonlGzipWriter(state_path)

    pair_evaluations = exact_pair_coverage(bars, registry)
    episode_starts = Counter()
    status_counts = Counter()
    reason_counts = Counter()
    state_counts = Counter()
    unique_levels: dict[str, set[str]] = defaultdict(set)
    samples: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    ambiguous_count = 0
    segments = contiguous_segments(bars)

    seen_transition_ids: set[str] = set()
    seen_state_times: set[datetime] = set()
    block_bars = 128
    history_bars = 29
    response_bars = 3

    with sample_path.open("w", encoding="utf-8", newline="\n") as sample_handle, ambiguous_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as ambiguous_handle:
        for segment in segments:
            for owned_start in range(0, len(segment), block_bars):
                owned_end = min(len(segment), owned_start + block_bars)
                window_start = max(0, owned_start - history_bars)
                window_end = min(len(segment), owned_end + response_bars)
                replay = replay_complete_terms(segment[window_start:window_end], registry)
                owned_close_times = {bar.close_time for bar in segment[owned_start:owned_end]}

                for record in replay.term_records:
                    if record.anchor_time not in owned_close_times:
                        continue
                    row = term_record_to_dict(record)
                    term_writer.write(row)
                    episode_starts[f"{record.term_id}:{record.direction.value}"] += 1
                    status_counts[f"{record.term_id}:{record.status.value}"] += 1
                    reason_counts.update(record.reason_codes)
                    if record.reference_level_id:
                        unique_levels[record.term_id].add(record.reference_level_id)
                    key = (record.term_id, record.status.value)
                    if len(samples[key]) < 30:
                        samples[key].append(row)
                for record in replay.transition_records:
                    if record.first_valid_time not in owned_close_times:
                        continue
                    if record.term_record_id in seen_transition_ids:
                        continue
                    seen_transition_ids.add(record.term_record_id)
                    transition_writer.write(term_record_to_dict(record))
                for state in replay.state_stream:
                    if state.close_time not in owned_close_times:
                        continue
                    if state.close_time in seen_state_times:
                        raise AssertionError("state stream contains duplicate close_time")
                    seen_state_times.add(state.close_time)
                    row = state_to_dict(state)
                    state_writer.write(row)
                    state_counts[state.state.split(":", 1)[0]] += 1
                    if state.state == "AMBIGUOUS":
                        ambiguous_handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
                        ambiguous_count += 1

        for key in sorted(samples):
            for row in samples[key]:
                sample_handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    term_writer.close()
    transition_writer.close()
    state_writer.close()
    if state_writer.count != len(bars):
        raise AssertionError(f"state stream has {state_writer.count} rows for {len(bars)} source bars")
    coverage = {
        "source_bars": len(bars),
        "contiguous_segments": len(segments),
        "registry_levels": len(registry.levels),
        "eligible_directional_level_bar_evaluations": sum(pair_evaluations.values()),
        "pair_evaluations": dict(sorted(pair_evaluations.items())),
        "materialized_episode_records": term_writer.count,
        "episode_starts": dict(sorted(episode_starts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "unique_levels_with_records_by_term": {
            term: len(ids) for term, ids in sorted(unique_levels.items())
        },
        "state_counts": dict(sorted(state_counts.items())),
        "transition_records": transition_writer.count,
        "materialization_policy": "All eligible pairs counted; records emitted on deterministic episode/condition entry and resolution.",
        "neutral_transition_policy": "Deferred because B-LANG-0.1 requires a confirmed destination trigger but defines no NEUTRAL-producing term.",
    }
    coverage_path.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = {
        "source_bars": len(bars),
        "contiguous_segments": len(segments),
        "registry_levels": len(registry.levels),
        "term_records": term_writer.count,
        "transition_records": transition_writer.count,
        "ambiguous_state_bars": ambiguous_count,
        "review_samples": sum(len(rows) for rows in samples.values()),
        "coverage": coverage,
        "term_records_canonical_jsonl_hash": term_writer.canonical_jsonl_hash,
        "transition_records_canonical_jsonl_hash": transition_writer.canonical_jsonl_hash,
        "state_stream_canonical_jsonl_hash": state_writer.canonical_jsonl_hash,
    }
    return result, [term_path, transition_path, state_path, coverage_path, sample_path, ambiguous_path]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--registry-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeframes", nargs="+", choices=("15M", "2H"), default=("15M", "2H"))
    args = parser.parse_args()
    seal_root = args.seal_root.resolve()
    registry_root = args.registry_root.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"replay output already exists: {output}")
    output.mkdir(parents=True)

    seal = verify_seal(seal_root)
    all_results: dict[str, object] = {}
    artifacts: list[dict[str, object]] = []
    registry_manifest: dict[str, object] | None = None
    for timeframe in args.timeframes:
        registry, registry_manifest = load_registry(registry_root, timeframe)
        if registry_manifest["opt_a_seal_hash"] != seal["seal_hash"]:
            raise ValueError("registry is not bound to the verified OPT-A seal")
        bars = read_canonical_bars(seal_root / f"canonical/accepted_{timeframe.lower()}.csv")
        result, paths = replay_timeframe_streaming(bars, registry, output, timeframe)
        for path in paths:
            artifacts.append(
                {
                    "path": path.name,
                    "sha256": sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        all_results[timeframe] = result

    assert registry_manifest is not None
    manifest_core = {
        "replay_id": "B-REPLAY-GBPUSD-2026H1-v0.1",
        "replay_version": "B-REPLAY-0.1",
        "status": "HISTORICALLY_REPLAYED_WITH_SEMANTIC_BLOCKERS_NOT_ACTIVE",
        "generated_date": "2026-07-19",
        "instrument_id": "GBPUSD",
        "price_side": "BID",
        "opt_a_seal_id": seal["seal_id"],
        "opt_a_seal_hash": seal["seal_hash"],
        "reference_registry_version": registry_manifest["registry_version"],
        "reference_registry_hash": registry_manifest["combined_registry_hash"],
        "term_registry_version": "B-LANG-0.1",
        "parameter_set_id": "B-LANG-0.1-SEED",
        "materialization_policy": {
            "coverage": "Every eligible directional level-bar combination is counted.",
            "records": "Materialize deterministic condition-entry and event-episode records; do not repeat persistent non-events on every bar.",
            "multiplicity": "Every qualifying level produces its own term record; no best-level selection.",
        },
        "results": all_results,
        "semantic_blockers": [
            "No ratified level retirement/relevance horizon; old levels remain eligible.",
            "Multiple same-precedence level states resolve to AMBIGUOUS rather than a hidden best level.",
            "B-LANG-0.1 defines NEUTRAL transitions but no confirmed term that produces NEUTRAL; neutral exit transitions are deferred.",
            "Acceptance failed windows are retained in aggregate coverage rather than emitted as hundreds of millions of duplicate rows.",
            "Confirmed acceptance records represent condition entry; a separate persistent acceptance exit/retirement ledger is not yet ratified.",
            "Semantic sample review and threshold sensitivity remain required before activation.",
        ],
        "artifacts": artifacts,
    }
    canonical = json.dumps(manifest_core, sort_keys=True, separators=(",", ":"))
    manifest = {**manifest_core, "manifest_hash": hashlib.sha256(canonical.encode()).hexdigest()}
    (output / "OPT_B_COMPLETE_REPLAY_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# OVC OPT-B Complete Historical Replay — GBP/USD 2026 H1",
        "",
        "**Replay:** `B-REPLAY-GBPUSD-2026H1-v0.1`  ",
        "**Status:** `HISTORICALLY_REPLAYED WITH SEMANTIC BLOCKERS — NOT ACTIVE`  ",
        f"**OPT-A seal:** `{seal['seal_id']}`  ",
        f"**Reference registry:** `{registry_manifest['registry_version']}`",
        "",
        "## Result",
        "",
        "| Clock | Bars | Levels | Eligible directional evaluations | Materialized records | Transitions | Ambiguous state bars |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for timeframe in args.timeframes:
        result = all_results[timeframe]
        lines.append(
            f"| {timeframe} | {result['source_bars']:,} | {result['registry_levels']:,} | "
            f"{result['coverage']['eligible_directional_level_bar_evaluations']:,} | {result['term_records']:,} | "
            f"{result['transition_records']:,} | {result['ambiguous_state_bars']:,} |"
        )
    lines.extend(
        [
            "",
            "Every eligible level was included in coverage. Individual records are emitted at deterministic episode or condition entry, including failed, pending, ambiguous and confirmed resolutions. Persistent non-events are counted rather than duplicated on every bar.",
            "",
            "## Promotion boundary",
            "",
            "The seven terms have reached historical replay, but none is active. Semantic review, ambiguity inspection, near-miss review, threshold sensitivity and operator approval remain mandatory. OPT-C outcomes and edge testing were not used.",
        ]
    )
    (output / "OVC_OPT_B_COMPLETE_HISTORICAL_REPLAY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "manifest_hash": manifest["manifest_hash"], "results": all_results}))


if __name__ == "__main__":
    main()
