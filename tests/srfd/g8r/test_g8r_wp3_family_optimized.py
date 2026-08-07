from __future__ import annotations

from itertools import combinations
import random
import unittest

from ovc.opt_b.srfd.families import (
    DistanceMatrix,
    FamilyMethodSpec,
    bounded_pam,
    hierarchical,
    medoid_star,
)
from ovc.opt_b.srfd.families_optimized import (
    PreparedDistanceMatrix,
    bounded_pam_optimized,
    hierarchical_optimized,
    medoid_star_optimized,
)
from ovc.opt_b.srfd.family_capacity import (
    profile_family_method_equivalence,
    render_family_profile_line,
)


def _matrix(ids: list[str], values: dict[str, str]) -> DistanceMatrix:
    return DistanceMatrix.from_pairs(ids, values)


def _random_matrix(population_count: int, seed: int) -> DistanceMatrix:
    rng = random.Random(seed)
    ids = [f"R{index:02d}" for index in range(population_count)]
    choices = (
        "0",
        "0.05",
        "0.10",
        "0.15",
        "0.20",
        "0.25",
        "0.30",
        "0.50",
        "1.00",
    )
    values = {
        f"{left}|{right}": rng.choice(choices)
        for left, right in combinations(ids, 2)
    }
    return _matrix(ids, values)


class SRFDIG8RWP3FamilyOptimizedTests(unittest.TestCase):
    def test_prepared_matrix_preserves_exact_decimal_surface(self) -> None:
        matrix = _matrix(
            ["A", "B", "C"],
            {
                "A|B": "0.1000000000000000001",
                "A|C": "0.2",
                "B|C": "0.3",
            },
        )
        prepared = PreparedDistanceMatrix.from_matrix(matrix)
        for left, right in combinations(matrix.ids, 2):
            self.assertEqual(
                matrix.distance(left, right), prepared.distance(left, right)
            )

    def test_medoid_star_ties_residuals_and_boundaries_match_reference(self) -> None:
        cases = [
            _matrix(
                ["A", "B", "C"],
                {"A|B": "0.1", "A|C": "0.1", "B|C": "0.2"},
            ),
            _matrix(
                ["A", "B", "C", "Z"],
                {
                    "A|B": "0.1",
                    "A|C": "0.2",
                    "A|Z": "1",
                    "B|C": "0.1",
                    "B|Z": "1",
                    "C|Z": "1",
                },
            ),
            _matrix(
                ["A", "B", "C"],
                {"A|B": "1", "A|C": "1", "B|C": "1"},
            ),
        ]
        for matrix in cases:
            for radius in ("0.1", "0.2", "0.25"):
                spec = FamilyMethodSpec(
                    "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
                    "G8R.TEST",
                    radius=radius,
                    minimum_support=2,
                )
                self.assertEqual(
                    medoid_star(matrix, spec), medoid_star_optimized(matrix, spec)
                )

    def test_hierarchical_complete_and_average_match_reference_on_ties(self) -> None:
        matrix = _matrix(
            ["A", "B", "C", "D", "E"],
            {
                "A|B": "0.10",
                "A|C": "0.10",
                "A|D": "0.40",
                "A|E": "0.40",
                "B|C": "0.20",
                "B|D": "0.40",
                "B|E": "0.40",
                "C|D": "0.30",
                "C|E": "0.30",
                "D|E": "0.10",
            },
        )
        for linkage in ("complete", "average"):
            for radius in ("0.10", "0.25", "0.40"):
                spec = FamilyMethodSpec(
                    linkage.upper() + "_LINKAGE",
                    "G8R.TEST",
                    radius=radius,
                    minimum_support=2,
                    linkage=linkage,
                )
                self.assertEqual(
                    hierarchical(matrix, spec),
                    hierarchical_optimized(matrix, spec),
                )

    def test_bounded_pam_matches_reference_with_outlier_and_ties(self) -> None:
        matrix = _matrix(
            ["A", "B", "C", "D", "Z"],
            {
                "A|B": "0.1",
                "A|C": "0.2",
                "A|D": "0.2",
                "A|Z": "5",
                "B|C": "0.1",
                "B|D": "0.2",
                "B|Z": "5",
                "C|D": "0.1",
                "C|Z": "5",
                "D|Z": "5",
            },
        )
        for k in (1, 2, 3):
            spec = FamilyMethodSpec(
                "BOUNDED_PAM",
                "G8R.TEST",
                k=k,
                minimum_support=2,
                max_assignment_distance="0.5",
                max_iterations=6,
            )
            self.assertEqual(
                bounded_pam(matrix, spec), bounded_pam_optimized(matrix, spec)
            )

    def test_deterministic_adversarial_population_sweep_is_reference_equivalent(self) -> None:
        for population_count in range(2, 9):
            for seed in range(6):
                matrix = _random_matrix(population_count, seed)
                medoid_spec = FamilyMethodSpec(
                    "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
                    "G8R.SWEEP",
                    radius="0.20",
                    minimum_support=2,
                )
                self.assertEqual(
                    medoid_star(matrix, medoid_spec),
                    medoid_star_optimized(matrix, medoid_spec),
                )
                for linkage in ("complete", "average"):
                    spec = FamilyMethodSpec(
                        linkage.upper() + "_LINKAGE",
                        "G8R.SWEEP",
                        radius="0.20",
                        minimum_support=2,
                        linkage=linkage,
                    )
                    self.assertEqual(
                        hierarchical(matrix, spec),
                        hierarchical_optimized(matrix, spec),
                    )
                pam_spec = FamilyMethodSpec(
                    "BOUNDED_PAM",
                    "G8R.SWEEP",
                    k=min(2, population_count),
                    minimum_support=2,
                    max_assignment_distance="0.30",
                    max_iterations=5,
                )
                self.assertEqual(
                    bounded_pam(matrix, pam_spec),
                    bounded_pam_optimized(matrix, pam_spec),
                )

    def test_family_capacity_profile_is_measured_equivalent_and_firewalled(self) -> None:
        receipt = profile_family_method_equivalence((48, 96))
        self.assertEqual([48, 96], receipt["population_counts"])
        self.assertFalse(receipt["june_market_records_read"])
        self.assertFalse(receipt["validation_consumed"])
        self.assertEqual("NONE", receipt["scientific_delta"])
        self.assertEqual("CANDIDATE_UNADMITTED", receipt["numpy_backend"])
        for rung in receipt["rungs"].values():
            self.assertEqual(4, len(rung["methods"]))
            self.assertTrue(
                all(
                    item["logical_equivalence"]
                    for item in rung["methods"].values()
                )
            )
        print(render_family_profile_line(receipt))


if __name__ == "__main__":
    unittest.main()
