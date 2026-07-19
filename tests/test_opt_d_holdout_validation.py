from __future__ import annotations

import unittest

from ovc_opt_b import evaluate_hypothesis


MONTHS = tuple(f"2025-{month:02d}" for month in range(1, 13))


def hypothesis() -> dict[str, object]:
    return {
        "hypothesis_id": "hypothesis:1",
        "source_story_archetype_id": "story:1",
        "antecedent": {
            "event_timeframe": "15M",
            "event_family_set": ["INTERACTION"],
            "event_direction": "UP",
            "eligibility_time": "AFTER_EVENT_ANCHOR_CLOSE",
            "antecedent_contract": "FROZEN_EVENT_FIELDS_ONLY",
        },
        "expected_forward_response": {
            "horizon_hours": 1,
            "endpoint_alignment": "ALIGNED",
            "excursion_dominance": "FAVORABLE_DOMINANT",
            "first_extreme": "UP_FIRST",
            "continuation_state": "CONTINUED",
            "frontier_outcome": "NO_PRIMARY_FRONTIER",
            "endpoint_range_location": "UPPER_THIRD",
            "matching_rule": "ALL_QUALITATIVE_RESPONSE_FIELDS_EXACT",
        },
        "untouched_validation_rules": {
            "minimum_evaluable_antecedent_clusters": 10,
            "minimum_evaluable_antecedent_months": 4,
            "minimum_reappearance_matching_clusters": 10,
            "minimum_reappearance_matching_months": 4,
            "reappeared_status": "STRUCTURAL_STORY_REAPPEARED",
            "not_reappeared_status": "STRUCTURAL_STORY_NOT_REAPPEARED",
            "insufficient_status": "NOT_EVALUABLE_INSUFFICIENT_ANTECEDENT_COVERAGE",
            "counter_story_alert": "CONTRADICTORY_RESPONSE_CLUSTERS_GREATER_THAN_OR_EQUAL_TO_MATCHING_CLUSTERS",
        },
    }


def outcome(index: int, *, aligned: bool = True, month: int | None = None) -> dict[str, object]:
    month = month or (index % 4) + 1
    raw = "1" if aligned else "-1"
    return {
        "neutral_outcome_record_id": f"outcome:{index}",
        "anchor_time": f"2025-{month:02d}-01T00:00:00+00:00",
        "event_timeframe": "15M",
        "event_families": ["INTERACTION"],
        "event_direction": "UP",
        "horizon_hours": 1,
        "measurements": {
            "direction_normalized_endpoint_return_pips": raw,
            "direction_normalized_favorable_excursion_pips": "2",
            "direction_normalized_adverse_excursion_pips": "1",
            "continued_beyond_event_extreme": True,
            "primary_frontier_type": None,
            "primary_frontier_lost_on_close": None,
            "primary_frontier_retested": None,
            "primary_frontier_held_at_endpoint": None,
            "endpoint_close_position_in_forward_range": "0.8",
            "first_extreme": "UP_FIRST",
        },
    }


class OptDHoldoutValidationTests(unittest.TestCase):
    def test_exact_story_reappears_at_frozen_threshold(self) -> None:
        rows = [outcome(index) for index in range(10)]
        result = evaluate_hypothesis(
            hypothesis(),
            outcome_rows=rows,
            cluster_by_outcome={row["neutral_outcome_record_id"]: f"cluster:{index}" for index, row in enumerate(rows)},
            supplied_months=MONTHS,
        )
        self.assertEqual(result["validation_status"], "STRUCTURAL_STORY_REAPPEARED")
        self.assertTrue(result["evaluable"])
        self.assertFalse(result["counter_story_alert"])
        self.assertEqual(result["monthly_distinct_cluster_counts"]["matching"]["2025-12"], 0)

    def test_rows_do_not_substitute_for_distinct_clusters(self) -> None:
        rows = [outcome(index) for index in range(20)]
        result = evaluate_hypothesis(
            hypothesis(),
            outcome_rows=rows,
            cluster_by_outcome={row["neutral_outcome_record_id"]: "cluster:one" for row in rows},
            supplied_months=MONTHS,
        )
        self.assertEqual(
            result["validation_status"],
            "NOT_EVALUABLE_INSUFFICIENT_ANTECEDENT_COVERAGE",
        )

    def test_counter_story_alert_uses_frozen_cluster_comparison(self) -> None:
        rows = [outcome(index, aligned=index < 5) for index in range(10)]
        result = evaluate_hypothesis(
            hypothesis(),
            outcome_rows=rows,
            cluster_by_outcome={row["neutral_outcome_record_id"]: f"cluster:{index}" for index, row in enumerate(rows)},
            supplied_months=MONTHS,
        )
        self.assertTrue(result["evaluable"])
        self.assertFalse(result["structural_story_reappeared"])
        self.assertTrue(result["counter_story_alert"])
        self.assertEqual(
            result["contradiction_label_row_counts"],
            {"OPPOSITE_ENDPOINT_ALIGNMENT": 5},
        )


if __name__ == "__main__":
    unittest.main()
