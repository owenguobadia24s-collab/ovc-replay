from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.distance import DistanceSpec, compute_distance
from ovc.opt_b.srfd.distance_optimized import batch_compute_prepared, deterministic_parallel_tiles, exact_equivalence
from ovc.opt_b.srfd.pair_index import canonical_ids, iter_pairs
from ovc.opt_b.srfd.semantic_cache import SemanticCache, TileCompletionLedger


ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_G8R_STATE_v0_2.json"


def records(n: int = 12) -> list[dict[str, object]]:
    return [
        {
            "representation_id": f"R{index:03d}",
            "comparability_domain_id": "D0",
            "ordering_semantics": "STATIC",
            "missingness": {},
            "structural_raw": {"x": format(index / 100, ".4f"), "y": format((index * 7 % 19) / 100, ".4f")},
        }
        for index in range(n)
    ]


class G8RWP2KernelTests(unittest.TestCase):
    def test_prepared_l1_l2_are_reference_exact(self) -> None:
        values = records()
        for method in ("L1_TYPED", "L2_TYPED"):
            spec = DistanceSpec(f"WP2.{method}", method, ("x", "y"), weights={"x":"2","y":"1"}, precision_places=8)
            self.assertTrue(exact_equivalence(values, spec))

    def test_unoptimized_method_falls_back_to_reference_exactly(self) -> None:
        values = records(8)
        spec = DistanceSpec("WP2.GOWER", "GOWER_MIXED", ("x", "y"), precision_places=8)
        ids = canonical_ids(item["representation_id"] for item in values)
        by_id = {item["representation_id"]: item for item in values}
        ordered = [by_id[item] for item in ids]
        reference = tuple(compute_distance(ordered[i], ordered[j], spec) for _, i, j in iter_pairs(len(ordered)))
        self.assertEqual(reference, batch_compute_prepared(values, spec))

    def test_parallel_worker_counts_preserve_logical_order(self) -> None:
        values = records(16)
        spec = DistanceSpec("WP2.L1", "L1_TYPED", ("x", "y"), precision_places=8)
        one = deterministic_parallel_tiles(values, spec, tile_pair_count=17, worker_count=1)
        two = deterministic_parallel_tiles(values, spec, tile_pair_count=17, worker_count=2)
        four = deterministic_parallel_tiles(values, spec, tile_pair_count=17, worker_count=4)
        self.assertEqual(one, two)
        self.assertEqual(one, four)


class G8RWP2CacheRestartTests(unittest.TestCase):
    def test_cache_scopes_are_distinct_and_corruption_quarantines(self) -> None:
        cache = SemanticCache()
        identity = {"pair_id":"P1","distance_spec_hash":"S1"}
        pair_key = cache.put("PAIR_LOCAL_REUSABLE", identity, {"distance":"0.1"})
        self.assertEqual({"distance":"0.1"}, cache.get("PAIR_LOCAL_REUSABLE", identity))
        self.assertIsNone(cache.get("POPULATION_SCOPED", identity))
        cache.corrupt_for_fixture(pair_key)
        self.assertIsNone(cache.get("PAIR_LOCAL_REUSABLE", identity))
        self.assertEqual("QA_CACHE_CORRUPTION", cache.quarantined[pair_key])

    def test_verified_complete_tile_is_never_recomputed(self) -> None:
        ledger = TileCompletionLedger()
        self.assertTrue(ledger.should_compute("T1"))
        ledger.register_complete("T1", content_hash="abc", attempt_id="A1")
        self.assertFalse(ledger.should_compute("T1", expected_hash="abc"))
        self.assertEqual(("A1",), ledger.attempts("T1"))
        self.assertTrue(ledger.should_compute("T1", expected_hash="different"))
        self.assertEqual("QA_CACHE_CORRUPTION", ledger.quarantined["T1"])

    def test_reserved_authority_remains_denied_and_g2f_blocks_wp3(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual("DENIED", state["authority"]["wp9"])
        self.assertEqual("DENIED", state["authority"]["june"])
        self.assertEqual("LOCKED_UNCONSUMED", state["authority"]["validation_2025"])
        wp3 = next(item for item in state["packets"] if item["packet_id"] == "SRFDI-G8R-WP3")
        self.assertIn("G8R_G2F_NOT_ACKNOWLEDGED", wp3["blockers"])


if __name__ == "__main__":
    unittest.main()
