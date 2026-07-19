from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Iterable, Mapping


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_overlap_clusters(rows: Iterable[Mapping[str, object]]) -> tuple[list[dict[str, object]], dict[str, str]]:
    ordered = sorted(
        rows,
        key=lambda row: (row["anchor_time"], row["event_timeframe"], row["neutral_outcome_record_id"]),
    )
    if not ordered:
        return [], {}
    horizons = {int(row["horizon_hours"]) for row in ordered}
    if len(horizons) != 1:
        raise ValueError("overlap clusters must be constructed one horizon at a time")
    horizon = next(iter(horizons))
    grouped: list[list[Mapping[str, object]]] = []
    current: list[Mapping[str, object]] = []
    current_end: datetime | None = None
    for row in ordered:
        start = datetime.fromisoformat(str(row["anchor_time"]))
        end = datetime.fromisoformat(str(row["endpoint_time"]))
        if end <= start:
            raise ValueError("outcome interval endpoint must follow anchor")
        if current_end is None or start >= current_end:
            if current:
                grouped.append(current)
            current = [row]
            current_end = end
        else:
            current.append(row)
            current_end = max(current_end, end)
    if current:
        grouped.append(current)

    clusters = []
    assignment = {}
    for members in grouped:
        ids = [str(row["neutral_outcome_record_id"]) for row in members]
        start = min(str(row["anchor_time"]) for row in members)
        end = max(str(row["endpoint_time"]) for row in members)
        core = {
            "horizon_hours": horizon,
            "cluster_start_time": start,
            "cluster_end_time": end,
            "ordered_outcome_record_ids_hash": _hash(ids),
        }
        cluster_id = f"opt-d-cluster:{_hash(core)}"
        for record_id in ids:
            if record_id in assignment:
                raise ValueError("outcome assigned to more than one overlap cluster")
            assignment[record_id] = cluster_id
        clusters.append({
            **core,
            "overlap_cluster_id": cluster_id,
            "outcome_records": len(members),
            "unique_event_anchors": len({row["event_anchor_id"] for row in members}),
            "event_timeframe_counts": dict(sorted(_counts(str(row["event_timeframe"]) for row in members).items())),
        })
    return clusters, assignment


def _counts(values: Iterable[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return result


def descriptive_band(count: int) -> str:
    if count < 0:
        raise ValueError("support cannot be negative")
    if count == 0:
        return "EMPTY"
    if count < 30:
        return "SPARSE"
    if count < 100:
        return "LIMITED"
    return "ADEQUATE"


def cohort_readiness(row_count: int, cluster_count: int, distinct_months: int) -> str:
    if row_count == 0:
        return "EMPTY"
    if row_count < 30:
        return "INVENTORY_ONLY_ROW_SPARSE"
    if cluster_count < 30:
        return "INVENTORY_ONLY_CLUSTER_SPARSE"
    if distinct_months < 3:
        return "INVENTORY_ONLY_TEMPORALLY_NARROW"
    if row_count < 100 or cluster_count < 100:
        return "LIMITED_CLUSTERED_DESCRIPTION"
    return "DESCRIPTIVE_COHORT_READY"


def semantic_event_signature(anchor: Mapping[str, object]) -> dict[str, object]:
    components = sorted({
        (
            str(component["family"]),
            str(component["subtype"]),
            str(component["direction"]),
        )
        for component in anchor["event_components"]
    })
    payload = [
        {"family": family, "subtype": subtype, "direction": direction}
        for family, subtype, direction in components
    ]
    return {
        "semantic_components": payload,
        "semantic_component_count": len(payload),
        "semantic_signature_hash": _hash(payload),
    }
