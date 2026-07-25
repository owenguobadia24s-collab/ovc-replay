from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
import gzip
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from ovc_opt_b import (  # noqa: E402
    AcceptanceEventComponent,
    AcceptanceEventSnapshot,
    resolve_acceptance_frontier_variants,
)
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402
from run_parallel_axis_state_replay import MetricTracker  # noqa: E402


CONTRACT_VERSION = "B-STATE-0.3b-REVIEW"
PARENT_VERSION = "B-STATE-0.3a"
EXPECTED_STEP = {"15M": timedelta(minutes=15), "2H": timedelta(hours=2)}
VARIANTS = ("raw_confirmation", "boundary_confirmation", "frontier_advance")


def verify_parent(root: Path) -> dict[str, object]:
    manifest = json.loads((root / "B_STATE_0_3A_REPLAY_MANIFEST.json").read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError("parent v0.3a manifest self-hash mismatch")
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        if sha256(path) != artifact["sha256"]:
            raise ValueError(f"parent v0.3a artifact mismatch: {path.name}")
    return manifest


def decimal_or_none(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


def parse_raw_event(row: dict[str, object]) -> AcceptanceEventSnapshot:
    components = tuple(
        AcceptanceEventComponent(
            semantic_state=item["semantic_state"],
            direction=item["direction"],
            support_level_ids=tuple(item["support_level_ids"]),
            trigger_term_record_ids=tuple(item["trigger_term_record_ids"]),
        )
        for item in row["acceptance_event_components"]
    )
    state = row["acceptance_event_state"]
    reasons = tuple(
        reason.removeprefix("ACCEPTANCE_EVENT_")
        for reason in row.get("conflict_reasons", [])
        if reason.startswith("ACCEPTANCE_EVENT_")
    )
    return AcceptanceEventSnapshot(
        semantic_state=state,
        components=components,
        genuine_conflict=state == "CONFLICTING" or bool(reasons),
        conflict_reasons=tuple(sorted(reasons)),
    )


def compact_frontier_summary(inventory: dict[str, object]) -> dict[str, object]:
    return {
        "accepted_floor_level_ids": inventory["accepted_floor_level_ids"],
        "accepted_floor_price": inventory["accepted_floor_price"],
        "accepted_ceiling_level_ids": inventory["accepted_ceiling_level_ids"],
        "accepted_ceiling_price": inventory["accepted_ceiling_price"],
        "boundary_width": inventory["boundary_width"],
        "close_position_in_boundary": inventory["close_position_in_boundary"],
        "accepted_above_count": inventory["accepted_above_count"],
        "accepted_below_count": inventory["accepted_below_count"],
        "relation_count": inventory["relation_count"],
        "challenged_count": inventory["challenged_count"],
        "refreshed_this_bar_count": inventory["refreshed_this_bar_count"],
        "youngest_relation_age_bars": inventory["youngest_relation_age_bars"],
        "median_relation_age_bars": inventory["median_relation_age_bars"],
        "oldest_relation_age_bars": inventory["oldest_relation_age_bars"],
        "relation_balance": inventory["relation_balance"],
    }


def component_summary(components: tuple[AcceptanceEventComponent, ...]) -> list[dict[str, object]]:
    return [
        {
            "direction": component.direction,
            "support_level_ids": list(component.support_level_ids),
            "trigger_term_record_ids": list(component.trigger_term_record_ids),
        }
        for component in components
    ]


def is_active(state: str) -> bool:
    return state not in ("NONE", "CONFLICTING")


def canonical_size(value: object) -> int:
    return len(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def pct(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) * 100 / float(denominator), 4) if denominator else 0.0


def replay_timeframe(parent_root: Path, output: Path, timeframe: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    source_path = parent_root / f"acceptance_relation_state_stream_{timeframe.lower()}.jsonl.gz"
    review_path = output / f"acceptance_frontier_review_state_stream_{timeframe.lower()}.jsonl.gz"
    event_path = output / f"acceptance_frontier_event_records_{timeframe.lower()}.jsonl.gz"
    review_writer = DeterministicJsonlGzipWriter(review_path)
    event_writer = DeterministicJsonlGzipWriter(event_path)
    semantic_trackers = {variant: MetricTracker() for variant in VARIANTS}
    active_trackers = {variant: MetricTracker() for variant in VARIANTS}
    any_axis_trackers = {"raw_confirmation": MetricTracker(), "frontier_advance": MetricTracker()}
    monthly = defaultdict(lambda: {"bars": 0, **{variant: 0 for variant in VARIANTS}})
    state_counts = {variant: Counter() for variant in VARIANTS}
    source_conflicts = review_conflicts = post_gap_boundary_events = 0
    full_inventory_bytes = compact_summary_bytes = 0
    full_relation_id_references = boundary_id_references = 0
    previous_row = None

    with gzip.open(source_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["state_contract_version"] != PARENT_VERSION:
                raise ValueError("unexpected parent state contract version")
            at = datetime.fromisoformat(row["close_time"])
            contiguous = (
                previous_row is not None
                and at - datetime.fromisoformat(previous_row["close_time"]) == EXPECTED_STEP[timeframe]
            )
            inventory = row["acceptance_relation_inventory"]
            previous_inventory = previous_row["acceptance_relation_inventory"] if contiguous else {}
            variants = resolve_acceptance_frontier_variants(
                parse_raw_event(row),
                current_floor_level_ids=inventory["accepted_floor_level_ids"],
                current_floor_price=decimal_or_none(inventory["accepted_floor_price"]),
                current_ceiling_level_ids=inventory["accepted_ceiling_level_ids"],
                current_ceiling_price=decimal_or_none(inventory["accepted_ceiling_price"]),
                previous_floor_price=decimal_or_none(previous_inventory.get("accepted_floor_price")),
                previous_ceiling_price=decimal_or_none(previous_inventory.get("accepted_ceiling_price")),
                contiguous=contiguous,
            )
            states = {
                "raw_confirmation": variants.raw_confirmation_state,
                "boundary_confirmation": variants.boundary_confirmation_state,
                "frontier_advance": variants.frontier_advance_state,
            }
            for variant, state in states.items():
                semantic_trackers[variant].observe(state, contiguous=contiguous)
                active_trackers[variant].observe("ACTIVE" if is_active(state) else "INACTIVE", contiguous=contiguous)
                state_counts[variant][state] += 1
            non_acceptance_active = (
                row["displacement_state"] != "NONE"
                or row["compression_state"] != "NORMAL"
                or row["interaction_state"] != "NONE"
            )
            for variant in any_axis_trackers:
                any_axis_trackers[variant].observe(
                    "ACTIVE" if non_acceptance_active or is_active(states[variant]) else "INACTIVE",
                    contiguous=contiguous,
                )

            # Attribute a fixed-interval bar to the month in which its interval
            # opens. A bar closing exactly at 00:00 on 1 July belongs to June.
            month = (at - EXPECTED_STEP[timeframe]).strftime("%Y-%m")
            monthly[month]["bars"] += 1
            for variant, state in states.items():
                monthly[month][variant] += int(is_active(state))
            if not contiguous and is_active(states["boundary_confirmation"]):
                post_gap_boundary_events += 1
            source_conflicts += int(bool(row["genuine_conflict"]))
            review_conflicts += int(variants.genuine_conflict)

            compact = compact_frontier_summary(inventory)
            full_inventory_bytes += canonical_size(inventory)
            compact_summary_bytes += canonical_size(compact)
            full_relation_id_references += (
                len(inventory["accepted_above_level_ids"])
                + len(inventory["accepted_below_level_ids"])
                + len(inventory["challenged_level_ids"])
            )
            boundary_id_references += (
                len(inventory["accepted_floor_level_ids"])
                + len(inventory["accepted_ceiling_level_ids"])
            )
            inventory_hash = canonical_hash(inventory)
            core = {
                "instrument_id": row["instrument_id"],
                "timeframe": timeframe,
                "close_time": row["close_time"],
                "raw_confirmation_event_state": states["raw_confirmation"],
                "boundary_confirmation_event_state": states["boundary_confirmation"],
                "frontier_advance_event_state": states["frontier_advance"],
                "boundary_confirmation_components": component_summary(variants.boundary_components),
                "frontier_advance_components": component_summary(variants.frontier_advance_components),
                "acceptance_frontier_summary": compact,
                "full_relation_inventory_hash": inventory_hash,
                "parent_state_record_id": row["state_record_id"],
                "displacement_state": row["displacement_state"],
                "compression_state": row["compression_state"],
                "interaction_state": row["interaction_state"],
                "interaction_components": row["interaction_components"],
                "quality_state": row["quality_state"],
                "source_genuine_conflict": row["genuine_conflict"],
                "review_genuine_conflict": variants.genuine_conflict,
                "review_conflict_reasons": list(variants.conflict_reasons),
                "state_contract_version": CONTRACT_VERSION,
                "parent_state_contract_version": PARENT_VERSION,
            }
            review_record = {**core, "review_state_record_id": f"frontier-review:{canonical_hash(core)}"}
            review_writer.write(review_record)
            if is_active(states["frontier_advance"]):
                event_core = {
                    "timeframe": timeframe,
                    "at": row["close_time"],
                    "frontier_advance_event_state": states["frontier_advance"],
                    "components": component_summary(variants.frontier_advance_components),
                    "full_relation_inventory_hash": inventory_hash,
                    "parent_state_record_id": row["state_record_id"],
                    "state_contract_version": CONTRACT_VERSION,
                }
                event_writer.write(
                    {**event_core, "frontier_event_record_id": f"frontier-event:{canonical_hash(event_core)}"}
                )
            previous_row = row

    review_writer.close()
    event_writer.close()
    for tracker in (*semantic_trackers.values(), *active_trackers.values(), *any_axis_trackers.values()):
        tracker.finish()

    rows = review_writer.count
    if rows == 0:
        raise ValueError("empty parent state stream")
    monthly_rates = {}
    for month, item in sorted(monthly.items()):
        monthly_rates[month] = {
            "bars": item["bars"],
            **{f"{variant}_event_bars": item[variant] for variant in VARIANTS},
            **{f"{variant}_event_rate_pct": pct(item[variant], item["bars"]) for variant in VARIANTS},
        }
    active_counts = {
        variant: active_trackers[variant].summary()["occupancy_counts"].get("ACTIVE", 0)
        for variant in VARIANTS
    }
    result = {
        "source_bars": rows,
        "review_state_records": review_writer.count,
        "frontier_event_records": event_writer.count,
        "semantic_metrics": {variant: semantic_trackers[variant].summary() for variant in VARIANTS},
        "active_metrics": {variant: active_trackers[variant].summary() for variant in VARIANTS},
        "any_axis_active_metrics": {variant: any_axis_trackers[variant].summary() for variant in any_axis_trackers},
        "state_counts": {variant: dict(sorted(counts.items())) for variant, counts in state_counts.items()},
        "monthly_event_rates": monthly_rates,
        "retention": {
            "boundary_from_raw_pct": pct(active_counts["boundary_confirmation"], active_counts["raw_confirmation"]),
            "frontier_from_raw_pct": pct(active_counts["frontier_advance"], active_counts["raw_confirmation"]),
            "frontier_from_boundary_pct": pct(active_counts["frontier_advance"], active_counts["boundary_confirmation"]),
        },
        "inventory_projection": {
            "full_inventory_canonical_bytes": full_inventory_bytes,
            "compact_summary_canonical_bytes": compact_summary_bytes,
            "canonical_byte_reduction_pct": pct(full_inventory_bytes - compact_summary_bytes, full_inventory_bytes),
            "full_relation_id_references": full_relation_id_references,
            "boundary_id_references": boundary_id_references,
            "id_reference_reduction_pct": pct(
                full_relation_id_references - boundary_id_references,
                full_relation_id_references,
            ),
            "full_ledger_authority": "PARENT_B_STATE_0_3A_STATE_STREAM",
        },
        "source_genuine_conflict_bars": source_conflicts,
        "review_genuine_conflict_bars": review_conflicts,
        "review_genuine_conflict_pct": pct(review_conflicts, rows),
        "post_gap_boundary_events_not_promoted_to_advance": post_gap_boundary_events,
        "review_state_stream_canonical_jsonl_hash": review_writer.canonical_jsonl_hash,
        "frontier_event_stream_canonical_jsonl_hash": event_writer.canonical_jsonl_hash,
    }
    artifacts = [
        {"path": review_path.name, "sha256": sha256(review_path), "size_bytes": review_path.stat().st_size},
        {"path": event_path.name, "sha256": sha256(event_path), "size_bytes": event_path.stat().st_size},
    ]
    return result, artifacts


def write_report(output: Path, results: dict[str, object]) -> Path:
    lines = [
        "# OVC B-STATE-0.3b Acceptance Frontier Semantic Review",
        "",
        "**Representation boundary:** `B-STATE-0.3a-REPRESENTATION-ONLY — RATIFIED`  ",
        "**Frontier candidate:** `B-STATE-0.3b-REVIEW — NOT RATIFIED`  ",
        "**Outcome use:** `NONE`",
        "",
        "## Event-surface comparison",
        "",
        "| Clock | Variant | Event occupancy | Active median | Active P90 | Active max | Active transitions / 1,000 bars |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    labels = {
        "raw_confirmation": "Raw confirmation",
        "boundary_confirmation": "Boundary confirmation",
        "frontier_advance": "Outward frontier advance",
    }
    for timeframe in ("15M", "2H"):
        for variant in VARIANTS:
            metrics = results[timeframe]["active_metrics"][variant]
            active = metrics["duration_by_state_bars"].get(
                "ACTIVE",
                {"median_bars": 0.0, "p90_bars": 0.0, "max_bars": 0},
            )
            lines.append(
                f"| {timeframe} | {labels[variant]} | {metrics['occupancy_pct'].get('ACTIVE', 0):.2f}% | "
                f"{active['median_bars']:.2f} | {active['p90_bars']:.2f} | {active['max_bars']:,} | "
                f"{metrics['transitions_per_1000_bars']:.2f} |"
            )
    lines.extend([
        "",
        "Raw confirmations remain auditable. Boundary confirmation removes interior-level repetitions. Frontier advance further requires the accepted floor to move higher or the accepted ceiling to move lower on a contiguous sealed bar.",
        "",
        "## Evidence retention and composite occupancy",
        "",
        "| Clock | Boundary retains raw | Frontier retains raw | Frontier retains boundary | Any-axis active with raw | Any-axis active with frontier |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for timeframe in ("15M", "2H"):
        item = results[timeframe]
        retention = item["retention"]
        raw_any = item["any_axis_active_metrics"]["raw_confirmation"]["occupancy_pct"].get("ACTIVE", 0)
        frontier_any = item["any_axis_active_metrics"]["frontier_advance"]["occupancy_pct"].get("ACTIVE", 0)
        lines.append(
            f"| {timeframe} | {retention['boundary_from_raw_pct']:.2f}% | "
            f"{retention['frontier_from_raw_pct']:.2f}% | "
            f"{retention['frontier_from_boundary_pct']:.2f}% | "
            f"{raw_any:.2f}% | {frontier_any:.2f}% |"
        )
    lines.extend([
        "",
        "## Monthly event rates",
        "",
        "| Clock | Month | Raw | Boundary | Frontier advance |",
        "|---|---|---:|---:|---:|",
    ])
    for timeframe in ("15M", "2H"):
        for month, item in results[timeframe]["monthly_event_rates"].items():
            lines.append(
                f"| {timeframe} | {month} | {item['raw_confirmation_event_rate_pct']:.2f}% | "
                f"{item['boundary_confirmation_event_rate_pct']:.2f}% | "
                f"{item['frontier_advance_event_rate_pct']:.2f}% |"
            )
    lines.extend([
        "",
        "## Inventory projection",
        "",
        "| Clock | Canonical byte reduction | ID-reference reduction | Full ledger | Genuine conflict |",
        "|---|---:|---:|---|---:|",
    ])
    for timeframe in ("15M", "2H"):
        item = results[timeframe]
        projection = item["inventory_projection"]
        lines.append(
            f"| {timeframe} | {projection['canonical_byte_reduction_pct']:.2f}% | "
            f"{projection['id_reference_reduction_pct']:.2f}% | Preserved by parent hash | "
            f"{item['review_genuine_conflict_pct']:.2f}% |"
        )
    lines.extend([
        "",
        "The compact projection is a view, not a relevance filter. Every relation remains in the manifest-bound parent ledger; no TTL, rank, score or best-level selector was introduced.",
        "",
        "## Recommendation",
        "",
        "Adopt `FRONTIER_ADVANCE` as the next controlled state-timeline candidate. Keep `RAW_CONFIRMATION` as audit evidence and `BOUNDARY_CONFIRMATION` as a diagnostic. Use the compact frontier projection as the default review view while retaining the full relation inventory as machine authority.",
        "",
        "This recommendation is semantic only. It does not ratify v0.3b or authorize outcome, edge, recommendation, production or execution use.",
    ])
    path = output / "OVC_OPT_B_STATE_v0_3B_ACCEPTANCE_FRONTIER_SEMANTIC_REVIEW.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parent_root = args.parent_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "B_STATE_0_3B_REVIEW_MANIFEST.json").exists():
        raise FileExistsError("B-STATE-0.3b review already finalized")
    parent_manifest = verify_parent(parent_root)
    results = {}
    artifacts = []
    for timeframe in ("15M", "2H"):
        print(f"{timeframe}: reviewing frontier semantics", flush=True)
        results[timeframe], produced = replay_timeframe(parent_root, output, timeframe)
        artifacts.extend(produced)

    summary_path = output / "b_state_0_3b_semantic_review_summary.json"
    summary_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    report_path = write_report(output, results)
    artifacts.append({"path": report_path.name, "sha256": sha256(report_path), "size_bytes": report_path.stat().st_size})
    for source in (
        ROOT / "contracts/B_STATE_0_3A_REPRESENTATION_RATIFICATION_RECORD.md",
        ROOT / "contracts/OVC_OPT_B_ACCEPTANCE_FRONTIER_SEMANTIC_REVIEW_CONTRACT_v0_3b.md",
        ROOT / "contracts/B_STATE_0_3B_OPERATOR_REVIEW_CHECKLIST.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    manifest_core = {
        "release_id": "B-STATE-GBPUSD-2026H1-v0.3b-semantic-review",
        "status": "REPRESENTATION_BOUNDARY_RATIFIED_FRONTIER_CANDIDATE_NOT_RATIFIED",
        "generated_date": "2026-07-19",
        "parent_v03a_manifest_hash": parent_manifest["manifest_hash"],
        "representation_ratification_id": "B-STATE-0.3a-REPRESENTATION-ONLY",
        "state_contract_version": CONTRACT_VERSION,
        "results": results,
        "artifacts": artifacts,
        "implementation_hashes": {
            "state_v03b.py": sha256(ROOT / "src/ovc_opt_b/state_v03b.py"),
            "run_acceptance_frontier_semantic_review.py": sha256(Path(__file__).resolve()),
            "test_state_v03b.py": sha256(ROOT / "tests/test_state_v03b.py"),
        },
        "authority_boundary": "Representation-only OPT-B research authority. No OPT-C outcome, edge, recommendation, production or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    (output / "B_STATE_0_3B_REVIEW_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": manifest["status"], "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
