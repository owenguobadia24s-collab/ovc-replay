from __future__ import annotations

import unittest

from ovc.opt_b.srfd.capacity_wp6 import (
    METHOD_IDS,
    REFERENCE_N,
    WP6_RUNGS,
    profile_wp6_capacity,
    render_wp6_profile_line,
)
from ovc.opt_b.srfd.pair_index import exact_pair_count


class SRFDIG8RWP6CapacityProfileOutputTest(unittest.TestCase):
    def test_zzzz_emit_github_hosted_multi_n_capacity_profile(self) -> None:
        receipt = profile_wp6_capacity()
        self.assertEqual(list(WP6_RUNGS), receipt["population_counts"])
        self.assertEqual("NONE", receipt["scientific_delta"])
        self.assertFalse(receipt["june_market_records_read"])
        self.assertFalse(receipt["validation_consumed"])
        self.assertEqual("DENIED", receipt["wp9"])
        self.assertEqual("PRESERVE_DO_NOT_MERGE", receipt["pr_371"])
        self.assertEqual("CANDIDATE_UNADMITTED", receipt["backend"]["numpy"])

        for n in WP6_RUNGS:
            rung = receipt["rungs"][str(n)]
            self.assertEqual(n, rung["population_count"])
            self.assertGreater(rung["representation"]["wall_seconds"], 0)
            self.assertEqual(exact_pair_count(n), rung["distance"]["pair_count"])
            self.assertEqual(8, rung["distance"]["compact_payload_bytes_per_pair"])
            self.assertGreater(rung["distance"]["distance_compute_seconds"], 0)
            self.assertEqual(set(METHOD_IDS), set(rung["family"]["methods"]))
            self.assertTrue(
                all(item["wall_seconds"] > 0 for item in rung["family"]["methods"].values())
            )

        sweep = receipt["worker_sweep"]
        self.assertEqual([1, 2, 4], [row["worker_count"] for row in sweep["rows"]])
        self.assertTrue(sweep["logical_equivalence"])
        self.assertFalse(receipt["storage_restart"]["verified_complete_tile_recomputed"])
        self.assertEqual(8, receipt["storage_restart"]["bytes_per_pair"])

        projection = receipt["projection"]
        self.assertEqual(REFERENCE_N, projection["reference_population"]["population_count"])
        self.assertEqual(
            "NON_BINDING_CAPACITY_REFERENCE_ONLY",
            projection["reference_population"]["binding_status"],
        )
        self.assertIn(
            projection["full_required_dag"]["capacity_status"],
            {"SUPPORTED_T0", "SUPPORTED_T1", "REQUIRES_SEPARATE_CAPACITY_TIER"},
        )
        self.assertEqual(set(METHOD_IDS), set(projection["method_capacity_statuses"]))
        self.assertFalse(projection["full_required_dag"]["cache_reuse_assumed"])
        self.assertFalse(projection["full_required_dag"]["parallel_speedup_assumed"])
        self.assertEqual("EXTRAPOLATED", projection["full_required_dag"]["measurement_class"])
        print(render_wp6_profile_line(receipt))


if __name__ == "__main__":
    unittest.main()
