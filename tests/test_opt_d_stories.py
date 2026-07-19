from __future__ import annotations

from decimal import Decimal
import unittest

from ovc_opt_b import canonical_cluster_representatives, qualitative_story_features, select_representative_cases


def row(record_id: str, value: str, *, alignment_value: str | None = None):
    alignment_value = value if alignment_value is None else alignment_value
    return {
        "neutral_outcome_record_id": record_id,
        "event_anchor_id": f"a-{record_id}",
        "event_timeframe": "15M",
        "horizon_hours": 1,
        "event_direction": "UP",
        "measurements": {
            "direction_normalized_endpoint_return_pips": alignment_value,
            "direction_normalized_favorable_excursion_pips": "10",
            "direction_normalized_adverse_excursion_pips": "5",
            "first_extreme": "UP_FIRST",
            "continued_beyond_event_extreme": True,
            "primary_frontier_type": "FLOOR",
            "primary_frontier_retested": True,
            "primary_frontier_lost_on_close": False,
            "primary_frontier_held_at_endpoint": True,
            "endpoint_close_position_in_forward_range": "0.8",
            "raw_return_pips": value,
        },
        "endpoint_b_state_snapshot": {
            "acceptance_event_state": "NONE", "displacement_state": "NONE",
            "compression_state": "NORMAL", "interaction_state": "NONE", "quality_state": "COHERENT",
        },
        "transition_lineage": {"counts_by_axis": {"DISPLACEMENT": 1}},
    }


class OptDStoryTests(unittest.TestCase):
    def test_qualitative_features_do_not_include_exact_return(self) -> None:
        first = qualitative_story_features(row("a", "5"), event_families=["DISPLACEMENT"])
        second = qualitative_story_features(row("b", "50"), event_families=["DISPLACEMENT"])
        self.assertEqual(first["story_archetype_id"], second["story_archetype_id"])
        self.assertEqual(first["endpoint_alignment"], "ALIGNED")

    def test_exact_endpoint_state_is_lineage_not_archetype_identity(self) -> None:
        first_row = row("a", "5")
        second_row = row("b", "5")
        second_row["endpoint_b_state_snapshot"]["interaction_state"] = "RECLAIMED"
        second_row["transition_lineage"]["counts_by_axis"] = {"INTERACTION": 3}
        first = qualitative_story_features(first_row, event_families=["DISPLACEMENT"])
        second = qualitative_story_features(second_row, event_families=["DISPLACEMENT"])
        self.assertEqual(first["story_archetype_id"], second["story_archetype_id"])

    def test_event_family_set_remains_archetype_identity(self) -> None:
        first = qualitative_story_features(row("a", "5"), event_families=["DISPLACEMENT"])
        second = qualitative_story_features(row("b", "5"), event_families=["ACCEPTANCE"])
        self.assertNotEqual(first["story_archetype_id"], second["story_archetype_id"])

    def test_cluster_representative_is_closest_to_cluster_median(self) -> None:
        rows = [row("a", "0"), row("b", "10"), row("c", "100")]
        selected = canonical_cluster_representatives(
            rows,
            cluster_by_outcome={"a": "c1", "b": "c1", "c": "c2"},
            metric_field="raw_return_pips",
        )
        self.assertEqual([item["neutral_outcome_record_id"] for item in selected], ["a", "c"])

    def test_case_roles_are_deterministic_and_cluster_distinct_for_quantiles(self) -> None:
        rows = [row("a", "0"), row("b", "10"), row("c", "20"), row("d", "30")]
        cases = select_representative_cases(
            rows,
            cluster_by_outcome={key: key for key in ("a", "b", "c", "d")},
            metric_field="raw_return_pips",
        )
        standard = [case for case in cases if case["case_role"] in ("CENTRAL", "LOWER_TAIL", "UPPER_TAIL")]
        self.assertEqual(len({case["overlap_cluster_id"] for case in standard}), 3)

    def test_opposite_endpoint_case_is_retained(self) -> None:
        rows = [row("a", "0", alignment_value="-5"), row("b", "10", alignment_value="10")]
        cases = select_representative_cases(
            rows,
            cluster_by_outcome={"a": "c1", "b": "c2"},
            metric_field="raw_return_pips",
        )
        self.assertIn("OPPOSITE_DIRECTION_COUNTEREXAMPLE", {case["case_role"] for case in cases})


if __name__ == "__main__":
    unittest.main()
