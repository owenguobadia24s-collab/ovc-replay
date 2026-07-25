from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable, Mapping


def median_decimal(values: Iterable[Decimal]) -> Decimal | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def cluster_balanced_metric(
    rows: Iterable[Mapping[str, object]],
    *,
    cluster_by_outcome: Mapping[str, str],
    metric_field: str,
) -> dict[str, object]:
    by_cluster: dict[str, list[Decimal]] = defaultdict(list)
    row_count = 0
    for row in rows:
        value = row["measurements"][metric_field]
        if value is None:
            continue
        record_id = str(row["neutral_outcome_record_id"])
        by_cluster[cluster_by_outcome[record_id]].append(Decimal(str(value)))
        row_count += 1
    cluster_medians = {
        cluster_id: median_decimal(values) for cluster_id, values in sorted(by_cluster.items())
    }
    values = [value for value in cluster_medians.values() if value is not None]
    return {
        "metric_field": metric_field,
        "measured_rows": row_count,
        "measured_clusters": len(values),
        "cluster_balanced_median": str(median_decimal(values)) if values else None,
        "cluster_medians": {key: str(value) for key, value in cluster_medians.items() if value is not None},
    }


def exclusive_arms(
    arm_a: Iterable[Mapping[str, object]],
    arm_b: Iterable[Mapping[str, object]],
) -> tuple[list[Mapping[str, object]], list[Mapping[str, object]], list[str]]:
    a = {str(row["neutral_outcome_record_id"]): row for row in arm_a}
    b = {str(row["neutral_outcome_record_id"]): row for row in arm_b}
    shared = sorted(set(a).intersection(b))
    return (
        [a[key] for key in sorted(set(a) - set(shared))],
        [b[key] for key in sorted(set(b) - set(shared))],
        shared,
    )


def contrast_readiness(
    arm_a_rows: int,
    arm_a_clusters: int,
    arm_a_months: int,
    arm_b_rows: int,
    arm_b_clusters: int,
    arm_b_months: int,
) -> str:
    if min(arm_a_rows, arm_b_rows, arm_a_clusters, arm_b_clusters) < 30:
        return "INVENTORY_ONLY_AFTER_EXCLUSIVITY"
    if min(arm_a_months, arm_b_months) < 3:
        return "INVENTORY_ONLY_TEMPORALLY_NARROW"
    if min(arm_a_rows, arm_b_rows, arm_a_clusters, arm_b_clusters) < 100:
        return "LIMITED_CLUSTERED_CONTRAST"
    return "DESCRIPTIVE_CONTRAST_READY"


def temporal_delta_status(monthly_deltas: Iterable[Decimal]) -> dict[str, object]:
    values = list(monthly_deltas)
    positive = sum(value > 0 for value in values)
    negative = sum(value < 0 for value in values)
    zero = sum(value == 0 for value in values)
    if len(values) < 3:
        status = "INSUFFICIENT_MONTHLY_SUPPORT"
    elif max(positive, negative) * 100 >= 80 * len(values):
        status = "DELTA_SIGN_CONSISTENT_80PCT"
    else:
        status = "DELTA_SIGN_MIXED"
    return {
        "eligible_months": len(values),
        "positive_delta_months": positive,
        "negative_delta_months": negative,
        "zero_delta_months": zero,
        "temporal_delta_status": status,
    }
