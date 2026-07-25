from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, sha256, verify_seal  # noqa: E402
from ovc_opt_b import (  # noqa: E402
    AxisEvidence,
    LevelLifecycle,
    LocationCondition,
    acceptance_maintenance_passes,
    contiguous_segments,
    displacement_trigger_state,
    resolve_interaction_snapshot,
    resolve_location_snapshot,
)
from run_complete_opt_b_replay import (  # noqa: E402
    DeterministicJsonlGzipWriter,
    canonical_hash,
    load_registry,
)
from run_relevance_semantic_sensitivity_review import verify_replay  # noqa: E402


CONTRACT_VERSION = "B-STATE-0.3"
POLICY_ID = "B-REF-0.2-STRUCTURAL-ONLY"
EXPECTED_STEP = {"15M": timedelta(minutes=15), "2H": timedelta(hours=2)}


class MetricTracker:
    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.episodes: dict[str, list[int]] = defaultdict(list)
        self.transitions = 0
        self.comparable_pairs = 0
        self._state: str | None = None
        self._length = 0

    def observe(self, state: str, *, contiguous: bool) -> bool:
        self.counts[state] += 1
        changed = False
        if self._state is None or not contiguous:
            self._finish_episode()
            self._state = state
            self._length = 1
        else:
            self.comparable_pairs += 1
            if state != self._state:
                changed = True
                self.transitions += 1
                self._finish_episode()
                self._state = state
                self._length = 1
            else:
                self._length += 1
        return changed

    def _finish_episode(self) -> None:
        if self._state is not None and self._length:
            self.episodes[self._state].append(self._length)

    def finish(self) -> None:
        self._finish_episode()
        self._state = None
        self._length = 0

    @staticmethod
    def _duration(values: list[int]) -> dict[str, float | int]:
        ordered = sorted(values)
        if not ordered:
            return {"episodes": 0, "mean_bars": 0.0, "median_bars": 0.0, "p90_bars": 0, "max_bars": 0}
        length = len(ordered)
        midpoint = length // 2
        median = (
            float(ordered[midpoint])
            if length % 2
            else (ordered[midpoint - 1] + ordered[midpoint]) / 2
        )
        return {
            "episodes": length,
            "mean_bars": round(sum(ordered) / length, 4),
            "median_bars": median,
            "p90_bars": ordered[max(0, math.ceil(length * 0.90) - 1)],
            "max_bars": ordered[-1],
        }

    def summary(self) -> dict[str, object]:
        total = sum(self.counts.values())
        return {
            "occupancy_counts": dict(sorted(self.counts.items())),
            "occupancy_pct": {
                key: round(value * 100 / total, 4) if total else 0.0
                for key, value in sorted(self.counts.items())
            },
            "transition_count": self.transitions,
            "comparable_adjacent_pairs": self.comparable_pairs,
            "transitions_per_1000_bars": round(self.transitions * 1000 / total, 4) if total else 0.0,
            "duration_by_state_bars": {
                state: self._duration(values) for state, values in sorted(self.episodes.items())
            },
        }


def parse_lifecycle(row: dict) -> LevelLifecycle:
    return LevelLifecycle(
        level_id=row["level_id"],
        relevant_from=datetime.fromisoformat(row["relevant_from"]),
        retired_at=datetime.fromisoformat(row["retired_at"]) if row["retired_at"] else None,
        retirement_reason=row["retirement_reason"],
        retirement_trigger_id=row["retirement_trigger_id"],
        policy_id=row["policy_id"],
        lifecycle_id=row["lifecycle_id"],
    )


def verify_manifest(path: Path, filename: str) -> dict:
    manifest = json.loads((path / filename).read_text(encoding="utf-8"))
    expected = manifest["manifest_hash"]
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != expected:
        raise ValueError(f"{filename} self-hash mismatch")
    return manifest


