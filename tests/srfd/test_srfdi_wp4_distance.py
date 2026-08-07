from __future__ import annotations

import unittest

from ovc.opt_b.srfd.distance import DistanceCache, DistanceSpec, compute_distance, deterministic_pair_id, pair_tiles


def rep(rep_id: str, x: str, y: str, *, domain: str = "D1") -> dict:
    return {"representation_id":rep_id,"comparability_domain_id":domain,"ordering_semantics":"STATIC_VECTOR","missingness":[],"structural_raw":{"x":x,"y":y},"structural_derived":{},"structural_normalized":{},"comparison_only":{}}


class SRFDIWP4DistanceTests(unittest.TestCase):
    def test_l1_and_l2_golden_and_symmetry(self) -> None:
        left, right = rep("A","0","0"), rep("B","3","4")
        l1 = DistanceSpec("D.L1","L1_TYPED",("x","y"))
        l2 = DistanceSpec("D.L2","L2_TYPED",("x","y"))
        self.assertEqual("3.500000000000",compute_distance(left,right,l1)["distance"])
        self.assertEqual(compute_distance(left,right,l1)["distance"],compute_distance(right,left,l1)["distance"])
        self.assertEqual("3.535533905933",compute_distance(left,right,l2)["distance"])
        self.assertEqual(compute_distance(left,right,l2)["distance"],compute_distance(right,left,l2)["distance"])

    def test_not_comparable_short_circuits_distance(self) -> None:
        result = compute_distance(rep("A","0","0",domain="D1"),rep("B","1","1",domain="D2"),DistanceSpec("D","L1_TYPED",("x","y")))
        self.assertEqual("NOT_COMPARABLE",result["status"])
        self.assertFalse(result["compute_invoked"])
        self.assertIsNone(result["distance"])

    def test_pair_id_and_tiles_are_input_order_independent(self) -> None:
        spec = DistanceSpec("D","L1_TYPED",("x",))
        self.assertEqual(deterministic_pair_id("A","B",spec,comparability_domain_id="D1"),deterministic_pair_id("B","A",spec,comparability_domain_id="D1"))
        self.assertEqual(pair_tiles(["C","A","B"],tile_size=2),pair_tiles(["B","C","A"],tile_size=2))
        self.assertEqual([[('A','B'),('A','C')],[('B','C')]],pair_tiles(["C","A","B"],tile_size=2))

    def test_cache_semantic_invalidation_and_corruption_quarantine(self) -> None:
        left, right = rep("A","0","0"), rep("B","1","1")
        spec = DistanceSpec("D1","L1_TYPED",("x","y"))
        result = compute_distance(left,right,spec)
        cache = DistanceCache(); key = cache.put(result,spec)
        self.assertEqual(result,cache.get(key,spec))
        changed = DistanceSpec("D1","L1_TYPED",("x","y"),weights={"x":"2","y":"1"})
        self.assertIsNone(cache.get(key,changed))
        cache.corrupt_for_fixture(key)
        self.assertIsNone(cache.get(key,spec))
        self.assertEqual("QA_CACHE_CORRUPTION",cache.quarantined[key])

    def test_dtw_sequence_reference(self) -> None:
        left = {"representation_id":"S1","comparability_domain_id":"D1","ordering_semantics":"ORDERED_SEQUENCE","missingness":[],"structural_derived":{"ordered_sequence":[0,1,2]}}
        right = {"representation_id":"S2","comparability_domain_id":"D1","ordering_semantics":"ORDERED_SEQUENCE","missingness":[],"structural_derived":{"ordered_sequence":[0,1,3]}}
        result = compute_distance(left,right,DistanceSpec("DTW","DTW_SEQUENCE",()))
        self.assertEqual("COMPUTED",result["status"])
        self.assertEqual("0.333333333333",result["distance"])

    def test_distance_tie_has_stable_pair_ids(self) -> None:
        spec = DistanceSpec("D","L1_TYPED",("x",))
        anchor = rep("A","0","0"); b = rep("B","1","0"); c = rep("C","1","0")
        rb = compute_distance(anchor,b,spec); rc = compute_distance(anchor,c,spec)
        self.assertEqual(rb["distance"],rc["distance"])
        self.assertEqual(sorted([rb["pair_id"],rc["pair_id"]]),[item["pair_id"] for item in sorted([rb,rc],key=lambda item:item["pair_id"])])


if __name__ == "__main__":
    unittest.main()
