from __future__ import annotations

from decimal import Decimal
from itertools import combinations
import random
import unittest

from ovc.opt_b.srfd.families import DistanceMatrix, FamilyMethodSpec, hierarchical
from ovc.opt_b.srfd.family_grid_capacity import (
    build_hierarchical_trace,
    frozen_hierarchical_configuration_id,
    materialize_hierarchical_trace,
    verify_hierarchical_grid_against_independent_optimized,
)


def random_matrix(n: int, seed: int) -> DistanceMatrix:
    rng = random.Random(seed)
    ids = [f"T{i:02d}" for i in range(n)]
    values = [
        "0.000000000000",
        "0.039999999999",
        "0.040000000000",
        "0.040000000001",
        "0.079999999999",
        "0.080000000000",
        "0.080000000001",
        "0.159999999999",
        "0.160000000000",
        "0.160000000001",
        "0.200000000000",
        "0.333333333333",
        "0.666666666667",
        "1.000000000000",
    ]
    pairs = {
        f"{left}|{right}": rng.choice(values)
        for left, right in combinations(ids, 2)
    }
    return DistanceMatrix.from_pairs(ids, pairs)


class SRFDIWP10AHierarchicalTraceReuseTests(unittest.TestCase):
    def test_all_18_materialized_configs_equal_independent_optimized(self) -> None:
        for n in (2, 4, 8, 12):
            for seed in range(8):
                receipt = verify_hierarchical_grid_against_independent_optimized(
                    random_matrix(n, seed),
                    domain_id=f"D-{n}-{seed}",
                )
                self.assertEqual("PASS", receipt["result"])
                self.assertEqual(18, receipt["checked_configuration_count"])

    def test_trace_materialization_equals_reference_oracle(self) -> None:
        surface = random_matrix(10, 991)
        for linkage, method_id in (("complete", "COMPLETE_LINKAGE"), ("average", "AVERAGE_LINKAGE")):
            trace = build_hierarchical_trace(surface, linkage=linkage, max_radius="0.16")
            for radius in ("0.04", "0.08", "0.16"):
                for support in (2, 4, 8):
                    config = frozen_hierarchical_configuration_id(
                        domain_id="REFERENCE-DOMAIN",
                        linkage=linkage,
                        radius=radius,
                        minimum_support=support,
                    )
                    spec = FamilyMethodSpec(
                        method_id,
                        config,
                        radius=radius,
                        minimum_support=support,
                        linkage=linkage,
                    )
                    self.assertEqual(
                        hierarchical(surface, spec),
                        materialize_hierarchical_trace(surface, trace, spec),
                    )

    def test_average_trace_score_is_exact_sum_over_count(self) -> None:
        ids = ["A", "B", "C", "D"]
        surface = DistanceMatrix.from_pairs(
            ids,
            {
                "A|B": "0.010000000000",
                "A|C": "0.050000000000",
                "A|D": "0.070000000000",
                "B|C": "0.090000000000",
                "B|D": "0.110000000000",
                "C|D": "0.020000000000",
            },
        )
        trace = build_hierarchical_trace(surface, linkage="average", max_radius="0.16")
        self.assertGreaterEqual(len(trace.steps), 2)
        merged_step = next(step for step in trace.steps if len(step.merged) > 2)
        self.assertGreater(merged_step.count, 1)
        self.assertEqual(
            Decimal(merged_step.numerator) / Decimal(merged_step.count),
            Decimal(merged_step.exact_score.numerator) / Decimal(merged_step.exact_score.denominator),
        )

    def test_trace_rejects_population_or_radius_mismatch(self) -> None:
        surface = random_matrix(6, 4)
        trace = build_hierarchical_trace(surface, linkage="average", max_radius="0.16")
        spec = FamilyMethodSpec(
            "AVERAGE_LINKAGE",
            "X",
            radius="0.20",
            minimum_support=2,
            linkage="average",
        )
        with self.assertRaisesRegex(Exception, "max radius"):
            materialize_hierarchical_trace(surface, trace, spec)


if __name__ == "__main__":
    unittest.main()
