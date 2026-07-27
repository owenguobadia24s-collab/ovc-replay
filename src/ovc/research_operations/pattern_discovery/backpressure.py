from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Iterable, Mapping


PRIORITY = {
    "QUALITY_OR_INCIDENT": 0,
    "CROSS_SCALE_CONFLICT": 1,
    "STRUCTURAL_TRANSITION": 2,
    "PERSISTENCE_OR_INSTABILITY": 3,
    "RECURRENCE": 4,
    "CONTROL": 5,
    "NOVELTY": 6,
}


@dataclass(frozen=True)
class QueuePolicy:
    max_promotions_per_instrument_day: int = 12
    max_promotions_per_family_day: int = 3
    max_unresolved_depth: int = 50
    minimum_control_share: float = 0.20


@dataclass(frozen=True)
class LatencyObservation:
    index_seconds: float
    trigger_seconds: float
    queue_seconds: float
    consecutive_index_late_cycles: int = 0


def degradation_states(observation: LatencyObservation) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    if observation.index_seconds > 5:
        states.append({
            "state": "DEGRADED_INDEX_LATENCY",
            "actual_seconds": observation.index_seconds,
            "objective_seconds": 5,
            "candidate_creation_paused": observation.consecutive_index_late_cycles >= 3,
        })
    if observation.trigger_seconds > 10:
        states.append({
            "state": "DEGRADED_TRIGGER_LATENCY",
            "actual_seconds": observation.trigger_seconds,
            "objective_seconds": 10,
            "new_window_opening_permitted": False,
        })
    if observation.queue_seconds > 15:
        states.append({
            "state": "STALE_QUEUE_PROJECTION",
            "actual_seconds": observation.queue_seconds,
            "objective_seconds": 15,
            "current_window_review_permitted": False,
        })
    return states


def _candidate_order(candidate: Mapping[str, Any]) -> tuple[int, str, str, str]:
    family = str(candidate.get("trigger_family") or "CONTROL")
    return (
        PRIORITY.get(family, len(PRIORITY)),
        str(candidate.get("trigger_first_valid_at") or candidate.get("first_valid_at") or ""),
        family,
        str(candidate.get("window_id") or candidate.get("candidate_id") or ""),
    )


def project_review_queue(
    candidates: Iterable[Mapping[str, Any]],
    *,
    unresolved_queue_depth: int,
    policy: QueuePolicy = QueuePolicy(),
) -> dict[str, Any]:
    if unresolved_queue_depth < 0:
        raise ValueError("queue depth cannot be negative")
    available_depth = max(policy.max_unresolved_depth - unresolved_queue_depth, 0)
    daily_slots = min(policy.max_promotions_per_instrument_day, available_depth)
    ordered = sorted((dict(item) for item in candidates), key=_candidate_order)

    incident_items = [item for item in ordered if item.get("trigger_family") == "QUALITY_OR_INCIDENT"]
    ordinary_items = [item for item in ordered if item.get("trigger_family") != "QUALITY_OR_INCIDENT"]
    controls = [item for item in ordinary_items if item.get("control_class") in {"MATCHED_CONTROL", "POPULATION_CONTROL"}]
    non_controls = [item for item in ordinary_items if item.get("control_class") not in {"MATCHED_CONTROL", "POPULATION_CONTROL"}]

    promoted: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    family_counts: dict[str, int] = {}

    def add(item: dict[str, Any], *, bypass_family_cap: bool = False) -> bool:
        if len(promoted) >= daily_slots:
            return False
        family = str(item.get("trigger_family") or "CONTROL")
        if not bypass_family_cap and family_counts.get(family, 0) >= policy.max_promotions_per_family_day:
            return False
        promoted.append(item)
        family_counts[family] = family_counts.get(family, 0) + 1
        return True

    for item in incident_items:
        if not add(item, bypass_family_cap=True):
            failed = dict(item)
            failed["suppression_reason"] = "SUPPRESSED_QUEUE_DEPTH" if available_depth == 0 else "SUPPRESSED_DAILY_PROMOTION_CAP"
            suppressed.append(failed)

    control_slots = ceil(daily_slots * policy.minimum_control_share) if controls else 0
    matched_needed = ceil(control_slots * 0.50)
    population_needed = ceil(control_slots * 0.25)
    matched = [item for item in controls if item.get("control_class") == "MATCHED_CONTROL"]
    population = [item for item in controls if item.get("control_class") == "POPULATION_CONTROL"]
    other_controls = [item for item in controls if item not in matched and item not in population]
    reserved = matched[:matched_needed] + population[:population_needed]
    seen_ids = {str(item.get("window_id") or item.get("candidate_id")) for item in reserved}
    reserved += [item for item in matched[matched_needed:] + population[population_needed:] + other_controls if str(item.get("window_id") or item.get("candidate_id")) not in seen_ids][: max(control_slots - len(reserved), 0)]

    for item in reserved:
        if not add(item):
            failed = dict(item)
            failed["suppression_reason"] = "SUPPRESSED_CONTROL_RESERVATION_CAP"
            suppressed.append(failed)

    for item in non_controls + [item for item in controls if item not in reserved]:
        family = str(item.get("trigger_family") or "CONTROL")
        if add(item):
            continue
        failed = dict(item)
        if len(promoted) >= daily_slots:
            failed["suppression_reason"] = "SUPPRESSED_QUEUE_DEPTH" if available_depth == 0 else "SUPPRESSED_DAILY_PROMOTION_CAP"
        elif family_counts.get(family, 0) >= policy.max_promotions_per_family_day:
            failed["suppression_reason"] = "SUPPRESSED_FAMILY_PROMOTION_CAP"
        else:
            failed["suppression_reason"] = "SUPPRESSED_QUEUE_POLICY"
        suppressed.append(failed)

    promoted = sorted(promoted, key=_candidate_order)
    suppressed = sorted(suppressed, key=_candidate_order)
    return {
        "promoted": promoted,
        "suppressed": suppressed,
        "metrics": {
            "input_candidates": len(ordered),
            "promoted_count": len(promoted),
            "suppressed_count": len(suppressed),
            "daily_slots": daily_slots,
            "unresolved_queue_depth_before": unresolved_queue_depth,
            "unresolved_queue_depth_after": unresolved_queue_depth + len(promoted),
            "family_counts": family_counts,
            "control_promotions": sum(1 for item in promoted if item.get("control_class") in {"MATCHED_CONTROL", "POPULATION_CONTROL"}),
            "control_slots_requested": control_slots,
        },
    }
