from __future__ import annotations

from itertools import combinations
import random
import unittest

from ovc.opt_b.srfd.families import (
    DistanceMatrix,
    FamilyMethodSpec,
    bounded_pam,
    medoid_star,
)
from ovc.opt_b.srfd.family_grid_reuse import (
    build_bounded_pam_core,
    build_medoid_star_trace,
    frozen_medoid_configuration_id,
    frozen_pam_configuration_id,
    materialize_bounded_pam_core,
    materialize_medoid_star_trace,
    verify_reuse_against_independent_optimized,
)


def random_matrix(n: int, seed: int) -> DistanceMatrix:
    rng = random.Random(seed)
    ids = [f"M{i:02d}" for i in range(n)]
    lattice = [
        "0.000000000000",
        "0.039999999999",
        "0.040000000000",
        "0.040000000001",
        "0.079999999999",
        "0.080000000000",
        "0.080000000001",
        "0.099999999999",
        "0.100000000000",
        "0.100000000001",
        "0.159999999999",
        "0.160000000000",
        "0.160000000001",
        "0.199999999999",
        "0.200000000000",
        "0.200000000001",
        "0.399999999999",
        "0.400000000000",
        "0.400000000001",
        "1.000000000000",
    ]
    return DistanceMatrix.from_pairs(
        ids,
        {
            f"{left}|{right}": rng.choice(lattice)
            for left, right in combinations(ids, 2)
        },
    )


class SRFDIWP10AMedoidPamReuseTests(unittest.TestCase):
    def test_all_reused_configs_equal_independent_optimized(self) -> None:
        for n in (8, 12):
            for seed in range(6):
                receipt = verify_reuse_against_independent_optimized(
                    random_matrix(n, seed),
                    domain_id=f"REUSE-{n}-{seed}",
                )
                self.assertEqual("PASS", receipt["result"])
                self.assertEqual(36, receipt["checked_configuration_count"])

    def test_medoid_prefix_materialization_equals_reference_oracle(self) -> None:
        surface = random_matrix(12, 71)
        for radius in ("0.04", "0.08", "0.16"):
            trace = build_medoid_star_trace(surface, radius=radius)
            for support in (2, 4, 8):
                config = frozen_medoid_configuration_id(
                    domain_id="REFERENCE",
                    radius=radius,
                    minimum_support=support,
                )
                spec = FamilyMethodSpec(
                    "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
                    config,
                    radius=radius,
                    minimum_support=support,
                )
                self.assertEqual(
                    medoid_star(surface, spec),
                    materialize_medoid_star_trace(surface, trace, spec),
                )

    def test_pam_support_materialization_equals_reference_oracle(self) -> None:
        surface = random_matrix(12, 121)
        for k in (2, 4, 8):
            for radius in ("0.10", "0.20", "0.40"):
                core = build_bounded_pam_core(
                    surface,
                    k=k,
                    max_assignment_distance=radius,
                    max_iterations=8,
                )
                for support in (2, 4, 8):
                    config = frozen_pam_configuration_id(
                        domain_id="REFERENCE",
                        k=k,
                        max_assignment_distance=radius,
                        max_iterations=8,
                        minimum_support=support,
                    )
                    spec = FamilyMethodSpec(
                        "BOUNDED_PAM",
                        config,
                        k=k,
                        max_assignment_distance=radius,
                        max_iterations=8,
                        minimum_support=support,
                    )
                    self.assertEqual(
                        bounded_pam(surface, spec),
                        materialize_bounded_pam_core(surface, core, spec),
                    )

    def test_medoid_trace_and_pam_core_reject_mismatched_specs(self) -> None:
        surface = random_matrix(8, 8)
        trace = build_medoid_star_trace(surface, radius="0.08")
        wrong_medoid = FamilyMethodSpec(
            "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
            "WRONG",
            radius="0.16",
            minimum_support=2,
        )
        with self.assertRaisesRegex(Exception, "radius mismatch"):
            materialize_medoid_star_trace(surface, trace, wrong_medoid)

        core = build_bounded_pam_core(
            surface,
            k=4,
            max_assignment_distance="0.20",
            max_iterations=8,
        )
        wrong_pam = FamilyMethodSpec(
            "BOUNDED_PAM",
            "WRONG",
            k=2,
            max_assignment_distance="0.20",
            max_iterations=8,
            minimum_support=2,
        )
        with self.assertRaisesRegex(Exception, "core/spec mismatch"):
            materialize_bounded_pam_core(surface, core, wrong_pam)


if __name__ == "__main__":
    unittest.main()