def verify_v02(v02_root: Path, seal_hash: str, replay_hash: str, review_hash: str) -> dict:
    manifest = verify_manifest(v02_root, "COMPOUND_STATE_REPLAY_MANIFEST.json")
    if manifest["opt_a_seal_hash"] != seal_hash:
        raise ValueError("v0.2 OPT-A authority mismatch")
    if manifest["complete_replay_manifest_hash"] != replay_hash:
        raise ValueError("v0.2 complete-replay authority mismatch")
    if manifest["relevance_review_manifest_hash"] != review_hash:
        raise ValueError("v0.2 relevance-review authority mismatch")
    for artifact in manifest["artifacts"]:
        artifact_path = v02_root / artifact["path"]
        if sha256(artifact_path) != artifact["sha256"]:
            raise ValueError(f"v0.2 artifact hash mismatch: {artifact_path.name}")
    return manifest


def load_ratified_lifecycles(v02_root: Path, timeframe: str) -> tuple[LevelLifecycle, ...]:
    path = v02_root / f"ratified_lifecycles_{timeframe.lower()}.jsonl"
    result = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            result.append(parse_lifecycle(json.loads(line)))
    if any(item.policy_id != POLICY_ID for item in result):
        raise ValueError("non-ratified lifecycle entered B-STATE-0.3")
    return tuple(result)


def evidence_from_row(row: dict) -> AxisEvidence | None:
    status = row["status"]
    if status not in {"CONFIRMED", "AMBIGUOUS"}:
        return None
    term = row["term_id"]
    direction = row["direction"]
    level_id = row["reference_level_id"]
    common = {
        "direction": direction,
        "level_id": level_id,
        "term_record_id": row["term_record_id"],
        "status": status,
    }
    if term == "B.TERM.ACCEPTANCE.v0.1":
        value = row["measurements"].get("return_min")
        return AxisEvidence(
            "LOCATION",
            "ACCEPTANCE",
            "ACCEPTED_ABOVE" if direction == "UP" else "ACCEPTED_BELOW",
            return_min=Decimal(value) if value is not None else None,
            **common,
        )
    if term == "B.TERM.DISPLACEMENT.v0.1":
        return AxisEvidence("DISPLACEMENT", "DISPLACEMENT", f"DISPLACING_{direction}", **common)
    if term == "B.TERM.COMPRESSION.v0.1":
        return AxisEvidence("COMPRESSION", "COMPRESSION", "COMPRESSED", **common)
    if term == "B.TERM.RECLAIM.v0.1":
        return AxisEvidence(
            "INTERACTION",
            "RECLAIM",
            "RECLAIMED_ABOVE" if direction == "UP" else "RECLAIMED_BELOW",
            **common,
        )
    if term == "B.TERM.REJECTION.v0.1":
        return AxisEvidence("INTERACTION", "REJECTION", f"REJECTED_{direction}", **common)
    if term == "B.TERM.REFERENCE_LEVEL_BREACH_RESPONSE.v0.1":
        return AxisEvidence("INTERACTION", "BREACH_RESPONSE", f"BREACH_RESPONSE_{direction}", **common)
    return None


