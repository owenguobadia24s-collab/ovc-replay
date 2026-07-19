from __future__ import annotations

import unittest

from ovc_opt_b import (
    frozen_holdout_rules,
    mirror_story_features,
    response_contradiction_labels,
    review_disposition,
    story_antecedent,
    story_response,
)


def archetype(*, alignment: str = "ALIGNED", status: str = "REPEATED_DESCRIPTIVE_SUPPORT"):
    return {
        "event_timeframe": "15M",
        "event_family_set": ["INTERACTION"],
        "event_direction": "UP",
        "horizon_hours": 2,
        "endpoint_alignment": alignment,
        "excursion_dominance": "FAVORABLE_DOMINANT",
        "first_extreme": "DOWN_FIRST",
        "continuation_state": "CONTINUED",
        "frontier_outcome": "NOT_RETESTED_AND_HELD",
        "endpoint_range_location": "UPPER_THIRD",
        "repetition_status": status,
    }


class OptDReviewTests(unittest.TestCase):
    def test_admission_is_independent_of_alignment(self) -> None:
        aligned = review_disposition(archetype(alignment="ALIGNED")["repetition_status"])
        opposite = review_disposition(archetype(alignment="OPPOSITE")["repetition_status"])
        self.assertEqual(aligned, opposite)
        self.assertEqual(aligned[0], "CANDIDATE_FOR_BATCH_PREREGISTRATION")

    def test_antecedent_contains_no_forward_response(self) -> None:
        fields = story_antecedent(archetype())
        self.assertNotIn("horizon_hours", fields)
        self.assertNotIn("endpoint_alignment", fields)
        self.assertEqual(fields["eligibility_time"], "AFTER_EVENT_ANCHOR_CLOSE")

    def test_response_retains_horizon_and_path_semantics(self) -> None:
        response = story_response(archetype())
        self.assertEqual(response["horizon_hours"], 2)
        self.assertEqual(response["first_extreme"], "DOWN_FIRST")
        self.assertEqual(response["matching_rule"], "ALL_QUALITATIVE_RESPONSE_FIELDS_EXACT")

    def test_directional_mirror_inverts_absolute_path_fields(self) -> None:
        mirrored = mirror_story_features(archetype())
        self.assertEqual(mirrored["event_direction"], "DOWN")
        self.assertEqual(mirrored["first_extreme"], "UP_FIRST")
        self.assertEqual(mirrored["endpoint_range_location"], "LOWER_THIRD")
        self.assertEqual(mirrored["endpoint_alignment"], "ALIGNED")

    def test_holdout_rules_are_count_based_and_frozen(self) -> None:
        rules = frozen_holdout_rules()
        self.assertEqual(rules["minimum_evaluable_antecedent_clusters"], 10)
        self.assertEqual(rules["minimum_reappearance_matching_months"], 4)
        self.assertEqual(rules["threshold_optimization"], "PROHIBITED_DURING_HOLDOUT")

    def test_counter_story_requires_alignment_or_frontier_polarity_conflict(self) -> None:
        target = archetype()
        opposite = archetype(alignment="OPPOSITE")
        self.assertIn(
            "OPPOSITE_ENDPOINT_ALIGNMENT",
            response_contradiction_labels(target, opposite),
        )
        lost = archetype()
        lost["frontier_outcome"] = "LOST_AFTER_RETEST"
        self.assertIn(
            "OPPOSITE_FRONTIER_POLARITY",
            response_contradiction_labels(target, lost),
        )


if __name__ == "__main__":
    unittest.main()
