from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256

from .models import AXES, PatternDiscoveryError


FINGERPRINT_VERSION = "PD.FINGERPRINT.v0.1"
PROHIBITED_KEYS = {
    "return",
    "returns",
    "mfe",
    "mae",
    "future_outcome",
    "outcome",
    "probability",
    "profitable_direction",
    "trade_direction",
    "setup",
    "execution",
    "archetype",
}


def _find_prohibited(value: Any, *, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text in PROHIBITED_KEYS:
                found.append(child_path)
            found.extend(_find_prohibited(child, path=child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found.extend(_find_prohibited(child, path=f"{path}[{index}]"))
    return found


def _axis_value(state: Mapping[str, Any], axis: str) -> str:
    axes = state.get("axes", state)
    payload = axes.get(axis) if isinstance(axes, Mapping) else None
    if isinstance(payload, Mapping):
        status = str(payload.get("status") or "UNKNOWN")
        value = payload.get("value")
        reason = payload.get("reason_code")
        return "|".join([status, "NULL" if value is None else str(value), "" if reason is None else str(reason)])
    if payload is None:
        return "NOT_EVALUABLE|NULL|MISSING_AXIS"
    return f"EVALUATED|{payload}|"


def _occupancy(state_sequence: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    total = len(state_sequence)
    for axis in AXES:
        counts = Counter(_axis_value(state, axis) for state in state_sequence)
        result[axis] = {
            key: 0.0 if total == 0 else round(count / total, 12)
            for key, count in sorted(counts.items())
        }
    return result


def _persistence_lengths(state_sequence: Sequence[Mapping[str, Any]]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for axis in AXES:
        values = [_axis_value(state, axis) for state in state_sequence]
        runs: list[int] = []
        if values:
            current = values[0]
            length = 1
            for value in values[1:]:
                if value == current:
                    length += 1
                else:
                    runs.append(length)
                    current = value
                    length = 1
            runs.append(length)
        result[axis] = runs
    return result


def build_pattern_fingerprint(
    candidate: Mapping[str, Any],
    *,
    state_sequence: Sequence[Mapping[str, Any]],
    transition_sequence: Sequence[str],
    interaction_events: Iterable[str],
    cross_scale_context: Mapping[str, Any],
    fingerprint_version: str = FINGERPRINT_VERSION,
) -> dict[str, Any]:
    prohibited = _find_prohibited(candidate) + _find_prohibited(state_sequence) + _find_prohibited(cross_scale_context)
    if prohibited:
        raise PatternDiscoveryError(f"prohibited fingerprint inputs: {sorted(set(prohibited))}")
    if candidate.get("status") not in {"READY_FOR_REVIEW", "DISMISSED", "SUPPRESSED_QUEUE_CAP", "REVIEWED"}:
        raise PatternDiscoveryError("fingerprint requires a valid deterministically closed candidate")
    if not state_sequence:
        raise PatternDiscoveryError("fingerprint requires a non-empty state sequence")
    required_partition = [
        "clock",
        "price_side",
        "primary_transition_grammar",
        "boundary_interaction_class",
        "parent_containment_class",
        "closure_class",
    ]
    missing = [field for field in required_partition if not candidate.get(field)]
    if missing:
        raise PatternDiscoveryError(f"missing fingerprint partition fields: {missing}")
    if candidate.get("source_lineage_status") not in {None, "RESOLVED"}:
        raise PatternDiscoveryError("unresolved source lineage is not fingerprint-eligible")

    transition_values = [str(item) for item in transition_sequence]
    interaction_values = sorted(set(str(item) for item in interaction_events))
    persistence = _persistence_lengths(state_sequence)
    duration_records = int(candidate.get("duration_records") or len(state_sequence))
    switches = sum(1 for before, after in zip(transition_values, transition_values[1:]) if before != after)
    quality_values = [_axis_value(state, "QUALITY") for state in state_sequence]
    not_evaluable_count = sum(1 for value in quality_values if value.startswith("NOT_EVALUABLE"))
    conflict_count = sum(1 for value in quality_values if "CONFLICT" in value)
    stale_count = sum(1 for value in quality_values if "STALE" in value)

    partition = {
        "clock": str(candidate["clock"]),
        "price_side": str(candidate["price_side"]),
        "primary_transition_grammar": str(candidate["primary_transition_grammar"]),
        "boundary_interaction_class": str(candidate["boundary_interaction_class"]),
        "parent_containment_class": str(candidate["parent_containment_class"]),
        "closure_class": str(candidate["closure_class"]),
    }
    payload = {
        "record_type": "PatternFingerprint",
        "fingerprint_version": fingerprint_version,
        "candidate_window_id": str(candidate.get("window_id") or candidate.get("candidate_id")),
        "source_release_id": str(candidate.get("source_release_id")),
        "source_manifest_id": str(candidate.get("source_manifest_id")),
        "window_start_utc": str(candidate.get("window_start_utc")),
        "window_end_utc": str(candidate.get("window_end_utc")),
        "scope_id": str(candidate.get("scope_id")),
        "partition": partition,
        "state_path": {
            "initial": {axis: _axis_value(state_sequence[0], axis) for axis in AXES},
            "terminal": {axis: _axis_value(state_sequence[-1], axis) for axis in AXES},
            "occupancy": _occupancy(state_sequence),
            "persistence_lengths": persistence,
        },
        "transition_sequence": transition_values,
        "interaction_events": interaction_values,
        "cross_scale": dict(sorted((str(key), value) for key, value in cross_scale_context.items())),
        "duration_persistence": {
            "duration_records": duration_records,
            "transition_count": len(transition_values),
            "switch_count": switches,
            "max_persistence": max((max(values) if values else 0) for values in persistence.values()),
        },
        "quality": {
            "not_evaluable_fraction": round(not_evaluable_count / len(quality_values), 12),
            "conflict_fraction": round(conflict_count / len(quality_values), 12),
            "stale_fraction": round(stale_count / len(quality_values), 12),
            "closure_reason": str(candidate.get("closure_reason")),
            "censored": str(candidate.get("closure_reason", "")).startswith("CENSORED"),
        },
        "selection": {
            "trigger_event_ids": sorted(str(item) for item in candidate.get("trigger_event_ids", ())),
            "control_class": str(candidate.get("control_class") or "NONE"),
            "disposition": str(candidate.get("disposition") or "UNREVIEWED"),
        },
    }
    fingerprint_id = f"PDFP-{canonical_sha256(payload)[:32]}"
    return {"fingerprint_id": fingerprint_id, **payload}


def partition_key(fingerprint: Mapping[str, Any]) -> tuple[str, ...]:
    partition = fingerprint.get("partition")
    if not isinstance(partition, Mapping):
        raise PatternDiscoveryError("fingerprint partition is missing")
    fields = (
        "clock",
        "price_side",
        "primary_transition_grammar",
        "boundary_interaction_class",
        "parent_containment_class",
        "closure_class",
    )
    values = tuple(str(partition.get(field) or "") for field in fields)
    if any(not value for value in values):
        raise PatternDiscoveryError("fingerprint partition is incomplete")
    return values
