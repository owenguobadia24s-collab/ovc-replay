from __future__ import annotations

import unittest

from ovc.opt_b.srfd.capacity import CapacityBudget, exact_pair_count, profile_fixture_capacity, project_capacity, render_measurement_line, synthetic_sources


class SRFDIWP8CapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = profile_fixture_capacity(
            representation_population_count=256,
            pairwise_population_count=128,
            family_population_count=48,
            dimensions=5,
            reference_population_count=8598,
            reference_population_basis={
                "source":"existing June full-month MDR coverage record only",
                "path":"docs/releases/pattern-discovery-v0-3/pd-june-full-month-mdr/wp2-replay/coverage.json",
                "field":"target_c2_state_count",
                "source_blob_sha":"2e283c6ec0b2d0fb5c65adfce1e22d80b2cd4427",
                "qualification":"not an SRFD eligible-population binding and not a June benchmark run"
            },
        )
        print(render_measurement_line(cls.receipt), flush=True)

    def test_exact_pair_count_and_no_sampling(self) -> None:
        self.assertEqual(8128, exact_pair_count(128))
        self.assertEqual("NONE", self.receipt["sampling"])
        self.assertEqual("EXACT_SYNTHETIC_GOLDEN", self.receipt["approximation_state"])
        self.assertEqual(8128, self.receipt["measurements"]["pairwise"]["pair_count"])

    def test_reference_is_non_binding_and_does_not_read_june_market_records(self) -> None:
        self.assertEqual("NON_BINDING_CAPACITY_REFERENCE_ONLY", self.receipt["reference_population"]["binding_status"])
        self.assertEqual("NOT_BOUND_AT_WP8", self.receipt["reference_population"]["srfd_eligible_population"])
        self.assertFalse(self.receipt["june_market_records_read"])
        self.assertFalse(self.receipt["june_benchmark_executed"])
        self.assertFalse(self.receipt["validation_consumed"])

    def test_budget_projection_has_explicit_pair_count_and_method_costs(self) -> None:
        projection = self.receipt["reference_projection"]
        self.assertEqual(exact_pair_count(8598), projection["pair_count"])
        self.assertEqual(4, len(projection["family_method_seconds"]))
        self.assertIn(projection["capacity_status"], {"CAPACITY_EXCEEDED", "WITHIN_PROVISIONAL_T0_PROJECTION"})

    def test_capacity_exceeded_is_controlled_not_hidden(self) -> None:
        tiny = CapacityBudget(max_runtime_seconds=0.000001, max_peak_rss_bytes=1, max_external_bytes=1)
        projected = project_capacity(self.receipt, 64, tiny)
        self.assertEqual("CAPACITY_EXCEEDED", projected.capacity_status)
        self.assertTrue(projected.reasons)

    def test_synthetic_source_is_deterministic(self) -> None:
        self.assertEqual(synthetic_sources(8, dimensions=3), synthetic_sources(8, dimensions=3))

    def test_restart_equivalence_is_measured(self) -> None:
        restart = self.receipt["measurements"]["checkpoint_restart"]
        self.assertTrue(restart["logical_equivalence"])
        self.assertTrue(restart["byte_equivalence"])


if __name__ == "__main__":
    unittest.main()
