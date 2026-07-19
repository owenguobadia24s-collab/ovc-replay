from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import hashlib
import json
from typing import Iterable, Mapping

from .review import response_contradiction_labels
from .stories import qualitative_story_features


VALIDATION_VERSION = "OPT-D-VALIDATE-0.1"


def _hash_ids(values: Iterable[object]) -> str:
    payload = sorted(str(value) for value in values)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _month(timestamp: object) -> str:
    return datetime.fromisoformat(str(timestamp)).strftime("%Y-%m")


def antecedent_key(value: Mapping[str, object]) -> tuple[str, tuple[str, ...], str]:
    """Return the frozen event-time-only antecedent key."""

    families = value.get("event_family_set", value.get("event_families"))
    if not isinstance(families, (list, tuple)):
        raise ValueError("antecedent event families must be a list or tuple")
    return (
        str(value["event_timeframe"]),
        tuple(sorted(str(item) for item in families)),
        str(value["event_direction"]),
    )


def response_vector(row: Mapping[str, object]) -> dict[str, object]:
    """Materialize the seven frozen qualitative response fields for one outcome."""

    story = qualitative_story_features(row, event_families=row["event_families"])
    return {
        "horizon_hours": story["horizon_hours"],
        "endpoint_alignment": story["endpoint_alignment"],
        "excursion_dominance": story["excursion_dominance"],
        "first_extreme": story["first_extreme"],
        "continuation_state": story["continuation_state"],
        "frontier_outcome": story["frontier_outcome"],
        "endpoint_range_location": story["endpoint_range_location"],
    }


def expected_response_vector(hypothesis: Mapping[str, object]) -> dict[str, object]:
    response = hypothesis["expected_forward_response"]
    return {
        key: response[key]
        for key in (
            "horizon_hours",
            "endpoint_alignment",
            "excursion_dominance",
            "first_extreme",
            "continuation_state",
            "frontier_outcome",
            "endpoint_range_location",
        )
    }


def _monthly_cluster_counts(
    rows: Iterable[Mapping[str, object]],
    *,
    cluster_by_outcome: Mapping[str, str],
    supplied_months: Iterable[str],
) -> dict[str, int]:
    clusters_by_month: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        clusters_by_month[_month(row["anchor_time"])].add(
            cluster_by_outcome[str(row["neutral_outcome_record_id"])]
        )
    return {
        month: len(clusters_by_month.get(month, set()))
        for month in supplied_months
    }


