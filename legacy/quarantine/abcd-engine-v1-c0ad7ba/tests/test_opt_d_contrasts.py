from __future__ import annotations

from decimal import Decimal
import unittest

from ovc_opt_b import (
    cluster_balanced_metric,
    contrast_readiness,
    exclusive_arms,
    temporal_delta_status,
)


def row(record_id: str, value: str):
    return {
        "neutral_outcome_record_id": record_id,
        "measurements": {"direction_normalized_endpoint_return_pips": value},
    }


class OptDContrastTests(unittest.TestCase):
    def test_cluster_balancing_gives_each_cluster_equal_mass(self) -> None:
        rows = [row("a", "100"), row("b", "100"), row("c", "0")]
        result = cluster_balanced_metric(
            rows,
            cluster_by_outcome={"a": "c1", "b": "c1", "c": "c2"},
            metric_field="direction_normalized_endpoint_return_pips",
        )
        self.assertEqual(result["cluster_balanced_median"], "50")
        self.assertEqual(result["measured_clusters"], 2)

    def test_exclusive_arms_retain_shared_ids_separately(self) -> None:
        a, b, shared = exclusive_arms([row("a", "1"), row("x", "2")], [row("b", "3"), row("x", "2")])
        self.assertEqual([item["neutral_outcome_record_id"] for item in a], ["a"])
        self.assertEqual([item["neutral_outcome_record_id"] for item in b], ["b"])
        self.assertEqual(shared, ["x"])

    def test_contrast_readiness_requires_clusters_not_only_rows(self) -> None:
        self.assertEqual(
            contrast_readiness(200, 20, 6, 200, 150, 6),
            "INVENTORY_ONLY_AFTER_EXCLUSIVITY",
        )
        self.assertEqual(
            contrast_readiness(200, 80, 6, 200, 90, 6),
            "LIMITED_CLUSTERED_CONTRAST",
        )
        self.assertEqual(
            contrast_readiness(200, 120, 6, 200, 110, 6),
            "DESCRIPTIVE_CONTRAST_READY",
        )

    def test_temporal_delta_status_needs_three_months(self) -> None:
        self.assertEqual(
            temporal_delta_status([Decimal("1"), Decimal("2")])["temporal_delta_status"],
            "INSUFFICIENT_MONTHLY_SUPPORT",
        )
        self.assertEqual(
            temporal_delta_status([Decimal("1"), Decimal("2"), Decimal("3"), Decimal("-1"), Decimal("4")])[
                "temporal_delta_status"
            ],
            "DELTA_SIGN_CONSISTENT_80PCT",
        )


if __name__ == "__main__":
    unittest.main()
