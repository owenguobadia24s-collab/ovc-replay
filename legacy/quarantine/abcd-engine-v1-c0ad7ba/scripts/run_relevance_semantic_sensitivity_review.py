from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, sha256, verify_seal  # noqa: E402
from ovc_opt_b import (  # noqa: E402
    Direction,
    RelevancePolicy,
    build_level_lifecycles,
    contiguous_segments,
    lifecycle_to_dict,
)
from ovc_opt_b.primitives import atr_before  # noqa: E402
from run_complete_opt_b_replay import canonical_hash, load_registry  # noqa: E402


D = Decimal
LEVEL_TERMS = {
    "B.TERM.ACCEPTANCE.v0.1",
    "B.TERM.RECLAIM.v0.1",
    "B.TERM.REFERENCE_LEVEL_BREACH_RESPONSE.v0.1",
    "B.TERM.REJECTION.v0.1",
}
TERM_SHORT = {
    "B.TERM.ACCEPTANCE.v0.1": "ACCEPTANCE",
    "B.TERM.COMPRESSION.v0.1": "COMPRESSION",
    "B.TERM.DISPLACEMENT.v0.1": "DISPLACEMENT",
    "B.TERM.RECLAIM.v0.1": "RECLAIM",
    "B.TERM.REFERENCE_LEVEL_BREACH_RESPONSE.v0.1": "BREACH_RESPONSE",
    "B.TERM.REJECTION.v0.1": "REJECTION",
}
POLICIES = (
    RelevancePolicy("NO_RETIREMENT", None, None, False, False),
    RelevancePolicy("STRUCTURAL_ONLY", None, None, True, True),
    RelevancePolicy("TIGHT_24H", timedelta(hours=8), timedelta(hours=24), True, True),
    RelevancePolicy("SEED_48H", timedelta(hours=8), timedelta(hours=48), True, True),
    RelevancePolicy("RELAXED_72H", timedelta(hours=12), timedelta(hours=72), True, True),
)
THRESHOLDS = {
    "CONSERVATIVE": {
        "compression": (D("0.63"), D("1.80"), D("0.60"), D("0.30")),
        "displacement": (D("1.65"), D("0.70"), D("0.85"), D("0.90")),
        "touch": D("0.04"), "breach": D("0.125"), "return": D("0.125"), "depart": D("0.60"),
    },
    "SEED": {
        "compression": (D("0.70"), D("2.00"), D("0.55"), D("0.35")),
        "displacement": (D("1.50"), D("0.65"), D("0.80"), D("0.80")),
        "touch": D("0.05"), "breach": D("0.10"), "return": D("0.10"), "depart": D("0.50"),
    },
    "PERMISSIVE": {
        "compression": (D("0.77"), D("2.20"), D("0.50"), D("0.40")),
        "displacement": (D("1.35"), D("0.60"), D("0.75"), D("0.70")),
        "touch": D("0.075"), "breach": D("0.075"), "return": D("0.075"), "depart": D("0.40"),
    },
}


def verify_replay(replay_root: Path, seal: dict, registry_manifest: dict) -> dict:
    path = replay_root / "OPT_B_COMPLETE_REPLAY_MANIFEST.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = manifest.pop("manifest_hash")
    if canonical_hash(manifest) != expected:
        raise ValueError("complete replay manifest hash mismatch")
    manifest["manifest_hash"] = expected
    if manifest["opt_a_seal_hash"] != seal["seal_hash"]:
        raise ValueError("complete replay is not bound to the selected OPT-A seal")
    if manifest["reference_registry_hash"] != registry_manifest["combined_registry_hash"]:
        raise ValueError("complete replay is not bound to the selected reference registry")
    return manifest


