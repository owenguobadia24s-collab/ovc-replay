from __future__ import annotations

import copy
import unittest

from ovc_opt_b import descriptive_support_band, measurement_semantic_violations, overlap_stratum


def valid_record() -> dict[str, object]:
    return {
        "anchor_price": "1.1000",
        "event_direction": "UP",
        "horizon_hours": 1,
        "path_bar_count": 4,
        "pip_size": "0.0001",
        "transition_lineage": {"transition_count": 2},
        "measurements": {
            "endpoint_price": "1.1010", "raw_return_price": "0.0010", "raw_return_pips": "10",
            "maximum_upward_excursion_price": "0.0020", "maximum_upward_excursion_pips": "20",
            "maximum_downward_excursion_price": "0.0005", "maximum_downward_excursion_pips": "5",
            "forward_maximum_price": "1.1020", "forward_minimum_price": "1.0995",
            "forward_range_price": "0.0025", "endpoint_close_position_in_forward_range": "0.6",
            "maximum_time_elapsed_minutes": 45, "minimum_time_elapsed_minutes": 15,
            "direction_normalization_status": "DIRECTIONAL",
            "direction_normalized_endpoint_return_pips": "10",
            "direction_normalized_favorable_excursion_pips": "20",
            "direction_normalized_adverse_excursion_pips": "5",
            "continued_beyond_event_extreme": True, "first_continuation_elapsed_minutes": 30,
            "frontier_tests": [{
                "frontier_type": "FLOOR", "frontier_price": "1.0990", "retested": False,
                "first_retest_elapsed_minutes": None, "lost_on_close": False,
                "first_loss_elapsed_minutes": None, "held_at_endpoint": True, "endpoint_relation": "ABOVE",
            }],
            "primary_frontier_type": "FLOOR", "primary_frontier_retested": False,
            "primary_frontier_lost_on_close": False, "primary_frontier_held_at_endpoint": True,
            "directional_reversal_through_frontier": False,
        },
    }


class OptCSemanticReviewTests(unittest.TestCase):
    def test_support_bands(self) -> None:
        self.assertEqual(descriptive_support_band(0), "EMPTY")
        self.assertEqual(descriptive_support_band(29), "SPARSE_NO_COMPARISON")
        self.assertEqual(descriptive_support_band(30), "LIMITED_DESCRIPTIVE_SUPPORT")
        self.assertEqual(descriptive_support_band(100), "ADEQUATE_DESCRIPTIVE_SUPPORT")

    def test_overlap_strata(self) -> None:
        base = {"overlap_present": False, "subsequent_overlap_anchor_count_same_clock": 0,
                "subsequent_overlap_anchor_count_all_clocks": 0}
        self.assertEqual(overlap_stratum(base), "NO_OVERLAP")
        base["overlap_present"] = True
        self.assertEqual(overlap_stratum(base), "SAME_TIME_ONLY")
        base["subsequent_overlap_anchor_count_all_clocks"] = 1
        self.assertEqual(overlap_stratum(base), "SUBSEQUENT_CROSS_CLOCK_ONLY")
        base["subsequent_overlap_anchor_count_same_clock"] = 1
        self.assertEqual(overlap_stratum(base), "SUBSEQUENT_SAME_CLOCK")

    def test_valid_measurement_has_no_violations(self) -> None:
        self.assertEqual(measurement_semantic_violations(valid_record()), [])

    def test_raw_return_defect_is_detected(self) -> None:
        row = valid_record()
        row["measurements"]["raw_return_price"] = "0.0020"
        self.assertIn("RAW_RETURN_IDENTITY", measurement_semantic_violations(row))

    def test_non_directional_values_are_rejected(self) -> None:
        row = valid_record()
        row["event_direction"] = "MIXED"
        self.assertIn("NON_DIRECTIONAL_STATUS", measurement_semantic_violations(row))

    def test_frontier_hold_defect_is_detected(self) -> None:
        row = valid_record()
        row["measurements"]["frontier_tests"][0]["held_at_endpoint"] = False
        self.assertIn("FRONTIER_ENDPOINT_HOLD", measurement_semantic_violations(row))


if __name__ == "__main__":
    unittest.main()