def scan_admitted_evidence(
    term_path: Path,
    lifecycle_map: dict[str, LevelLifecycle],
) -> tuple[dict[datetime, dict[str, list[AxisEvidence]]], dict[datetime, set[str]], dict[str, int]]:
    by_time: dict[datetime, dict[str, list[AxisEvidence]]] = defaultdict(lambda: defaultdict(list))
    compression_statuses: dict[datetime, set[str]] = defaultdict(set)
    counts = Counter()
    with gzip.open(term_path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            if line_number % 250_000 == 0:
                print(f"{term_path.name}: scanned {line_number:,} rows", flush=True)
            term = row["term_id"]
            at = datetime.fromisoformat(row["first_valid_time"])
            if term == "B.TERM.COMPRESSION.v0.1":
                compression_statuses[at].add(row["status"])
            evidence = evidence_from_row(row)
            if evidence is None:
                continue
            if evidence.level_id is not None:
                lifecycle = lifecycle_map[evidence.level_id]
                anchor = datetime.fromisoformat(row["anchor_time"])
                if not lifecycle.is_relevant(anchor):
                    counts["excluded_irrelevant"] += 1
                    continue
            by_time[at][evidence.axis].append(evidence)
            counts[f"admitted_{evidence.axis.lower()}"] += 1
            counts[f"admitted_status_{evidence.status.lower()}"] += 1
    counts["scanned_rows"] = line_number if "line_number" in locals() else 0
    return by_time, compression_statuses, dict(sorted(counts.items()))


def interaction_to_dict(snapshot) -> list[dict[str, object]]:
    return [
        {
            "semantic_state": item.semantic_state,
            "direction": item.direction,
            "support_level_ids": list(item.support_level_ids),
            "trigger_term_record_ids": list(item.trigger_term_record_ids),
        }
        for item in snapshot.components
    ]


def state_record(
    *,
    bar,
    location,
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
        "location_state": location.semantic_state,
        "location_above_level_ids": list(location.above_level_ids),
        "location_below_level_ids": list(location.below_level_ids),
        "location_challenged_level_ids": list(location.challenged_level_ids),
        "location_trigger_term_record_ids": list(location.trigger_term_record_ids),
        "displacement_state": displacement_state,
        "displacement_exit_pending_count": displacement_exit_count,
        "compression_state": compression_state,
        "compression_exit_pending_count": compression_exit_count,
        "interaction_state": interaction.semantic_state,
        "interaction_components": interaction_to_dict(interaction),
        "quality_state": quality_state,
        "stale_axes": list(stale_axes),
        "genuine_conflict": bool(conflict_reasons),
        "conflict_reasons": list(conflict_reasons),
        "reason_codes": list(reason_codes),
        "state_contract_version": CONTRACT_VERSION,
        "relevance_policy_id": POLICY_ID,
    }
    return {**core, "state_record_id": f"parallel-state:{canonical_hash(core)}"}


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


def legacy_v02_metrics(v02_root: Path, timeframe: str) -> dict[str, object]:
    tracker = MetricTracker()
    accepted = MetricTracker()
    previous_time = None
    path = v02_root / f"compound_state_stream_{timeframe.lower()}.jsonl.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            at = datetime.fromisoformat(row["close_time"])
            contiguous = previous_time is not None and at - previous_time == EXPECTED_STEP[timeframe]
            state = row["semantic_state"]
            tracker.observe(state, contiguous=contiguous)
            accepted.observe("ACTIVE" if state.startswith("ACCEPTED_") else "INACTIVE", contiguous=contiguous)
            previous_time = at
    tracker.finish()
    accepted.finish()
    return {
        "exclusive_state": tracker.summary(),
        "acceptance_occupancy": accepted.summary(),
    }


def replay_timeframe(
    *,
    timeframe: str,
    bars,
    registry,
    lifecycles: tuple[LevelLifecycle, ...],
    evidence_by_time,
    compression_statuses,
    output: Path,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    level_prices = {level.level_id: level.price for level in registry.levels}
    lifecycle_map = {item.level_id: item for item in lifecycles}
    conditions: dict[str, LocationCondition] = {}
    displacement_active = "NONE"
    displacement_exit_count = 0
    displacement_stale = False
    compression_active = "NORMAL"
    compression_exit_count = 0
    compression_stale = False

    axis_names = ("location", "displacement", "compression", "interaction", "quality")
    trackers = {axis: MetricTracker() for axis in axis_names}
    location_active = MetricTracker()
    any_active = MetricTracker()
    component_counts = Counter()
    conflict_reasons_count = Counter()
    reason_counts = Counter()
    conflict_bars = 0
    stale_bars = 0
    carried_gap_bars = 0

    state_path = output / f"parallel_axis_state_stream_{timeframe.lower()}.jsonl.gz"
    transition_path = output / f"parallel_axis_transition_records_{timeframe.lower()}.jsonl.gz"
    state_writer = DeterministicJsonlGzipWriter(state_path)
    transition_writer = DeterministicJsonlGzipWriter(transition_path)

    first_segment = True
    for segment in contiguous_segments(bars):
        gap = not first_segment
        first_segment = False
        carried_axes: set[str] = set()
        if gap:
            if conditions:
                carried_axes.add("LOCATION")
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
        previous_states: dict[str, str] | None = None
        for bar_index, bar in enumerate(segment):
            reasons: list[str] = []
            bar_conflicts: set[str] = set()
            if bar_index == 0 and carried_axes:
                carried_gap_bars += 1
                reasons.append("GAP_CARRY_FORWARD_AXES_STALE")

            axes = evidence_by_time.get(bar.close_time, {})
            location_evidence = tuple(axes.get("LOCATION", ()))
            refreshed_levels: set[str] = set()
            by_level: dict[str, list[AxisEvidence]] = defaultdict(list)
            for item in location_evidence:
                if item.level_id is not None:
                    by_level[item.level_id].append(item)
                if item.status == "AMBIGUOUS":
                    bar_conflicts.add("LOCATION_CLASSIFIER_AMBIGUITY")
            for level_id, items in sorted(by_level.items()):
                confirmed = [item for item in items if item.status == "CONFIRMED"]
                directions = {item.direction for item in confirmed}
                if len(directions) > 1:
                    bar_conflicts.add("SAME_LEVEL_ACCEPTANCE_OPPOSITE_DIRECTIONS")
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
                refreshed_levels.add(level_id)
                reasons.append("LOCATION_CONDITION_REFRESHED" if current else "LOCATION_CONDITION_ENTERED")

            for level_id in tuple(sorted(conditions)):
                item = conditions[level_id]
                lifecycle = lifecycle_map[level_id]
                if (
                    lifecycle.retirement_reason == "RANGE_SUPERSEDED"
                    and lifecycle.retired_at is not None
                    and bar.open_time >= lifecycle.retired_at
                ):
                    del conditions[level_id]
                    reasons.append("LOCATION_ENDED_RANGE_SUPERSEDED")
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
                    reasons.append("LOCATION_MAINTENANCE_FAILED")
                    if item.challenge_count >= 2:
                        del conditions[level_id]
                        reasons.append("LOCATION_CONDITION_EXITED")

            location = resolve_location_snapshot(
                conditions,
                level_prices=level_prices,
                extra_conflict_reasons=(
                    reason
                    for reason in bar_conflicts
                    if reason.startswith("LOCATION_") or "ACCEPTANCE" in reason
                ),
            )
            bar_conflicts.update(location.conflict_reasons)

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
                stale_axes.add("LOCATION")
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
                "location": location.semantic_state,
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
            location_active.observe(
                "ACTIVE" if location.semantic_state != "NEUTRAL" else "INACTIVE",
                contiguous=contiguous,
            )
            any_axis_active = (
                location.semantic_state != "NEUTRAL"
                or displacement_state != "NONE"
                or compression_state != "NORMAL"
                or interaction.semantic_state != "NONE"
            )
            any_active.observe("ACTIVE" if any_axis_active else "INACTIVE", contiguous=contiguous)

            if bar_conflicts:
                conflict_bars += 1
                conflict_reasons_count.update(bar_conflicts)
            if stale_axes:
                stale_bars += 1
            reason_counts.update(reasons)
            state_writer.write(
                state_record(
                    bar=bar,
                    location=location,
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
    for tracker in trackers.values():
        tracker.finish()
    location_active.finish()
    any_active.finish()
    if state_writer.count != len(bars):
        raise AssertionError("parallel-axis state stream must have one row per sealed bar")
    result = {
        "source_bars": len(bars),
        "registry_levels": len(registry.levels),
        "ratified_lifecycles": len(lifecycles),
        "state_records": state_writer.count,
        "transition_records": transition_writer.count,
        "axis_metrics": {axis: trackers[axis].summary() for axis in axis_names},
        "location_active_metrics": location_active.summary(),
        "any_axis_active_metrics": any_active.summary(),
        "interaction_component_bar_counts": dict(sorted(component_counts.items())),
        "genuine_conflict_bars": conflict_bars,
        "genuine_conflict_pct": round(conflict_bars * 100 / len(bars), 4),
        "genuine_conflict_reason_counts": dict(sorted(conflict_reasons_count.items())),
        "stale_after_gap_bars": stale_bars,
        "gap_carry_bars": carried_gap_bars,
        "reason_counts": dict(sorted(reason_counts.items())),
        "suppressed_cross_axis_evidence": 0,
        "state_stream_canonical_jsonl_hash": state_writer.canonical_jsonl_hash,
        "transition_stream_canonical_jsonl_hash": transition_writer.canonical_jsonl_hash,
    }
    artifacts = [
        {"path": state_path.name, "sha256": sha256(state_path), "size_bytes": state_path.stat().st_size},
        {"path": transition_path.name, "sha256": sha256(transition_path), "size_bytes": transition_path.stat().st_size},
    ]
    return result, artifacts


def active_duration(summary: dict[str, object], state: str = "ACTIVE") -> dict[str, object]:
    return summary["duration_by_state_bars"].get(state, MetricTracker._duration([]))


def comparison_for(v02: dict, v03: dict, v02_manifest_result: dict) -> dict[str, object]:
    v02_accept = v02["acceptance_occupancy"]
    v03_location = v03["location_active_metrics"]
    return {
        "v02_acceptance_occupancy_pct": v02_accept["occupancy_pct"].get("ACTIVE", 0.0),
        "v03_location_occupancy_pct": v03_location["occupancy_pct"].get("ACTIVE", 0.0),
        "v02_acceptance_duration_bars": active_duration(v02_accept),
        "v03_location_duration_bars": active_duration(v03_location),
        "v02_exclusive_transitions_per_1000_bars": v02["exclusive_state"]["transitions_per_1000_bars"],
        "v03_axis_transitions_per_1000_bars": {
            axis: values["transitions_per_1000_bars"]
            for axis, values in v03["axis_metrics"].items()
        },
        "v02_ambiguous_occupancy_pct": v02["exclusive_state"]["occupancy_pct"].get("AMBIGUOUS", 0.0),
        "v02_conflicting_trigger_count": v02_manifest_result["conflicting_compound_triggers"],
        "v03_genuine_conflict_pct": v03["genuine_conflict_pct"],
        "v03_genuine_conflict_bars": v03["genuine_conflict_bars"],
        "v02_suppressed_lower_precedence_triggers": v02_manifest_result["suppressed_lower_precedence_triggers"],
        "v03_suppressed_cross_axis_evidence": v03["suppressed_cross_axis_evidence"],
    }


def write_report(output: Path, results: dict[str, object]) -> Path:
    lines = [
        "# OVC B-STATE-0.3 Parallel-Axis H1 Replay and v0.2 Comparison",
        "",
        "**Status:** `CONTROLLED H1 REPLAY COMPLETE — B-STATE-0.3 NOT RATIFIED`  ",
        "**Relevance authority:** `B-REF-0.2-STRUCTURAL-ONLY`  ",
        "**Outcome use:** `NONE`",
        "",
        "## Headline comparison",
        "",
        "| Clock | v0.2 acceptance occupancy | v0.3 location occupancy | v0.2 ambiguity occupancy | v0.3 genuine conflict | v0.2 suppressed | v0.3 suppressed |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for timeframe in ("15M", "2H"):
        item = results[timeframe]["comparison"]
        lines.append(
            f"| {timeframe} | {item['v02_acceptance_occupancy_pct']:.2f}% | "
            f"{item['v03_location_occupancy_pct']:.2f}% | "
            f"{item['v02_ambiguous_occupancy_pct']:.2f}% | "
            f"{item['v03_genuine_conflict_pct']:.2f}% | "
            f"{item['v02_suppressed_lower_precedence_triggers']:,} | "
            f"{item['v03_suppressed_cross_axis_evidence']:,} |"
        )
    lines.extend([
        "",
        "## Decisive semantic finding",
        "",
        "Parallel axes solve the authority problem: acceptance no longer suppresses displacement, compression or interaction evidence, and topology-aware conflict does not mislabel different-level observations as contradictory. However, the proposed maintained-location rule creates a second saturation problem. Accepted-above lower levels and accepted-below higher levels accumulate into `ACCEPTED_CORRIDOR`, leaving the location axis active on nearly every H1 bar.",
        "",
        "`B-STATE-0.3` therefore remains blocked from ratification. The next revision must either represent acceptance as a level-relation collection without a categorical corridor state, or close accepted-through relations under an explicitly bounded lifecycle. This decision must be tested semantically before any OPT-C outcome is introduced.",
        "",
        "## State duration",
        "",
        "Durations are contiguous-bar episodes and split at every source gap.",
        "",
        "| Clock | Contract | Episode | Median bars | P90 bars | Maximum bars |",
        "|---|---|---|---:|---:|---:|",
    ])
    for timeframe in ("15M", "2H"):
        comparison = results[timeframe]["comparison"]
        for version, key, label in (
            ("v0.2", "v02_acceptance_duration_bars", "acceptance active"),
            ("v0.3", "v03_location_duration_bars", "location active"),
        ):
            duration = comparison[key]
            lines.append(
                f"| {timeframe} | {version} | {label} | {duration['median_bars']} | "
                f"{duration['p90_bars']} | {duration['max_bars']} |"
            )
    lines.extend([
        "",
        "## Transition frequency",
        "",
        "v0.2 reports its one exclusive state stream. v0.3 reports each independent axis; these rates must not be summed as though they were one state machine.",
        "",
        "| Clock | v0.2 exclusive | v0.3 location | displacement | compression | interaction | quality |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for timeframe in ("15M", "2H"):
        item = results[timeframe]["comparison"]
        rates = item["v03_axis_transitions_per_1000_bars"]
        lines.append(
            f"| {timeframe} | {item['v02_exclusive_transitions_per_1000_bars']:.2f} | "
            f"{rates['location']:.2f} | {rates['displacement']:.2f} | "
            f"{rates['compression']:.2f} | {rates['interaction']:.2f} | {rates['quality']:.2f} |"
        )
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "The comparison measures semantic behaviour only. It does not select v0.3 using returns, MFE/MAE, profitability or any OPT-C outcome. `B-STATE-0.3` remains a replayed candidate requiring operator review.",
    ])
    path = output / "OVC_OPT_B_STATE_v0_3_H1_COMPARISON_REPORT.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--registry-root", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--v02-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "B_STATE_0_3_REPLAY_MANIFEST.json").exists():
        raise FileExistsError("B-STATE-0.3 replay already finalized")

    seal = verify_seal(args.seal_root.resolve())
    review_manifest = verify_manifest(args.review_root.resolve(), "RELEVANCE_REVIEW_MANIFEST.json")
    all_results = {}
    artifacts = []
    registry_manifest = replay_manifest = v02_manifest = None
    for timeframe in ("15M", "2H"):
        print(f"{timeframe}: validating authority inputs", flush=True)
        registry, registry_manifest = load_registry(args.registry_root.resolve(), timeframe)
        replay_manifest = verify_replay(args.replay_root.resolve(), seal, registry_manifest)
        if review_manifest["opt_a_seal_hash"] != seal["seal_hash"]:
            raise ValueError("relevance review OPT-A authority mismatch")
        if review_manifest["complete_replay_manifest_hash"] != replay_manifest["manifest_hash"]:
            raise ValueError("relevance review complete-replay authority mismatch")
        v02_manifest = verify_v02(
            args.v02_root.resolve(),
            seal["seal_hash"],
            replay_manifest["manifest_hash"],
            review_manifest["manifest_hash"],
        )
        bars = read_canonical_bars(args.seal_root.resolve() / f"canonical/accepted_{timeframe.lower()}.csv")
        lifecycles = load_ratified_lifecycles(args.v02_root.resolve(), timeframe)
        if len(lifecycles) != len(registry.levels):
            raise ValueError("lifecycle and registry cardinality mismatch")
        evidence, compression_statuses, scan_counts = scan_admitted_evidence(
            args.replay_root.resolve() / f"term_records_{timeframe.lower()}.jsonl.gz",
            {item.level_id: item for item in lifecycles},
        )
        print(f"{timeframe}: replaying {len(bars):,} sealed bars", flush=True)
        v03, produced = replay_timeframe(
            timeframe=timeframe,
            bars=bars,
            registry=registry,
            lifecycles=lifecycles,
            evidence_by_time=evidence,
            compression_statuses=compression_statuses,
            output=output,
        )
        v02 = legacy_v02_metrics(args.v02_root.resolve(), timeframe)
        all_results[timeframe] = {
            "evidence_scan": scan_counts,
            "v02": v02,
            "v03": v03,
            "comparison": comparison_for(v02, v03, v02_manifest["results"][timeframe]),
        }
        artifacts.extend(produced)
        print(f"{timeframe}: complete", flush=True)

    summary_path = output / "b_state_0_3_comparison_summary.json"
    summary_path.write_text(json.dumps(all_results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    report_path = write_report(output, all_results)
    artifacts.append({"path": report_path.name, "sha256": sha256(report_path), "size_bytes": report_path.stat().st_size})
    for source in (
        ROOT / "contracts/OVC_OPT_B_PARALLEL_AXIS_STATE_CONTRACT_v0_3.md",
        ROOT / "contracts/B_STATE_0_3_OPERATOR_REVIEW_CHECKLIST.md",
        ROOT / "contracts/OVC_OPT_B_COMPLETE_REPLAY_INPUT_REPAIR_RECORD.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    assert registry_manifest and replay_manifest and v02_manifest
    manifest_core = {
        "release_id": "B-STATE-GBPUSD-2026H1-v0.3",
        "status": "CONTROLLED_H1_REPLAY_COMPLETE_NOT_RATIFIED",
        "generated_date": "2026-07-19",
        "opt_a_seal_hash": seal["seal_hash"],
        "reference_registry_hash": registry_manifest["combined_registry_hash"],
        "complete_replay_manifest_hash": replay_manifest["manifest_hash"],
        "relevance_review_manifest_hash": review_manifest["manifest_hash"],
        "v02_state_manifest_hash": v02_manifest["manifest_hash"],
        "relevance_policy_id": POLICY_ID,
        "state_contract_version": CONTRACT_VERSION,
        "semantic_findings": [
            "Parallel axes eliminate cross-axis evidence suppression.",
            "Topology-aware level relations reduce v0.3 genuine-conflict bars to zero in H1.",
            "Maintained accepted-level relations accumulate into ACCEPTED_CORRIDOR and saturate the location axis.",
            "B-STATE-0.3 is not recommended for ratification without a revised acceptance-relation lifecycle or non-categorical location representation.",
        ],
        "results": all_results,
        "artifacts": artifacts,
        "implementation_hashes": {
            "state_v03.py": sha256(ROOT / "src/ovc_opt_b/state_v03.py"),
            "run_parallel_axis_state_replay.py": sha256(Path(__file__).resolve()),
            "test_state_v03.py": sha256(ROOT / "tests/test_state_v03.py"),
        },
        "authority_boundary": "B-STATE-0.3 is historically replayed for semantic comparison only and is not ratified. No OPT-C outcome, edge, recommendation or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    manifest_path = output / "B_STATE_0_3_REPLAY_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "manifest_hash": manifest["manifest_hash"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
