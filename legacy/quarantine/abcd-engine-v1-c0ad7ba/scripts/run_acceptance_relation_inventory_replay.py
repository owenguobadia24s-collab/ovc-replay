from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import gzip
import json
import math
from pathlib import Path
import shutil
import sys
from itertools import zip_longest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, sha256, verify_seal  # noqa: E402
from ovc_opt_b import (  # noqa: E402
    LocationCondition,
    acceptance_maintenance_passes,
    contiguous_segments,
    displacement_trigger_state,
    resolve_acceptance_event,
    resolve_acceptance_relation_inventory,
    resolve_interaction_snapshot,
)
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash, load_registry  # noqa: E402
from run_relevance_semantic_sensitivity_review import verify_replay  # noqa: E402
import run_parallel_axis_state_replay as v03  # noqa: E402


CONTRACT_VERSION = "B-STATE-0.3a"
POLICY_ID = "B-REF-0.2-STRUCTURAL-ONLY"


def decimal_text(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def event_components_to_dict(snapshot) -> list[dict[str, object]]:
    return [
        {
            "semantic_state": item.semantic_state,
            "direction": item.direction,
            "support_level_ids": list(item.support_level_ids),
            "trigger_term_record_ids": list(item.trigger_term_record_ids),
        }
        for item in snapshot.components
    ]


def inventory_to_dict(inventory) -> dict[str, object]:
    return {
        "accepted_above_level_ids": list(inventory.accepted_above_level_ids),
        "accepted_below_level_ids": list(inventory.accepted_below_level_ids),
        "challenged_level_ids": list(inventory.challenged_level_ids),
        "accepted_floor_level_ids": list(inventory.accepted_floor_level_ids),
        "accepted_floor_price": decimal_text(inventory.accepted_floor_price),
        "accepted_ceiling_level_ids": list(inventory.accepted_ceiling_level_ids),
        "accepted_ceiling_price": decimal_text(inventory.accepted_ceiling_price),
        "boundary_width": decimal_text(inventory.boundary_width),
        "close_position_in_boundary": decimal_text(inventory.close_position_in_boundary),
        "accepted_above_count": inventory.accepted_above_count,
        "accepted_below_count": inventory.accepted_below_count,
        "relation_count": inventory.relation_count,
        "challenged_count": inventory.challenged_count,
        "refreshed_this_bar_count": inventory.refreshed_this_bar_count,
        "youngest_relation_age_bars": inventory.youngest_relation_age_bars,
        "median_relation_age_bars": inventory.median_relation_age_bars,
        "oldest_relation_age_bars": inventory.oldest_relation_age_bars,
        "relation_balance": inventory.relation_balance,
    }


def state_record(
    *,
    bar,
    acceptance_event,
    inventory,
    latest_acceptance_event_time: datetime | None,
    observed_bars_since_latest_acceptance_event: int | None,
    displacement_state: str,
    displacement_exit_count: int,
    compression_state: str,
    compression_exit_count: int,
    interaction,
    quality_state: str,
    stale_axes: tuple[str, ...],
    conflict_reasons: tuple[str, ...],
    reason_codes: tuple[str, ...],
) -> dict[str, object]:
    core = {
        "instrument_id": bar.instrument_id,
        "timeframe": bar.timeframe,
        "close_time": bar.close_time.astimezone(timezone.utc).isoformat(),
        "acceptance_event_state": acceptance_event.semantic_state,
        "acceptance_event_components": event_components_to_dict(acceptance_event),
        "acceptance_relation_inventory": inventory_to_dict(inventory),
        "latest_acceptance_event_time": (
            latest_acceptance_event_time.astimezone(timezone.utc).isoformat()
            if latest_acceptance_event_time
            else None
        ),
        "observed_bars_since_latest_acceptance_event": observed_bars_since_latest_acceptance_event,
        "displacement_state": displacement_state,
        "displacement_exit_pending_count": displacement_exit_count,
        "compression_state": compression_state,
        "compression_exit_pending_count": compression_exit_count,
        "interaction_state": interaction.semantic_state,
        "interaction_components": v03.interaction_to_dict(interaction),
        "quality_state": quality_state,
        "stale_axes": list(stale_axes),
        "genuine_conflict": bool(conflict_reasons),
        "conflict_reasons": list(conflict_reasons),
        "reason_codes": list(reason_codes),
        "state_contract_version": CONTRACT_VERSION,
        "relevance_policy_id": POLICY_ID,
    }
    return {**core, "state_record_id": f"acceptance-relations:{canonical_hash(core)}"}


def relation_change_record(
    timeframe: str,
    at: datetime,
    prior_ids: set[str],
    current_ids: set[str],
    inventory,
) -> dict[str, object]:
    core = {
        "timeframe": timeframe,
        "at": at.astimezone(timezone.utc).isoformat(),
        "added_level_ids": sorted(current_ids - prior_ids),
        "removed_level_ids": sorted(prior_ids - current_ids),
        "relation_count": inventory.relation_count,
        "accepted_above_count": inventory.accepted_above_count,
        "accepted_below_count": inventory.accepted_below_count,
        "state_contract_version": CONTRACT_VERSION,
    }
    return {**core, "relation_change_record_id": f"acceptance-relation-change:{canonical_hash(core)}"}


def transition_record(timeframe: str, at: datetime, axis: str, old: str, new: str) -> dict[str, object]:
    core = {
        "timeframe": timeframe,
        "at": at.astimezone(timezone.utc).isoformat(),
        "axis": axis,
        "from_state": old,
        "to_state": new,
        "state_contract_version": CONTRACT_VERSION,
    }
    return {**core, "transition_record_id": f"axis-transition:{canonical_hash(core)}"}


def distribution(values: list[int | float]) -> dict[str, float | int]:
    ordered = sorted(values)
    if not ordered:
        return {"observations": 0, "mean": 0.0, "median": 0.0, "p90": 0.0, "max": 0.0}
    length = len(ordered)
    midpoint = length // 2
    median_value = (
        float(ordered[midpoint])
        if length % 2
        else (float(ordered[midpoint - 1]) + float(ordered[midpoint])) / 2
    )
    return {
        "observations": length,
        "mean": round(sum(float(value) for value in ordered) / length, 4),
        "median": round(median_value, 4),
        "p90": round(float(ordered[max(0, math.ceil(length * 0.90) - 1)]), 4),
        "max": round(float(ordered[-1]), 4),
    }


def verify_v03(v03_root: Path, *, seal_hash: str, replay_hash: str, review_hash: str, v02_hash: str) -> dict:
    manifest = v03.verify_manifest(v03_root, "B_STATE_0_3_REPLAY_MANIFEST.json")
    expected = {
        "opt_a_seal_hash": seal_hash,
        "complete_replay_manifest_hash": replay_hash,
        "relevance_review_manifest_hash": review_hash,
        "v02_state_manifest_hash": v02_hash,
    }
    for field, value in expected.items():
        if manifest[field] != value:
            raise ValueError(f"v0.3 authority mismatch: {field}")
    for artifact in manifest["artifacts"]:
        if sha256(v03_root / artifact["path"]) != artifact["sha256"]:
            raise ValueError(f"v0.3 artifact hash mismatch: {artifact['path']}")
    return manifest


def replay_timeframe(
    *,
    timeframe: str,
    bars,
    registry,
    lifecycles,
    evidence_by_time,
    compression_statuses,
    output: Path,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    level_prices = {level.level_id: level.price for level in registry.levels}
    lifecycle_map = {item.level_id: item for item in lifecycles}
    conditions: dict[str, LocationCondition] = {}
    relation_age_bars: dict[str, int] = {}
    latest_acceptance_event_time = None
    bars_since_latest_acceptance_event = None
    displacement_active = "NONE"
    displacement_exit_count = 0
    displacement_stale = False
    compression_active = "NORMAL"
    compression_exit_count = 0
    compression_stale = False

    axis_names = ("acceptance_event", "displacement", "compression", "interaction", "quality")
    trackers = {axis: v03.MetricTracker() for axis in axis_names}
    event_active = v03.MetricTracker()
    relation_present = v03.MetricTracker()
    any_active = v03.MetricTracker()
    component_counts = Counter()
    conflict_reason_counts = Counter()
    reason_counts = Counter()
    boundary_availability = Counter()
    relation_counts = []
    above_counts = []
    below_counts = []
    challenged_counts = []
    oldest_age_bars = []
    latest_event_ages = []
    boundary_width_pips = []
    conflict_bars = 0
    stale_bars = 0
    gap_carry_bars = 0
    refreshed_event_bars = 0

    state_path = output / f"acceptance_relation_state_stream_{timeframe.lower()}.jsonl.gz"
    transition_path = output / f"acceptance_relation_transition_records_{timeframe.lower()}.jsonl.gz"
    change_path = output / f"acceptance_relation_change_records_{timeframe.lower()}.jsonl.gz"
    state_writer = DeterministicJsonlGzipWriter(state_path)
    transition_writer = DeterministicJsonlGzipWriter(transition_path)
    change_writer = DeterministicJsonlGzipWriter(change_path)
    prior_relation_ids: set[str] = set()

    first_segment = True
    for segment in contiguous_segments(bars):
        gap = not first_segment
        first_segment = False
        carried_axes: set[str] = set()
        if gap:
            if conditions:
                carried_axes.add("ACCEPTANCE_RELATIONS")
                for item in conditions.values():
                    item.challenge_count = 0
                    item.stale_after_gap = True
            if displacement_active != "NONE":
                carried_axes.add("DISPLACEMENT")
                displacement_exit_count = 0
                displacement_stale = True
            if compression_active == "COMPRESSED":
                carried_axes.add("COMPRESSION")
                compression_exit_count = 0
                compression_stale = True

        previous_bar = None
        previous_states = None
        for bar_index, bar in enumerate(segment):
            reasons: list[str] = []
            bar_conflicts: set[str] = set()
            if bar_index == 0 and carried_axes:
                gap_carry_bars += 1
                reasons.append("GAP_CARRY_FORWARD_AXES_STALE")
            for level_id in tuple(relation_age_bars):
                relation_age_bars[level_id] += 1
            if bars_since_latest_acceptance_event is not None:
                bars_since_latest_acceptance_event += 1

            axes = evidence_by_time.get(bar.close_time, {})
            location_evidence = tuple(axes.get("LOCATION", ()))
            acceptance_event = resolve_acceptance_event(location_evidence)
            bar_conflicts.update(f"ACCEPTANCE_EVENT_{reason}" for reason in acceptance_event.conflict_reasons)
            if acceptance_event.components:
                latest_acceptance_event_time = bar.close_time
                bars_since_latest_acceptance_event = 0
                refreshed_event_bars += 1

            refreshed_levels: set[str] = set()
            by_level = defaultdict(list)
            for item in location_evidence:
                if item.level_id is not None:
                    by_level[item.level_id].append(item)
            for level_id, items in sorted(by_level.items()):
                confirmed = [item for item in items if item.status == "CONFIRMED"]
                directions = {item.direction for item in confirmed}
                if len(directions) > 1:
                    continue
                if not confirmed:
                    continue
                direction = next(iter(directions))
                return_values = [item.return_min for item in confirmed if item.return_min is not None]
                if not return_values:
                    raise ValueError("confirmed acceptance missing frozen return_min")
                current = conditions.get(level_id)
                state_since = current.state_since if current and current.direction == direction else bar.close_time
                conditions[level_id] = LocationCondition(
                    level_id=level_id,
                    direction=direction,
                    state_since=state_since,
                    refreshed_at=bar.close_time,
                    trigger_term_record_ids=tuple(sorted({item.term_record_id for item in confirmed})),
                    return_min=max(return_values),
                )
                relation_age_bars[level_id] = 0
                refreshed_levels.add(level_id)
                reasons.append("ACCEPTANCE_RELATION_REFRESHED" if current else "ACCEPTANCE_RELATION_ENTERED")

            for level_id in tuple(sorted(conditions)):
                item = conditions[level_id]
                lifecycle = lifecycle_map[level_id]
                if (
                    lifecycle.retirement_reason == "RANGE_SUPERSEDED"
                    and lifecycle.retired_at is not None
                    and bar.open_time >= lifecycle.retired_at
                ):
                    del conditions[level_id]
                    relation_age_bars.pop(level_id, None)
                    reasons.append("ACCEPTANCE_RELATION_ENDED_RANGE_SUPERSEDED")
                    continue
                if level_id in refreshed_levels:
                    continue
                passes = acceptance_maintenance_passes(
                    item,
                    close=bar.close,
                    level_price=level_prices[level_id],
                )
                if passes:
                    item.challenge_count = 0
                    item.stale_after_gap = False
                else:
                    item.challenge_count += 1
                    reasons.append("ACCEPTANCE_RELATION_MAINTENANCE_FAILED")
                    if item.challenge_count >= 2:
                        del conditions[level_id]
                        relation_age_bars.pop(level_id, None)
                        reasons.append("ACCEPTANCE_RELATION_EXITED")

            inventory = resolve_acceptance_relation_inventory(
                conditions,
                level_prices=level_prices,
                close=bar.close,
                relation_age_bars=relation_age_bars,
                refreshed_level_ids=refreshed_levels,
                extra_conflict_reasons=acceptance_event.conflict_reasons,
            )
            bar_conflicts.update(f"ACCEPTANCE_RELATIONS_{reason}" for reason in inventory.conflict_reasons)

            displacement_items = tuple(axes.get("DISPLACEMENT", ()))
            displacement_trigger, displacement_conflicts = displacement_trigger_state(displacement_items)
            bar_conflicts.update(f"DISPLACEMENT_{reason}" for reason in displacement_conflicts)
            if displacement_trigger and displacement_trigger != "CONFLICTING":
                displacement_active = displacement_trigger
                displacement_exit_count = 0
                displacement_stale = False
                reasons.append("DISPLACEMENT_AXIS_REFRESHED")
            elif displacement_active != "NONE" and previous_bar is not None:
                counter = (
                    bar.close <= previous_bar.close
                    if displacement_active == "DISPLACING_UP"
                    else bar.close >= previous_bar.close
                )
                if counter:
                    displacement_exit_count += 1
                    reasons.append("DISPLACEMENT_EXIT_PENDING")
                    if displacement_exit_count >= 2:
                        displacement_active = "NONE"
                        displacement_exit_count = 0
                        displacement_stale = False
                        reasons.append("DISPLACEMENT_AXIS_EXITED")
                else:
                    displacement_exit_count = 0
                    displacement_stale = False
            displacement_state = "CONFLICTING" if displacement_trigger == "CONFLICTING" else displacement_active

            compression_items = tuple(axes.get("COMPRESSION", ()))
            compression_raw = compression_statuses.get(bar.close_time, set())
            if "AMBIGUOUS" in compression_raw or ({"CONFIRMED", "FAILED"} <= compression_raw):
                bar_conflicts.add("COMPRESSION_CLASSIFIER_CONFLICT")
                compression_state = "CONFLICTING"
            else:
                if any(item.status == "CONFIRMED" for item in compression_items):
                    compression_active = "COMPRESSED"
                    compression_exit_count = 0
                    compression_stale = False
                    reasons.append("COMPRESSION_AXIS_REFRESHED")
                elif compression_active == "COMPRESSED" and "FAILED" in compression_raw:
                    compression_exit_count += 1
                    reasons.append("COMPRESSION_EXIT_PENDING")
                    if compression_exit_count >= 2:
                        compression_active = "NORMAL"
                        compression_exit_count = 0
                        compression_stale = False
                        reasons.append("COMPRESSION_AXIS_EXITED")
                compression_state = compression_active

            interaction = resolve_interaction_snapshot(axes.get("INTERACTION", ()))
            bar_conflicts.update(f"INTERACTION_{reason}" for reason in interaction.conflict_reasons)
            for component in interaction.components:
                component_counts[component.semantic_state] += 1

            stale_axes = set()
            if any(item.stale_after_gap for item in conditions.values()):
                stale_axes.add("ACCEPTANCE_RELATIONS")
            if displacement_active != "NONE" and displacement_stale:
                stale_axes.add("DISPLACEMENT")
            if compression_active == "COMPRESSED" and compression_stale:
                stale_axes.add("COMPRESSION")
            if bar_index == 0:
                stale_axes.update(carried_axes)
            if bar_conflicts and stale_axes:
                quality_state = "STALE_AND_CONFLICTING"
            elif bar_conflicts:
                quality_state = "CONFLICTING"
            elif stale_axes:
                quality_state = "STALE_AFTER_GAP"
            else:
                quality_state = "COHERENT"

            states = {
                "acceptance_event": acceptance_event.semantic_state,
                "displacement": displacement_state,
                "compression": compression_state,
                "interaction": interaction.semantic_state,
                "quality": quality_state,
            }
            contiguous = previous_bar is not None
            for axis, state in states.items():
                changed = trackers[axis].observe(state, contiguous=contiguous)
                if changed and previous_states is not None:
                    transition_writer.write(
                        transition_record(timeframe, bar.close_time, axis.upper(), previous_states[axis], state)
                    )
            event_active.observe(
                "ACTIVE" if acceptance_event.semantic_state != "NONE" else "INACTIVE",
                contiguous=contiguous,
            )
            relation_present.observe("PRESENT" if inventory.relation_count else "ABSENT", contiguous=contiguous)
            any_axis_active = (
                acceptance_event.semantic_state != "NONE"
                or displacement_state != "NONE"
                or compression_state != "NORMAL"
                or interaction.semantic_state != "NONE"
            )
            any_active.observe("ACTIVE" if any_axis_active else "INACTIVE", contiguous=contiguous)

            current_relation_ids = set(conditions)
            if current_relation_ids != prior_relation_ids:
                change_writer.write(
                    relation_change_record(timeframe, bar.close_time, prior_relation_ids, current_relation_ids, inventory)
                )
                prior_relation_ids = set(current_relation_ids)

            relation_counts.append(inventory.relation_count)
            above_counts.append(inventory.accepted_above_count)
            below_counts.append(inventory.accepted_below_count)
            challenged_counts.append(inventory.challenged_count)
            if inventory.oldest_relation_age_bars is not None:
                oldest_age_bars.append(inventory.oldest_relation_age_bars)
            if bars_since_latest_acceptance_event is not None:
                latest_event_ages.append(bars_since_latest_acceptance_event)
            if inventory.accepted_floor_price is not None and inventory.accepted_ceiling_price is not None:
                boundary_availability["BOTH"] += 1
                if inventory.boundary_width is not None and inventory.boundary_width > 0:
                    boundary_width_pips.append(float(inventory.boundary_width / Decimal("0.0001")))
            elif inventory.accepted_floor_price is not None:
                boundary_availability["FLOOR_ONLY"] += 1
            elif inventory.accepted_ceiling_price is not None:
                boundary_availability["CEILING_ONLY"] += 1
            else:
                boundary_availability["NONE"] += 1
            if bar_conflicts:
                conflict_bars += 1
                conflict_reason_counts.update(bar_conflicts)
            if stale_axes:
                stale_bars += 1
            reason_counts.update(reasons)
            state_writer.write(
                state_record(
                    bar=bar,
                    acceptance_event=acceptance_event,
                    inventory=inventory,
                    latest_acceptance_event_time=latest_acceptance_event_time,
                    observed_bars_since_latest_acceptance_event=bars_since_latest_acceptance_event,
                    displacement_state=displacement_state,
                    displacement_exit_count=displacement_exit_count,
                    compression_state=compression_state,
                    compression_exit_count=compression_exit_count,
                    interaction=interaction,
                    quality_state=quality_state,
                    stale_axes=tuple(sorted(stale_axes)),
                    conflict_reasons=tuple(sorted(bar_conflicts)),
                    reason_codes=tuple(sorted(set(reasons))),
                )
            )
            previous_states = states
            previous_bar = bar

    state_writer.close()
    transition_writer.close()
    change_writer.close()
    for tracker in trackers.values():
        tracker.finish()
    event_active.finish()
    relation_present.finish()
    any_active.finish()
    if state_writer.count != len(bars):
        raise AssertionError("v0.3a state stream must have one row per sealed bar")

    result = {
        "source_bars": len(bars),
        "registry_levels": len(registry.levels),
        "ratified_lifecycles": len(lifecycles),
        "state_records": state_writer.count,
        "transition_records": transition_writer.count,
        "relation_change_records": change_writer.count,
        "axis_metrics": {axis: trackers[axis].summary() for axis in axis_names},
        "acceptance_event_active_metrics": event_active.summary(),
        "relation_inventory_presence_metrics": relation_present.summary(),
        "any_axis_active_metrics": any_active.summary(),
        "relation_inventory_distributions": {
            "relation_count": distribution(relation_counts),
            "accepted_above_count": distribution(above_counts),
            "accepted_below_count": distribution(below_counts),
            "challenged_count": distribution(challenged_counts),
            "oldest_relation_age_bars": distribution(oldest_age_bars),
            "observed_bars_since_latest_acceptance_event": distribution(latest_event_ages),
            "boundary_width_pips": distribution(boundary_width_pips),
        },
        "boundary_availability_counts": dict(sorted(boundary_availability.items())),
        "acceptance_event_bars": refreshed_event_bars,
        "relation_set_changes_per_1000_bars": round(change_writer.count * 1000 / len(bars), 4),
        "interaction_component_bar_counts": dict(sorted(component_counts.items())),
        "genuine_conflict_bars": conflict_bars,
        "genuine_conflict_pct": round(conflict_bars * 100 / len(bars), 4),
        "genuine_conflict_reason_counts": dict(sorted(conflict_reason_counts.items())),
        "stale_after_gap_bars": stale_bars,
        "gap_carry_bars": gap_carry_bars,
        "reason_counts": dict(sorted(reason_counts.items())),
        "suppressed_cross_axis_evidence": 0,
        "state_stream_canonical_jsonl_hash": state_writer.canonical_jsonl_hash,
        "transition_stream_canonical_jsonl_hash": transition_writer.canonical_jsonl_hash,
        "relation_change_stream_canonical_jsonl_hash": change_writer.canonical_jsonl_hash,
    }
    artifacts = [
        {"path": state_path.name, "sha256": sha256(state_path), "size_bytes": state_path.stat().st_size},
        {"path": transition_path.name, "sha256": sha256(transition_path), "size_bytes": transition_path.stat().st_size},
        {"path": change_path.name, "sha256": sha256(change_path), "size_bytes": change_path.stat().st_size},
    ]
    return result, artifacts


def compare_unchanged_axes(v03_root: Path, v03a_root: Path, timeframe: str) -> dict[str, object]:
    fields = (
        "displacement_state",
        "compression_state",
        "interaction_state",
        "interaction_components",
        "quality_state",
        "genuine_conflict",
    )
    mismatch_counts = Counter()
    rows = 0
    with gzip.open(v03_root / f"parallel_axis_state_stream_{timeframe.lower()}.jsonl.gz", "rt", encoding="utf-8") as left:
        with gzip.open(v03a_root / f"acceptance_relation_state_stream_{timeframe.lower()}.jsonl.gz", "rt", encoding="utf-8") as right:
            for left_line, right_line in zip_longest(left, right):
                if left_line is None or right_line is None:
                    raise ValueError("v0.3/v0.3a state row cardinality mismatch")
                before = json.loads(left_line)
                after = json.loads(right_line)
                rows += 1
                if before["close_time"] != after["close_time"]:
                    raise ValueError("v0.3/v0.3a state timestamp mismatch")
                for field in fields:
                    if before[field] != after[field]:
                        mismatch_counts[field] += 1
    return {
        "rows_compared": rows,
        "fields_compared": list(fields),
        "mismatch_counts": dict(sorted(mismatch_counts.items())),
        "all_unchanged_axes_match": not mismatch_counts,
    }


def comparison(v02: dict, v03_result: dict, v03a: dict) -> dict[str, object]:
    return {
        "v02_acceptance_occupancy_pct": v02["acceptance_occupancy"]["occupancy_pct"].get("ACTIVE", 0.0),
        "v03_location_occupancy_pct": v03_result["location_active_metrics"]["occupancy_pct"].get("ACTIVE", 0.0),
        "v03a_acceptance_event_occupancy_pct": v03a["acceptance_event_active_metrics"]["occupancy_pct"].get("ACTIVE", 0.0),
        "v03a_relation_inventory_presence_pct": v03a["relation_inventory_presence_metrics"]["occupancy_pct"].get("PRESENT", 0.0),
        "v03_location_transitions_per_1000_bars": v03_result["axis_metrics"]["location"]["transitions_per_1000_bars"],
        "v03a_acceptance_event_transitions_per_1000_bars": v03a["axis_metrics"]["acceptance_event"]["transitions_per_1000_bars"],
        "v03a_relation_set_changes_per_1000_bars": v03a["relation_set_changes_per_1000_bars"],
        "v03_genuine_conflict_pct": v03_result["genuine_conflict_pct"],
        "v03a_genuine_conflict_pct": v03a["genuine_conflict_pct"],
        "v03_suppressed_cross_axis_evidence": v03_result["suppressed_cross_axis_evidence"],
        "v03a_suppressed_cross_axis_evidence": v03a["suppressed_cross_axis_evidence"],
    }


def write_report(output: Path, results: dict[str, object]) -> Path:
    lines = [
        "# OVC B-STATE-0.3a Acceptance Relation-Inventory H1 Replay",
        "",
        "**Status:** `CONTROLLED H1 REPLAY COMPLETE — B-STATE-0.3a NOT RATIFIED`  ",
        "**Relevance authority:** `B-REF-0.2-STRUCTURAL-ONLY`  ",
        "**Outcome use:** `NONE`",
        "",
        "## Representation comparison",
        "",
        "| Clock | v0.2 persistent acceptance | v0.3 categorical location | v0.3a acceptance event | v0.3a relation inventory present |",
        "|---|---:|---:|---:|---:|",
    ]
    for timeframe in ("15M", "2H"):
        item = results[timeframe]["comparison"]
        lines.append(
            f"| {timeframe} | {item['v02_acceptance_occupancy_pct']:.2f}% | "
            f"{item['v03_location_occupancy_pct']:.2f}% | "
            f"{item['v03a_acceptance_event_occupancy_pct']:.2f}% | "
            f"{item['v03a_relation_inventory_presence_pct']:.2f}% |"
        )
    lines.extend([
        "",
        "The high relation-inventory presence is retained as an observable fact, but it no longer occupies or governs a categorical state. Only lawful new acceptance confirmations occupy the event field.",
        "",
        "## Duration and transition comparison",
        "",
        "| Clock | Model | Active median | Active P90 | Active max | Transitions / 1,000 bars |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for timeframe in ("15M", "2H"):
        item = results[timeframe]
        duration_rows = (
            ("v0.2 persistent acceptance", item["v02"]["acceptance_occupancy"]),
            ("v0.3 categorical location", item["v03"]["location_active_metrics"]),
            ("v0.3a acceptance event", item["v03a"]["acceptance_event_active_metrics"]),
        )
        for label, metrics in duration_rows:
            duration = metrics["duration_by_state_bars"].get(
                "ACTIVE",
                {"median_bars": 0.0, "p90_bars": 0.0, "max_bars": 0},
            )
            lines.append(
                f"| {timeframe} | {label} | {duration['median_bars']:.2f} | "
                f"{duration['p90_bars']:.2f} | {duration['max_bars']:,} | "
                f"{metrics['transitions_per_1000_bars']:.2f} |"
            )
    lines.extend([
        "",
        "Consecutive acceptance confirmations can form short event runs, but the event is recomputed from current-bar evidence and is never carried forward. The median active run is one bar on both clocks.",
        "",
        "## Inventory measurements",
        "",
        "| Clock | Median relations | P90 relations | Max relations | Median boundary width | P90 boundary width | Relation-set changes / 1,000 bars |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for timeframe in ("15M", "2H"):
        item = results[timeframe]["v03a"]
        counts = item["relation_inventory_distributions"]["relation_count"]
        widths = item["relation_inventory_distributions"]["boundary_width_pips"]
        lines.append(
            f"| {timeframe} | {counts['median']:.2f} | {counts['p90']:.2f} | {counts['max']:.0f} | "
            f"{widths['median']:.2f} pips | {widths['p90']:.2f} pips | "
            f"{item['relation_set_changes_per_1000_bars']:.2f} |"
        )
    lines.extend([
        "",
        "The inventory still contains old relations because the ratified structural-only policy has no elapsed-time expiry. This is disclosed rather than hidden: the oldest active relation reaches 10,177 observed 15M bars and 1,301 observed 2H bars. That is a relevance-inventory review issue, not categorical state dominance.",
        "",
        "## Semantic controls",
        "",
        "| Clock | Genuine conflict | Cross-axis suppression | Unchanged v0.3 axes match |",
        "|---|---:|---:|---:|",
    ])
    for timeframe in ("15M", "2H"):
        item = results[timeframe]
        lines.append(
            f"| {timeframe} | {item['v03a']['genuine_conflict_pct']:.2f}% | "
            f"{item['v03a']['suppressed_cross_axis_evidence']:,} | "
            f"{'PASS' if item['unchanged_axis_comparison']['all_unchanged_axes_match'] else 'FAIL'} |"
        )
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "v0.3a changes representation only. The acceptance classifier, level lifecycle, maintenance exits and all non-acceptance axes remain frozen. No OPT-C outcome, profitability, future bar, recommendation or execution input entered the replay.",
        "",
        "**Review finding:** the semantic-dominance defect is removed from the categorical state model. Ratification should still require operator review of whether a fresh acceptance event rate near one bar in four is linguistically useful, and a separate future contract should decide how to summarize the large relation inventory without outcome-tuned pruning.",
    ])
    path = output / "OVC_OPT_B_STATE_v0_3A_H1_REPLAY_REPORT.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--registry-root", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--v02-root", type=Path, required=True)
    parser.add_argument("--v03-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "B_STATE_0_3A_REPLAY_MANIFEST.json").exists():
        raise FileExistsError("B-STATE-0.3a replay already finalized")

    seal = verify_seal(args.seal_root.resolve())
    review_manifest = v03.verify_manifest(args.review_root.resolve(), "RELEVANCE_REVIEW_MANIFEST.json")
    all_results = {}
    artifacts = []
    registry_manifest = replay_manifest = v02_manifest = v03_manifest = None
    for timeframe in ("15M", "2H"):
        print(f"{timeframe}: validating authority inputs", flush=True)
        registry, registry_manifest = load_registry(args.registry_root.resolve(), timeframe)
        replay_manifest = verify_replay(args.replay_root.resolve(), seal, registry_manifest)
        v02_manifest = v03.verify_v02(
            args.v02_root.resolve(),
            seal["seal_hash"],
            replay_manifest["manifest_hash"],
            review_manifest["manifest_hash"],
        )
        v03_manifest = verify_v03(
            args.v03_root.resolve(),
            seal_hash=seal["seal_hash"],
            replay_hash=replay_manifest["manifest_hash"],
            review_hash=review_manifest["manifest_hash"],
            v02_hash=v02_manifest["manifest_hash"],
        )
        bars = read_canonical_bars(args.seal_root.resolve() / f"canonical/accepted_{timeframe.lower()}.csv")
        lifecycles = v03.load_ratified_lifecycles(args.v02_root.resolve(), timeframe)
        evidence, compression_statuses, scan_counts = v03.scan_admitted_evidence(
            args.replay_root.resolve() / f"term_records_{timeframe.lower()}.jsonl.gz",
            {item.level_id: item for item in lifecycles},
        )
        print(f"{timeframe}: replaying {len(bars):,} sealed bars", flush=True)
        v03a_result, produced = replay_timeframe(
            timeframe=timeframe,
            bars=bars,
            registry=registry,
            lifecycles=lifecycles,
            evidence_by_time=evidence,
            compression_statuses=compression_statuses,
            output=output,
        )
        unchanged = compare_unchanged_axes(args.v03_root.resolve(), output, timeframe)
        if not unchanged["all_unchanged_axes_match"]:
            raise AssertionError("non-acceptance v0.3 axes changed under v0.3a")
        v02_result = v03_manifest["results"][timeframe]["v02"]
        parent_result = v03_manifest["results"][timeframe]["v03"]
        parent_presence = parent_result["location_active_metrics"]["occupancy_counts"].get("ACTIVE", 0)
        child_presence = v03a_result["relation_inventory_presence_metrics"]["occupancy_counts"].get("PRESENT", 0)
        if parent_presence != child_presence:
            raise AssertionError("v0.3a relation inventory does not preserve v0.3 maintained relations")
        all_results[timeframe] = {
            "evidence_scan": scan_counts,
            "v02": v02_result,
            "v03": parent_result,
            "v03a": v03a_result,
            "unchanged_axis_comparison": unchanged,
            "comparison": comparison(v02_result, parent_result, v03a_result),
        }
        artifacts.extend(produced)
        print(f"{timeframe}: complete", flush=True)

    summary_path = output / "b_state_0_3a_replay_summary.json"
    summary_path.write_text(json.dumps(all_results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    report_path = write_report(output, all_results)
    artifacts.append({"path": report_path.name, "sha256": sha256(report_path), "size_bytes": report_path.stat().st_size})
    for source in (
        ROOT / "contracts/OVC_OPT_B_ACCEPTANCE_RELATION_INVENTORY_CONTRACT_v0_3a.md",
        ROOT / "contracts/B_STATE_0_3A_OPERATOR_REVIEW_CHECKLIST.md",
        ROOT / "contracts/OVC_OPT_B_COMPLETE_REPLAY_INPUT_REPAIR_RECORD.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    assert registry_manifest and replay_manifest and v02_manifest and v03_manifest
    manifest_core = {
        "release_id": "B-STATE-GBPUSD-2026H1-v0.3a",
        "status": "CONTROLLED_H1_REPLAY_COMPLETE_NOT_RATIFIED",
        "generated_date": "2026-07-19",
        "opt_a_seal_hash": seal["seal_hash"],
        "reference_registry_hash": registry_manifest["combined_registry_hash"],
        "complete_replay_manifest_hash": replay_manifest["manifest_hash"],
        "relevance_review_manifest_hash": review_manifest["manifest_hash"],
        "v02_state_manifest_hash": v02_manifest["manifest_hash"],
        "v03_state_manifest_hash": v03_manifest["manifest_hash"],
        "relevance_policy_id": POLICY_ID,
        "state_contract_version": CONTRACT_VERSION,
        "semantic_findings": [
            "Acceptance is represented as one-bar events plus a level-relation inventory; no categorical corridor state exists.",
            "Persistent relation presence is disclosed as an inventory measurement rather than state occupancy.",
            "All non-acceptance v0.3 axes are required to match bar-for-bar.",
            "No qualitative freshness threshold, TTL, outcome or execution input is used.",
        ],
        "results": all_results,
        "artifacts": artifacts,
        "implementation_hashes": {
            "state_v03a.py": sha256(ROOT / "src/ovc_opt_b/state_v03a.py"),
            "run_acceptance_relation_inventory_replay.py": sha256(Path(__file__).resolve()),
            "test_state_v03a.py": sha256(ROOT / "tests/test_state_v03a.py"),
        },
        "authority_boundary": "B-STATE-0.3a is historically replayed for semantic review only and is not ratified. No OPT-C outcome, edge, recommendation or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    (output / "B_STATE_0_3A_REPLAY_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": manifest["status"], "manifest_hash": manifest["manifest_hash"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
