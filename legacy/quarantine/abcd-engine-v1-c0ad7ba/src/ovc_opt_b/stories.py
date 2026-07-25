from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
import hashlib
import json
from typing import Iterable, Mapping

from .contrasts import median_decimal


STORY_VERSION = "OPT-D-STORY-0.1"


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def qualitative_story_features(
    row: Mapping[str, object],
    *,
    event_families: Iterable[str],
) -> dict[str, object]:
    measurements = row["measurements"]
    normalized = measurements["direction_normalized_endpoint_return_pips"]
    favorable = measurements["direction_normalized_favorable_excursion_pips"]
    adverse = measurements["direction_normalized_adverse_excursion_pips"]
    if normalized is None:
        endpoint_alignment = "NOT_DIRECTIONAL"
    elif Decimal(str(normalized)) > 0:
        endpoint_alignment = "ALIGNED"
    elif Decimal(str(normalized)) < 0:
        endpoint_alignment = "OPPOSITE"
    else:
        endpoint_alignment = "FLAT"
    if favorable is None or adverse is None:
        excursion_dominance = "NOT_DIRECTIONAL"
    elif Decimal(str(favorable)) > Decimal(str(adverse)):
        excursion_dominance = "FAVORABLE_DOMINANT"
    elif Decimal(str(favorable)) < Decimal(str(adverse)):
        excursion_dominance = "ADVERSE_DOMINANT"
    else:
        excursion_dominance = "BALANCED"
    continuation = measurements["continued_beyond_event_extreme"]
    continuation_state = (
        "NOT_DIRECTIONAL" if continuation is None else "CONTINUED" if continuation else "NOT_CONTINUED"
    )
    primary_frontier = measurements["primary_frontier_type"]
    if primary_frontier is None:
        frontier_outcome = "NO_PRIMARY_FRONTIER"
    elif measurements["primary_frontier_lost_on_close"]:
        frontier_outcome = (
            "LOST_AFTER_RETEST"
            if measurements["primary_frontier_retested"]
            else "LOST_WITHOUT_RECORDED_RETEST"
        )
    elif measurements["primary_frontier_held_at_endpoint"]:
        frontier_outcome = (
            "RETESTED_AND_HELD"
            if measurements["primary_frontier_retested"]
            else "NOT_RETESTED_AND_HELD"
        )
    else:
        frontier_outcome = "UNRESOLVED_PRIMARY_FRONTIER"
    position = measurements["endpoint_close_position_in_forward_range"]
    if position is None:
        endpoint_range_location = "ZERO_RANGE"
    elif Decimal(str(position)) <= Decimal("0.3333333333333333333333333333"):
        endpoint_range_location = "LOWER_THIRD"
    elif Decimal(str(position)) >= Decimal("0.6666666666666666666666666667"):
        endpoint_range_location = "UPPER_THIRD"
    else:
        endpoint_range_location = "MIDDLE_THIRD"
    vector = {
        "event_family_set": sorted(set(event_families)),
        "event_timeframe": row["event_timeframe"],
        "horizon_hours": row["horizon_hours"],
        "event_direction": row["event_direction"],
        "endpoint_alignment": endpoint_alignment,
        "excursion_dominance": excursion_dominance,
        "first_extreme": measurements["first_extreme"],
        "continuation_state": continuation_state,
        "frontier_outcome": frontier_outcome,
        "endpoint_range_location": endpoint_range_location,
        "story_contract_version": STORY_VERSION,
    }
    return {**vector, "story_archetype_id": f"opt-d-story:{_hash(vector)}"}


def quantile_decimal(values: list[Decimal], fraction: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * Decimal(len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - Decimal(lower)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def canonical_cluster_representatives(
    rows: Iterable[Mapping[str, object]],
    *,
    cluster_by_outcome: Mapping[str, str],
    metric_field: str,
) -> list[Mapping[str, object]]:
    by_cluster: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        if row["measurements"][metric_field] is not None:
            by_cluster[cluster_by_outcome[str(row["neutral_outcome_record_id"])]].append(row)
    representatives = []
    for cluster_id, members in sorted(by_cluster.items()):
        values = [Decimal(str(row["measurements"][metric_field])) for row in members]
        center = median_decimal(values)
        representatives.append(min(
            members,
            key=lambda row: (
                abs(Decimal(str(row["measurements"][metric_field])) - center),
                str(row["neutral_outcome_record_id"]),
            ),
        ))
    return representatives


def select_representative_cases(
    rows: Iterable[Mapping[str, object]],
    *,
    cluster_by_outcome: Mapping[str, str],
    metric_field: str,
) -> list[dict[str, object]]:
    rows = list(rows)
    representatives = canonical_cluster_representatives(
        rows, cluster_by_outcome=cluster_by_outcome, metric_field=metric_field
    )
    values = [Decimal(str(row["measurements"][metric_field])) for row in representatives]
    roles = (
        ("CENTRAL", Decimal("0.50")),
        ("LOWER_TAIL", Decimal("0.10")),
        ("UPPER_TAIL", Decimal("0.90")),
    )
    selected: list[dict[str, object]] = []
    used_clusters: set[str] = set()
    for role, fraction in roles:
        target = quantile_decimal(values, fraction)
        if target is None:
            continue
        candidates = sorted(
            representatives,
            key=lambda row: (
                cluster_by_outcome[str(row["neutral_outcome_record_id"])] in used_clusters,
                abs(Decimal(str(row["measurements"][metric_field])) - target),
                str(row["neutral_outcome_record_id"]),
            ),
        )
        chosen = candidates[0]
        cluster_id = cluster_by_outcome[str(chosen["neutral_outcome_record_id"])]
        used_clusters.add(cluster_id)
        selected.append({
            "case_role": role,
            "neutral_outcome_record_id": chosen["neutral_outcome_record_id"],
            "event_anchor_id": chosen["event_anchor_id"],
            "overlap_cluster_id": cluster_id,
            "metric_field": metric_field,
            "metric_value_pips": chosen["measurements"][metric_field],
            "target_quantile_value_pips": str(target),
        })

    counterexample_filters = (
        (
            "OPPOSITE_DIRECTION_COUNTEREXAMPLE",
            lambda row: row["measurements"]["direction_normalized_endpoint_return_pips"] is not None
            and Decimal(str(row["measurements"]["direction_normalized_endpoint_return_pips"])) < 0,
        ),
        (
            "PRIMARY_FRONTIER_LOSS_CASE",
            lambda row: row["measurements"]["primary_frontier_lost_on_close"] is True,
        ),
    )
    for role, predicate in counterexample_filters:
        filtered = [row for row in rows if predicate(row)]
        candidates = canonical_cluster_representatives(
            filtered, cluster_by_outcome=cluster_by_outcome, metric_field=metric_field
        )
        if not candidates:
            continue
        center = median_decimal([Decimal(str(row["measurements"][metric_field])) for row in candidates])
        chosen = min(
            candidates,
            key=lambda row: (
                abs(Decimal(str(row["measurements"][metric_field])) - center),
                str(row["neutral_outcome_record_id"]),
            ),
        )
        selected.append({
            "case_role": role,
            "neutral_outcome_record_id": chosen["neutral_outcome_record_id"],
            "event_anchor_id": chosen["event_anchor_id"],
            "overlap_cluster_id": cluster_by_outcome[str(chosen["neutral_outcome_record_id"])],
            "metric_field": metric_field,
            "metric_value_pips": chosen["measurements"][metric_field],
            "target_quantile_value_pips": str(center),
        })
    return selected
