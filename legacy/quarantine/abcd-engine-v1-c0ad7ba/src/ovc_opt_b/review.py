from __future__ import annotations

import hashlib
import json
from typing import Mapping


REVIEW_VERSION = "OPT-D-REVIEW-0.1"


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def review_disposition(repetition_status: str) -> tuple[str, str]:
    mapping = {
        "REPEATED_DESCRIPTIVE_SUPPORT": (
            "CANDIDATE_FOR_BATCH_PREREGISTRATION",
            "AT_LEAST_TEN_DISTINCT_OVERLAP_CLUSTERS",
        ),
        "REPEATED_LIMITED_SUPPORT": (
            "RETAIN_LIMITED_SUPPORT_INVENTORY",
            "THREE_TO_NINE_DISTINCT_OVERLAP_CLUSTERS",
        ),
        "REPEATED_MINIMAL_SUPPORT": (
            "RETAIN_MINIMAL_SUPPORT_INVENTORY",
            "TWO_DISTINCT_OVERLAP_CLUSTERS",
        ),
        "SINGLETON_INVENTORY": (
            "RETAIN_SINGLETON_INVENTORY",
            "ONE_DISTINCT_OVERLAP_CLUSTER",
        ),
    }
    if repetition_status not in mapping:
        raise ValueError(f"unknown repetition status: {repetition_status}")
    return mapping[repetition_status]


def story_antecedent(archetype: Mapping[str, object]) -> dict[str, object]:
    return {
        "event_timeframe": archetype["event_timeframe"],
        "event_family_set": list(archetype["event_family_set"]),
        "event_direction": archetype["event_direction"],
        "eligibility_time": "AFTER_EVENT_ANCHOR_CLOSE",
        "antecedent_contract": "FROZEN_EVENT_FIELDS_ONLY",
    }


def story_response(archetype: Mapping[str, object]) -> dict[str, object]:
    return {
        "horizon_hours": archetype["horizon_hours"],
        "endpoint_alignment": archetype["endpoint_alignment"],
        "excursion_dominance": archetype["excursion_dominance"],
        "first_extreme": archetype["first_extreme"],
        "continuation_state": archetype["continuation_state"],
        "frontier_outcome": archetype["frontier_outcome"],
        "endpoint_range_location": archetype["endpoint_range_location"],
        "matching_rule": "ALL_QUALITATIVE_RESPONSE_FIELDS_EXACT",
    }


def story_feature_key(archetype: Mapping[str, object]) -> str:
    return _hash({
        "antecedent": story_antecedent(archetype),
        "response": story_response(archetype),
        "review_contract_version": REVIEW_VERSION,
    })


def mirror_story_features(archetype: Mapping[str, object]) -> dict[str, object]:
    direction = {"UP": "DOWN", "DOWN": "UP"}.get(str(archetype["event_direction"]))
    if direction is None:
        raise ValueError("directional mirror requires UP or DOWN")
    first_extreme = {"UP_FIRST": "DOWN_FIRST", "DOWN_FIRST": "UP_FIRST"}.get(
        str(archetype["first_extreme"]), archetype["first_extreme"]
    )
    range_location = {
        "UPPER_THIRD": "LOWER_THIRD",
        "LOWER_THIRD": "UPPER_THIRD",
        "MIDDLE_THIRD": "MIDDLE_THIRD",
        "ZERO_RANGE": "ZERO_RANGE",
    }.get(str(archetype["endpoint_range_location"]), archetype["endpoint_range_location"])
    return {
        "event_timeframe": archetype["event_timeframe"],
        "event_family_set": list(archetype["event_family_set"]),
        "event_direction": direction,
        "horizon_hours": archetype["horizon_hours"],
        "endpoint_alignment": archetype["endpoint_alignment"],
        "excursion_dominance": archetype["excursion_dominance"],
        "first_extreme": first_extreme,
        "continuation_state": archetype["continuation_state"],
        "frontier_outcome": archetype["frontier_outcome"],
        "endpoint_range_location": range_location,
    }


def mirror_story_key(archetype: Mapping[str, object]) -> str:
    return story_feature_key(mirror_story_features(archetype))


def response_contradiction_labels(
    target: Mapping[str, object],
    other: Mapping[str, object],
) -> list[str]:
    labels = []
    directional_alignment = {"ALIGNED", "OPPOSITE"}
    if (
        target["endpoint_alignment"] in directional_alignment
        and other["endpoint_alignment"] in directional_alignment
        and target["endpoint_alignment"] != other["endpoint_alignment"]
    ):
        labels.append("OPPOSITE_ENDPOINT_ALIGNMENT")

    def frontier_polarity(value: object) -> str:
        text = str(value)
        if text.startswith("LOST_"):
            return "LOST"
        if text.endswith("_HELD"):
            return "HELD"
        return "OTHER"

    target_frontier = frontier_polarity(target["frontier_outcome"])
    other_frontier = frontier_polarity(other["frontier_outcome"])
    if {target_frontier, other_frontier} == {"LOST", "HELD"}:
        labels.append("OPPOSITE_FRONTIER_POLARITY")
    return labels


def frozen_holdout_rules() -> dict[str, object]:
    return {
        "input_authority": "NEW_SEALED_NON_OVERLAPPING_OPT_A_RELEASE",
        "definition_authority": "OPT_D_STORY_0_1_AND_OPT_D_REVIEW_0_1_FROZEN",
        "minimum_evaluable_antecedent_clusters": 10,
        "minimum_evaluable_antecedent_months": 4,
        "minimum_reappearance_matching_clusters": 10,
        "minimum_reappearance_matching_months": 4,
        "eligible_status": "EVALUABLE",
        "insufficient_status": "NOT_EVALUABLE_INSUFFICIENT_ANTECEDENT_COVERAGE",
        "reappeared_status": "STRUCTURAL_STORY_REAPPEARED",
        "not_reappeared_status": "STRUCTURAL_STORY_NOT_REAPPEARED",
        "definition_drift_status": "INVALID_DEFINITION_OR_LINEAGE_DRIFT",
        "counter_story_definition": "SAME_ANTECEDENT_AND_HORIZON_WITH_OPPOSITE_ENDPOINT_ALIGNMENT_OR_FRONTIER_POLARITY",
        "counter_story_alert": "CONTRADICTORY_RESPONSE_CLUSTERS_GREATER_THAN_OR_EQUAL_TO_MATCHING_CLUSTERS",
        "monthly_reporting": "ALL_SUPPLIED_MONTHS_WITH_ZERO_SUPPORT_MONTHS_EXPLICIT",
        "cluster_counting": "DISTINCT_OVERLAP_CLUSTERS_ONLY",
        "threshold_optimization": "PROHIBITED_DURING_HOLDOUT",
    }