def acceptance_times(path: Path) -> dict[str, tuple[datetime, str]]:
    result: dict[str, tuple[datetime, str]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["term_id"] != "B.TERM.ACCEPTANCE.v0.1" or row["status"] != "CONFIRMED":
                continue
            level_id = row["reference_level_id"]
            candidate = (datetime.fromisoformat(row["first_valid_time"]), row["term_record_id"])
            if level_id not in result or candidate < result[level_id]:
                result[level_id] = candidate
    return result


def term_state(row: dict) -> tuple[int, str] | None:
    if row["status"] == "AMBIGUOUS":
        return 1, "AMBIGUOUS"
    if row["status"] != "CONFIRMED":
        return None
    term = row["term_id"]
    direction = row["direction"]
    level = row["reference_level_id"]
    if term == "B.TERM.ACCEPTANCE.v0.1":
        return 2, f"ACCEPTED_{'ABOVE' if direction == 'UP' else 'BELOW'}:{level}"
    if term == "B.TERM.RECLAIM.v0.1":
        return 3, f"RECLAIMED_{'ABOVE' if direction == 'UP' else 'BELOW'}:{level}"
    if term == "B.TERM.REJECTION.v0.1":
        return 4, f"REJECTED_{direction}:{level}"
    if term == "B.TERM.DISPLACEMENT.v0.1":
        return 5, f"DISPLACING_{direction}"
    if term == "B.TERM.COMPRESSION.v0.1":
        return 6, "COMPRESSED"
    return None


def update_state_candidate(target: dict, at: str, candidate: tuple[int, str]) -> None:
    rank, state = candidate
    current = target.get(at)
    if current is None or rank < current[0]:
        target[at] = [rank, {state}]
    elif rank == current[0]:
        current[1].add(state)


def qualifies_unlevelled(row: dict, profile: dict) -> bool | None:
    m = {key: D(value) for key, value in row["measurements"].items()}
    if row["term_id"] == "B.TERM.COMPRESSION.v0.1":
        tr, span, overlap, efficiency = profile["compression"]
        return m["tr_ratio"] <= tr and m["span_atr"] <= span and m["mean_overlap"] >= overlap and m["path_efficiency"] <= efficiency
    if row["term_id"] == "B.TERM.DISPLACEMENT.v0.1":
        tr, body, location, travel = profile["displacement"]
        return m["tr_atr"] >= tr and m["body_fraction"] >= body and m["close_location"] >= location and m["close_travel_atr"] >= travel
    return None


def distance(profile: dict, key: str, atr: Decimal, epsilon: Decimal) -> Decimal:
    ticks = D(4 if key == "depart" else 2) * epsilon
    return max(ticks, profile[key] * atr)


def retained_level_predicate(row: dict, bars_by_id: dict, level, profile: dict) -> bool:
    inputs = [bars_by_id[item] for item in row["input_bar_ids"]]
    if len(inputs) < 21:
        return False
    anchor = inputs[20]
    atr = D(row["measurements"]["anchor_atr"])
    direction = Direction(row["direction"])
    price = level.price
    touch = distance(profile, "touch", atr, anchor.price_increment)
    breach = distance(profile, "breach", atr, anchor.price_increment)
    returned = distance(profile, "return", atr, anchor.price_increment)
    depart = distance(profile, "depart", atr, anchor.price_increment)
    term = row["term_id"]
    response = inputs[20:]
    if term == "B.TERM.ACCEPTANCE.v0.1":
        window = inputs[-4:]
        if direction is Direction.UP:
            return sum(item.close >= price + returned for item in window) >= 3 and window[-1].close >= price + returned and min(item.low for item in window) >= price - D("0.25") * atr
        return sum(item.close <= price - returned for item in window) >= 3 and window[-1].close <= price - returned and max(item.high for item in window) <= price + D("0.25") * atr
    if term == "B.TERM.REFERENCE_LEVEL_BREACH_RESPONSE.v0.1":
        crossed = anchor.high >= price + breach if direction is Direction.UP else anchor.low <= price - breach
        response_met = any(item.close <= price - returned for item in response) if direction is Direction.UP else any(item.close >= price + returned for item in response)
        return crossed and response_met
    if term == "B.TERM.RECLAIM.v0.1":
        prior = inputs[12:20]
        if direction is Direction.UP:
            history = any(item.close <= price - touch for item in prior)
            confirmations = sum(item.close >= price + returned for item in response)
            return history and anchor.close >= price + returned and confirmations >= 2
        history = any(item.close >= price + touch for item in prior)
        confirmations = sum(item.close <= price - returned for item in response)
        return history and anchor.close <= price - returned and confirmations >= 2
    if term == "B.TERM.REJECTION.v0.1":
        if direction is Direction.DOWN:
            return anchor.high >= price - touch and any(item.low <= price - depart for item in response)
        return anchor.low <= price + touch and any(item.high >= price + depart for item in response)
    raise ValueError(term)


def active_level_stats(
    bars: list, levels: tuple, lifecycle_map: dict, *, compute_surfaces: bool = False
) -> tuple[dict, dict[str, dict] | None]:
    starts = sorted(item.relevant_from for item in lifecycle_map.values())
    ends = sorted(item.retired_at for item in lifecycle_map.values() if item.retired_at is not None)
    counts = [bisect_right(starts, bar.open_time) - bisect_right(ends, bar.open_time) for bar in bars]
    summary = {
        "mean_active_levels": statistics.fmean(counts) if counts else 0,
        "median_active_levels": statistics.median(counts) if counts else 0,
        "max_active_levels": max(counts, default=0),
        "zero_active_bars": sum(value == 0 for value in counts),
    }

    if not compute_surfaces:
        return summary, None
    level_by_id = {level.level_id: level for level in levels}
    start_events = sorted((life.relevant_from, life.level_id) for life in lifecycle_map.values())
    end_events = sorted((life.retired_at, life.level_id) for life in lifecycle_map.values() if life.retired_at)
    si = ei = 0
    active: set[str] = set()
    surfaces = {name: Counter() for name in THRESHOLDS}
    for segment in contiguous_segments(bars):
        for index, bar in enumerate(segment):
            at = bar.open_time
            while si < len(start_events) and start_events[si][0] <= at:
                active.add(start_events[si][1]); si += 1
            while ei < len(end_events) and end_events[ei][0] <= at:
                active.discard(end_events[ei][1]); ei += 1
            if index < 21:
                continue
            atr = atr_before(segment, index)
            for name, profile in THRESHOLDS.items():
                breach = distance(profile, "breach", atr, bar.price_increment)
                touch = distance(profile, "touch", atr, bar.price_increment)
                surfaces[name]["active_level_bar_pairs"] += len(active)
                for level_id in active:
                    level = level_by_id[level_id]
                    if level.level_type.endswith("HIGH"):
                        surfaces[name]["breach_candidates"] += bar.high >= level.price + breach
                        surfaces[name]["touch_candidates"] += bar.high >= level.price - touch
                    else:
                        surfaces[name]["breach_candidates"] += bar.low <= level.price - breach
                        surfaces[name]["touch_candidates"] += bar.low <= level.price + touch
    return summary, {name: dict(values) for name, values in surfaces.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--registry-root", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "RELEVANCE_REVIEW_MANIFEST.json").exists():
        raise FileExistsError("review output already finalized")

    seal = verify_seal(args.seal_root.resolve())
    results = {}
    artifacts = []
    registry_manifest = None
    replay_manifest = None
    for timeframe in ("15M", "2H"):
        registry, registry_manifest = load_registry(args.registry_root.resolve(), timeframe)
        replay_manifest = verify_replay(args.replay_root.resolve(), seal, registry_manifest)
        bars = read_canonical_bars(args.seal_root.resolve() / f"canonical/accepted_{timeframe.lower()}.csv")
        bars_by_id = {bar.bar_id: bar for bar in bars}
        level_by_id = {level.level_id: level for level in registry.levels}
        term_path = args.replay_root.resolve() / f"term_records_{timeframe.lower()}.jsonl.gz"
        accepted = acceptance_times(term_path)
        lifecycles = {
            policy.policy_id: build_level_lifecycles(registry.levels, policy=policy, acceptance_times=accepted)
            for policy in POLICIES
        }
        lifecycle_maps = {
            policy_id: {item.level_id: item for item in values} for policy_id, values in lifecycles.items()
        }
        seed_map = lifecycle_maps["SEED_48H"]
        lifecycle_path = output / f"level_lifecycles_{timeframe.lower()}_seed.jsonl"
        lifecycle_path.write_text(
            "".join(json.dumps(lifecycle_to_dict(item), sort_keys=True, separators=(",", ":")) + "\n" for item in lifecycles["SEED_48H"]),
            encoding="utf-8",
        )

        record_counts = {policy.policy_id: Counter() for policy in POLICIES}
        candidates = {policy.policy_id: {} for policy in POLICIES}
        unlevelled_sensitivity = {name: Counter() for name in THRESHOLDS}
        level_retention = {name: Counter() for name in THRESHOLDS}
        with gzip.open(term_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                term = row["term_id"]
                short = TERM_SHORT.get(term, term)
                level_id = row["reference_level_id"]
                anchor = datetime.fromisoformat(row["anchor_time"])
                if term in {"B.TERM.COMPRESSION.v0.1", "B.TERM.DISPLACEMENT.v0.1"}:
                    for name, profile in THRESHOLDS.items():
                        if qualifies_unlevelled(row, profile):
                            unlevelled_sensitivity[name][short] += 1
                for policy in POLICIES:
                    if level_id is not None and not lifecycle_maps[policy.policy_id][level_id].is_relevant(anchor):
                        continue
                    record_counts[policy.policy_id][f"{short}:{row['status']}"] += 1
                    state = term_state(row)
                    if state is not None:
                        update_state_candidate(candidates[policy.policy_id], row["first_valid_time"], state)
                if level_id is not None and row["status"] == "CONFIRMED" and seed_map[level_id].is_relevant(anchor):
                    for name, profile in THRESHOLDS.items():
                        level_retention[name][short + ":BASE"] += 1
                        if retained_level_predicate(row, bars_by_id, level_by_id[level_id], profile):
                            level_retention[name][short + ":RETAINED"] += 1

        close_times = [bar.close_time.isoformat() for bar in bars]
        policy_summaries = {}
        seed_ambiguities = []
        for policy in POLICIES:
            state_counts = Counter()
            ambiguity_taxonomy = Counter()
            for at in close_times:
                candidate = candidates[policy.policy_id].get(at)
                if candidate is None:
                    state_counts["NEUTRAL"] += 1
                    continue
                rank, states = candidate
                if rank == 1 or len(states) != 1:
                    state_counts["AMBIGUOUS"] += 1
                    semantic_labels = {state.split(":", 1)[0] for state in states}
                    if rank == 1:
                        category = "EXPLICIT_AMBIGUOUS_TERM"
                    elif len(semantic_labels) == 1:
                        category = "COHERENT_MULTI_LEVEL"
                    else:
                        category = "CONFLICTING_SEMANTIC_STATE"
                    ambiguity_taxonomy[category] += 1
                    if policy.policy_id == "SEED_48H" and len(seed_ambiguities) < 50:
                        seed_ambiguities.append({
                            "close_time": at,
                            "category": category,
                            "semantic_labels": sorted(semantic_labels),
                            "top_precedence_states": sorted(states),
                        })
                else:
                    state_counts[next(iter(states)).split(":", 1)[0]] += 1
            active_summary, surfaces = active_level_stats(
                bars,
                registry.levels,
                lifecycle_maps[policy.policy_id],
                compute_surfaces=policy.policy_id == "SEED_48H",
            )
            policy_summaries[policy.policy_id] = {
                "record_counts": dict(sorted(record_counts[policy.policy_id].items())),
                "state_counts": dict(sorted(state_counts.items())),
                "ambiguous_rate": state_counts["AMBIGUOUS"] / len(bars),
                "ambiguity_taxonomy": dict(sorted(ambiguity_taxonomy.items())),
                "active_levels": active_summary,
                "retirement_reasons": dict(sorted(Counter(item.retirement_reason or "NOT_RETIRED" for item in lifecycles[policy.policy_id]).items())),
                "threshold_candidate_surfaces": surfaces if policy.policy_id == "SEED_48H" else None,
            }
        ambiguity_path = output / f"semantic_ambiguity_examples_{timeframe.lower()}.jsonl"
        ambiguity_path.write_text(
            "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in seed_ambiguities),
            encoding="utf-8",
        )
        results[timeframe] = {
            "bars": len(bars),
            "levels": len(registry.levels),
            "policies": policy_summaries,
            "threshold_sensitivity": {
                "unlevelled_full_population_confirmed": {name: dict(values) for name, values in unlevelled_sensitivity.items()},
                "seed_relevant_confirmed_level_predicate_retention": {name: dict(values) for name, values in level_retention.items()},
                "interpretation": "Level retention rechecks distance predicates for seed-relevant confirmed episodes; it is not an OPT-C outcome test.",
            },
        }
        for path in (lifecycle_path, ambiguity_path):
            artifacts.append({"path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size})

    comparison_path = output / "relevance_semantic_threshold_results.json"
    comparison_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": comparison_path.name, "sha256": sha256(comparison_path), "size_bytes": comparison_path.stat().st_size})
    assert registry_manifest is not None and replay_manifest is not None
    manifest_core = {
        "review_id": "B-REF-SEMANTIC-SENSITIVITY-2026H1-v0.2",
        "status": "REVIEWED_WITH_OPERATOR_RATIFICATION_REQUIRED_NOT_ACTIVE",
        "generated_date": "2026-07-19",
        "opt_a_seal_hash": seal["seal_hash"],
        "reference_registry_hash": registry_manifest["combined_registry_hash"],
        "complete_replay_manifest_hash": replay_manifest["manifest_hash"],
        "relevance_contract_version": "B-REF-0.2",
        "seed_policy": "SEED_48H",
        "results_hash": sha256(comparison_path),
        "artifacts": artifacts,
        "activation_blockers": [
            "Operator semantic review of ambiguity examples is required.",
            "Seed 8h/48h maximum ages require ratification; no OPT-C outcomes were used.",
            "Full response-window threshold replay is required before changing B-LANG-0.1 thresholds.",
            "A deterministic NEUTRAL exit trigger remains undefined.",
        ],
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    (output / "RELEVANCE_REVIEW_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# OVC OPT-B Level Relevance, Semantic and Threshold-Sensitivity Review",
        "",
        "**Status:** `REVIEWED — OPERATOR RATIFICATION REQUIRED — NOT ACTIVE`  ",
        f"**OPT-A seal:** `{seal['seal_id']}`  ",
        "**Relevance contract:** `B-REF-0.2`  ",
        "**Seed candidate:** `SEED_48H` (8-hour ranges, 48-hour swings)",
        "",
        "## Relevance comparison",
        "",
        "| Clock | Policy | Mean active levels | Max | Ambiguous bars | Ambiguous rate |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for tf in ("15M", "2H"):
        for policy in POLICIES:
            item = results[tf]["policies"][policy.policy_id]
            active = item["active_levels"]
            ambiguous = item["state_counts"].get("AMBIGUOUS", 0)
            lines.append(f"| {tf} | {policy.policy_id} | {active['mean_active_levels']:.2f} | {active['max_active_levels']} | {ambiguous:,} | {item['ambiguous_rate']:.2%} |")
    lines.extend([
        "",
        "## Semantic finding",
        "",
        "The no-retirement baseline allows obsolete and current levels to claim the same bar. Relevance filtering tests whether ambiguity falls without using outcomes. Remaining ambiguity is preserved explicitly; no nearest-level or best-level heuristic is introduced.",
        "",
        "## Threshold finding",
        "",
        "Compression and displacement sensitivity is measured over their full evaluated populations. Level-term sensitivity rechecks the observable distance predicates of seed-relevant confirmed episodes under conservative, seed and permissive profiles. These counts describe classification stability, not edge.",
        "",
        "## Promotion boundary",
        "",
        "`B-REF-0.2-SEED` is a review candidate only. Operator ratification, a full response-window replay for any threshold change, and the missing deterministic NEUTRAL exit contract remain mandatory before activation.",
    ])
    report_path = output / "OVC_OPT_B_RELEVANCE_SEMANTIC_SENSITIVITY_REVIEW_v0_2.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "manifest_hash": manifest["manifest_hash"], "results": results}))


if __name__ == "__main__":
    main()