def evaluate_hypothesis(
    hypothesis: Mapping[str, object],
    *,
    outcome_rows: Iterable[Mapping[str, object]],
    cluster_by_outcome: Mapping[str, str],
    supplied_months: Iterable[str],
) -> dict[str, object]:
    """Evaluate one frozen hypothesis without tuning or row-level independence claims."""

    rules = hypothesis["untouched_validation_rules"]
    target_antecedent = antecedent_key(hypothesis["antecedent"])
    target_response = expected_response_vector(hypothesis)
    horizon = int(target_response["horizon_hours"])
    months = tuple(supplied_months)

    antecedent_rows: list[Mapping[str, object]] = []
    matching_rows: list[Mapping[str, object]] = []
    contradictory_rows: list[Mapping[str, object]] = []
    other_response_rows: list[Mapping[str, object]] = []
    contradiction_labels: dict[str, int] = defaultdict(int)

    for row in outcome_rows:
        if int(row["horizon_hours"]) != horizon:
            continue
        if antecedent_key(row) != target_antecedent:
            continue
        outcome_id = str(row["neutral_outcome_record_id"])
        if outcome_id not in cluster_by_outcome:
            raise ValueError(f"outcome lacks overlap-cluster assignment: {outcome_id}")
        antecedent_rows.append(row)
        actual_response = response_vector(row)
        if actual_response == target_response:
            matching_rows.append(row)
            continue
        labels = response_contradiction_labels(target_response, actual_response)
        if labels:
            contradictory_rows.append(row)
            for label in labels:
                contradiction_labels[label] += 1
        else:
            other_response_rows.append(row)

    def cluster_ids(rows: Iterable[Mapping[str, object]]) -> set[str]:
        return {
            cluster_by_outcome[str(row["neutral_outcome_record_id"])]
            for row in rows
        }

    antecedent_clusters = cluster_ids(antecedent_rows)
    matching_clusters = cluster_ids(matching_rows)
    contradictory_clusters = cluster_ids(contradictory_rows)
    other_response_clusters = cluster_ids(other_response_rows)
    antecedent_months = {_month(row["anchor_time"]) for row in antecedent_rows}
    matching_months = {_month(row["anchor_time"]) for row in matching_rows}
    contradictory_months = {_month(row["anchor_time"]) for row in contradictory_rows}

    evaluable = (
        len(antecedent_clusters) >= int(rules["minimum_evaluable_antecedent_clusters"])
        and len(antecedent_months) >= int(rules["minimum_evaluable_antecedent_months"])
    )
    reappeared = (
        evaluable
        and len(matching_clusters) >= int(rules["minimum_reappearance_matching_clusters"])
        and len(matching_months) >= int(rules["minimum_reappearance_matching_months"])
    )
    counter_alert = (
        evaluable and len(contradictory_clusters) >= len(matching_clusters)
    )

    if not evaluable:
        validation_status = str(rules["insufficient_status"])
        counter_story_status = "NOT_ASSESSED_INSUFFICIENT_ANTECEDENT_COVERAGE"
    else:
        validation_status = str(
            rules["reappeared_status"] if reappeared else rules["not_reappeared_status"]
        )
        counter_story_status = (
            str(rules["counter_story_alert"]) if counter_alert else "NO_COUNTER_STORY_ALERT"
        )

    return {
        "hypothesis_id": hypothesis["hypothesis_id"],
        "source_story_archetype_id": hypothesis["source_story_archetype_id"],
        "antecedent": hypothesis["antecedent"],
        "expected_forward_response": hypothesis["expected_forward_response"],
        "validation_status": validation_status,
        "counter_story_status": counter_story_status,
        "evaluable": evaluable,
        "structural_story_reappeared": reappeared,
        "counter_story_alert": counter_alert,
        "counts": {
            "antecedent_outcome_records": len(antecedent_rows),
            "matching_outcome_records": len(matching_rows),
            "contradictory_outcome_records": len(contradictory_rows),
            "other_response_outcome_records": len(other_response_rows),
            "distinct_antecedent_overlap_clusters": len(antecedent_clusters),
            "distinct_matching_overlap_clusters": len(matching_clusters),
            "distinct_contradictory_overlap_clusters": len(contradictory_clusters),
            "distinct_other_response_overlap_clusters": len(other_response_clusters),
            "matching_and_contradictory_cluster_overlap": len(
                matching_clusters.intersection(contradictory_clusters)
            ),
            "distinct_antecedent_months": len(antecedent_months),
            "distinct_matching_months": len(matching_months),
            "distinct_contradictory_months": len(contradictory_months),
        },
        "evidence_hashes": {
            "antecedent_outcome_record_ids_hash": _hash_ids(
                row["neutral_outcome_record_id"] for row in antecedent_rows
            ),
            "matching_outcome_record_ids_hash": _hash_ids(
                row["neutral_outcome_record_id"] for row in matching_rows
            ),
            "contradictory_outcome_record_ids_hash": _hash_ids(
                row["neutral_outcome_record_id"] for row in contradictory_rows
            ),
            "antecedent_overlap_cluster_ids_hash": _hash_ids(antecedent_clusters),
            "matching_overlap_cluster_ids_hash": _hash_ids(matching_clusters),
            "contradictory_overlap_cluster_ids_hash": _hash_ids(contradictory_clusters),
        },
        "monthly_distinct_cluster_counts": {
            "antecedent": _monthly_cluster_counts(
                antecedent_rows,
                cluster_by_outcome=cluster_by_outcome,
                supplied_months=months,
            ),
            "matching": _monthly_cluster_counts(
                matching_rows,
                cluster_by_outcome=cluster_by_outcome,
                supplied_months=months,
            ),
            "contradictory": _monthly_cluster_counts(
                contradictory_rows,
                cluster_by_outcome=cluster_by_outcome,
                supplied_months=months,
            ),
        },
        "contradiction_label_row_counts": dict(sorted(contradiction_labels.items())),
        "validation_contract_version": VALIDATION_VERSION,
        "outcome_authority": "STRUCTURAL_HOLDOUT_VALIDATION_ONLY",
        "probability_authority": "NONE",
        "edge_authority": "NONE",
        "execution_authority": "NONE",
    }
