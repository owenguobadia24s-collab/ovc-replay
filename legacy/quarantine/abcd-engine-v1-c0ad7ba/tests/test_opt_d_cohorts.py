from __future__ import annotations

import unittest

from ovc_opt_b import build_overlap_clusters, cohort_readiness, descriptive_band, semantic_event_signature


def row(record_id: str, start: str, end: str, clock: str = "15M", horizon: int = 1):
    return {
        "neutral_outcome_record_id": record_id,
        "event_anchor_id": f"a-{record_id}",
        "event_timeframe": clock,
        "anchor_time": start,
        "endpoint_time": end,
        "horizon_hours": horizon,
    }


class OptDCohortTests(unittest.TestCase):
    def test_half_open_adjacent_intervals_do_not_overlap(self) -> None:
        rows = [
            row("r1", "2026-01-01T00:00:00+00:00", "2026-01-01T01:00:00+00:00"),
            row("r2", "2026-01-01T01:00:00+00:00", "2026-01-01T02:00:00+00:00"),
        ]
        clusters, assignment = build_overlap_clusters(rows)
        self.assertEqual(len(clusters), 2)
        self.assertNotEqual(assignment["r1"], assignment["r2"])

    def test_transitive_overlap_is_one_cluster(self) -> None:
        rows = [
            row("r1", "2026-01-01T00:00:00+00:00", "2026-01-01T01:00:00+00:00"),
            row("r2", "2026-01-01T00:30:00+00:00", "2026-01-01T01:30:00+00:00", "2H"),
            row("r3", "2026-01-01T01:15:00+00:00", "2026-01-01T02:15:00+00:00"),
        ]
        clusters, assignment = build_overlap_clusters(rows)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(set(assignment.values())), 1)
        self.assertEqual(clusters[0]["event_timeframe_counts"], {"15M": 2, "2H": 1})

    def test_mixed_horizons_are_rejected(self) -> None:
        rows = [
            row("r1", "2026-01-01T00:00:00+00:00", "2026-01-01T01:00:00+00:00", horizon=1),
            row("r2", "2026-01-01T00:00:00+00:00", "2026-01-01T02:00:00+00:00", horizon=2),
        ]
        with self.assertRaises(ValueError):
            build_overlap_clusters(rows)

    def test_support_and_readiness_controls(self) -> None:
        self.assertEqual(descriptive_band(29), "SPARSE")
        self.assertEqual(descriptive_band(100), "ADEQUATE")
        self.assertEqual(cohort_readiness(200, 20, 6), "INVENTORY_ONLY_CLUSTER_SPARSE")
        self.assertEqual(cohort_readiness(200, 80, 6), "LIMITED_CLUSTERED_DESCRIPTION")
        self.assertEqual(cohort_readiness(200, 120, 6), "DESCRIPTIVE_COHORT_READY")

    def test_signature_ignores_component_order_and_level_ids(self) -> None:
        first = {"event_components": [
            {"family": "INTERACTION", "subtype": "REJECTION", "direction": "DOWN", "support_level_ids": ["a"]},
            {"family": "DISPLACEMENT", "subtype": "ONSET", "direction": "DOWN", "support_level_ids": []},
        ]}
        second = {"event_components": [
            {"family": "DISPLACEMENT", "subtype": "ONSET", "direction": "DOWN", "support_level_ids": ["x"]},
            {"family": "INTERACTION", "subtype": "REJECTION", "direction": "DOWN", "support_level_ids": ["b"]},
        ]}
        self.assertEqual(
            semantic_event_signature(first)["semantic_signature_hash"],
            semantic_event_signature(second)["semantic_signature_hash"],
        )


if __name__ == "__main__":
    unittest.main()
