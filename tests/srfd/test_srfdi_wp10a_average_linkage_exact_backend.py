from __future__ import annotations

from itertools import combinations
import random
import unittest

from ovc.opt_b.srfd.families import DistanceMatrix, FamilyMethodSpec, hierarchical
from ovc.opt_b.srfd.families_optimized import hierarchical_optimized


def matrix(ids: list[str], values: dict[str, str]) -> DistanceMatrix:
    return DistanceMatrix.from_pairs(ids, values)


def random_matrix(n: int, seed: int) -> DistanceMatrix:
    rng = random.Random(seed)
    ids = [f"R{i:02d}" for i in range(n)]
    lattice = [
        "0.000000000001",
        "0.039999999999",
        "0.040000000000",
        "0.040000000001",
        "0.079999999999",
        "0.080000000000",
        "0.080000000001",
        "0.159999999999",
        "0.160000000000",
        "0.160000000001",
        "0.333333333333",
        "0.666666666667",
        "1.000000000000",
    ]
    values = {
        f"{left}|{right}": rng.choice(lattice)
        for left, right in combinations(ids, 2)
    }
    return matrix(ids, values)


class SRFDIWP10AAverageLinkageExactBackendTests(unittest.TestCase):
    def assert_reference_equivalent(self, surface: DistanceMatrix) -> None:
        for radius in ("0.04", "0.08", "0.16", "1"):
            for minimum_support in (2, 4, 8):
                if minimum_support > len(surface.ids):
                    continue
                spec = FamilyMethodSpec(
                    "AVERAGE_LINKAGE",
                    f"WP10A.AVG.{radius}.{minimum_support}",
                    radius=radius,
                    minimum_support=minimum_support,
                    linkage="average",
                )
                self.assertEqual(
                    hierarchical(surface, spec),
                    hierarchical_optimized(surface, spec),
                )

    def test_exact_sum_count_matches_reference_on_unbalanced_cluster_merges(self) -> None:
        surface = matrix(
            ["A", "B", "C", "D", "E", "F"],
            {
                "A|B": "0.010000000000",
                "A|C": "0.020000000000",
                "A|D": "0.150000000000",
                "A|E": "0.150000000000",
                "A|F": "0.300000000000",
                "B|C": "0.030000000000",
                "B|D": "0.150000000000",
                "B|E": "0.150000000000",
                "B|F": "0.300000000000",
                "C|D": "0.140000000000",
                "C|E": "0.140000000000",
                "C|F": "0.300000000000",
                "D|E": "0.010000000000",
                "D|F": "0.200000000000",
                "E|F": "0.200000000000",
            },
        )
        self.assert_reference_equivalent(surface)

    def test_exact_sum_count_preserves_decimal_boundary_and_tie_semantics(self) -> None:
        surface = matrix(
            ["A", "B", "C", "D", "E"],
            {
                "A|B": "0.040000000000",
                "A|C": "0.080000000001",
                "A|D": "0.159999999999",
                "A|E": "0.160000000001",
                "B|C": "0.079999999999",
                "B|D": "0.160000000001",
                "B|E": "0.159999999999",
                "C|D": "0.040000000000",
                "C|E": "0.080000000000",
                "D|E": "0.040000000000",
            },
        )
        self.assert_reference_equivalent(surface)

    def test_randomized_frozen_precision_lattice_is_reference_equivalent(self) -> None:
        for n in range(2, 11):
            for seed in range(12):
                self.assert_reference_equivalent(random_matrix(n, seed))


if __name__ == "__main__":
    unittest.main()
