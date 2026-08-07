from __future__ import annotations

from decimal import Decimal
from itertools import combinations
import json
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from ovc.opt_b.srfd.distance import DistanceSpec
from ovc.opt_b.srfd.distance_optimized import deterministic_parallel_tiles, exact_equivalence
from ovc.opt_b.srfd.distance_surface import DistanceSurfaceError, TileHeader, coefficient_to_decimal, coefficient_width, decimal_to_coefficient, read_exact_tile, write_exact_tile
from ovc.opt_b.srfd.families import DistanceMatrix, FamilyMethodSpec, bounded_pam, hierarchical, medoid_star
from ovc.opt_b.srfd.families_optimized import bounded_pam_optimized, hierarchical_optimized, medoid_star_optimized
from ovc.opt_b.srfd.pair_index import exact_pair_count, index_to_pair, pair_to_index
from ovc.opt_b.srfd.scheduler import CapacityBudget, build_capacity_plan
from ovc.opt_b.srfd.semantic_cache import SemanticCache, TileCompletionLedger
from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_G8R_STATE_v0_2.json"
BACKEND_LOCK = ROOT / "registries/research/srfd/g8r_backend_lock_v0_2.json"


def records(n: int = 14) -> list[dict[str, object]]:
    return [{
        "representation_id": f"R{index:04d}", "comparability_domain_id": "D0",
        "ordering_semantics": "STATIC", "missingness": {},
        "structural_raw": {"x": format(index / 100, ".4f"), "y": format((index * 7 % 23) / 100, ".4f")},
    } for index in range(n)]


def random_matrix(n: int, seed: int) -> DistanceMatrix:
    rng = random.Random(seed)
    ids = [f"F{index:02d}" for index in range(n)]
    choices = ("0", "0.05", "0.10", "0.15", "0.20", "0.25", "0.5", "1")
    return DistanceMatrix.from_pairs(ids, {f"{a}|{b}": rng.choice(choices) for a, b in combinations(ids, 2)})


class SRFDIG8RWP5IntegratedQATests(unittest.TestCase):
    def test_pair_index_bijection_and_large_boundary(self) -> None:
        for n in range(2, 129):
            for k in range(exact_pair_count(n)):
                i, j = index_to_pair(k, n)
                self.assertEqual(k, pair_to_index(i, j, n))
        n = 100_000
        total = exact_pair_count(n)
        for k in (0, 1, n - 2, total // 2, total - 2, total - 1):
            i, j = index_to_pair(k, n)
            self.assertEqual(k, pair_to_index(i, j, n))

    def test_exact_coefficient_8_16_and_precision_boundaries(self) -> None:
        for value, places in (("0", 12), ("1.234567890123", 12), ("-0.000000000001", 12)):
            coefficient = decimal_to_coefficient(value, places)
            expected = format(Decimal(value), f".{places}f")
            self.assertEqual(expected, coefficient_to_decimal(coefficient, places))
        self.assertEqual(8, coefficient_width((-(2**63), 2**63 - 1)))
        self.assertEqual(16, coefficient_width((-(2**63) - 1, 2**63)))
        with self.assertRaisesRegex(DistanceSurfaceError, "G8R_SURFACE_NOT_QUANTIZED"):
            decimal_to_coefficient("0.0001", 3)
        with self.assertRaisesRegex(DistanceSurfaceError, "G8R_SURFACE_COEFFICIENT_OVERFLOW"):
            coefficient_width((2**127,))

    def test_distance_worker_order_and_input_order_are_exact(self) -> None:
        base, shuffled = records(16), list(reversed(records(16)))
        for method in ("L1_TYPED", "L2_TYPED"):
            spec = DistanceSpec(f"WP5.{method}", method, ("x", "y"), weights={"x": "2", "y": "1"}, precision_places=8)
            self.assertTrue(exact_equivalence(base, spec))
            one = deterministic_parallel_tiles(base, spec, tile_pair_count=17, worker_count=1)
            two = deterministic_parallel_tiles(shuffled, spec, tile_pair_count=17, worker_count=2)
            four = deterministic_parallel_tiles(base, spec, tile_pair_count=17, worker_count=4)
            self.assertEqual(one, two)
            self.assertEqual(one, four)

    def test_tile_relocation_atomicity_and_corruption_quarantine(self) -> None:
        header = TileHeader("1", "big", 8, 4, "p", "d", "s", 0, 4, 4)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a" / "tile.bin"
            receipt = write_exact_tile(first, header, (1, 2, 3, 4)).to_dict()
            self.assertFalse(first.with_name(first.name + ".staging").exists())
            second = root / "b" / "relocated.bin"
            second.parent.mkdir(parents=True)
            shutil.move(first, second)
            read_header, values = read_exact_tile(second, receipt)
            self.assertEqual(header, read_header)
            self.assertEqual((1, 2, 3, 4), values)
            raw = bytearray(second.read_bytes()); raw[-1] ^= 1; second.write_bytes(raw)
            with self.assertRaisesRegex(DistanceSurfaceError, "QA_CACHE_CORRUPTION"):
                read_exact_tile(second, receipt)

    def test_cache_identity_corruption_and_restart_no_recompute(self) -> None:
        cache = SemanticCache(); identity = {"pair_id": "P", "distance_spec_hash": "S", "population_hash": "POP"}
        key = cache.put("POPULATION_SCOPED", identity, {"distance": "0.1"})
        self.assertEqual({"distance": "0.1"}, cache.get("POPULATION_SCOPED", identity))
        self.assertIsNone(cache.get("PAIR_LOCAL_REUSABLE", identity))
        cache.corrupt_for_fixture(key); self.assertIsNone(cache.get("POPULATION_SCOPED", identity))
        self.assertEqual("QA_CACHE_CORRUPTION", cache.quarantined[key])
        ledger = TileCompletionLedger(); ledger.register_complete("T", content_hash="abc", attempt_id="A1")
        self.assertFalse(ledger.should_compute("T", expected_hash="abc")); self.assertEqual(("A1",), ledger.attempts("T"))
        self.assertTrue(ledger.should_compute("T", expected_hash="def")); self.assertEqual("QA_CACHE_CORRUPTION", ledger.quarantined["T"])

    def test_all_family_methods_match_reference_under_adversarial_order_and_ties(self) -> None:
        for n in range(2, 10):
            for seed in range(4):
                matrix = random_matrix(n, seed)
                medoid = FamilyMethodSpec("GREEDY_LEXICOGRAPHIC_MEDOID_STAR", "WP5", radius="0.20", minimum_support=2)
                self.assertEqual(medoid_star(matrix, medoid), medoid_star_optimized(matrix, medoid))
                for linkage in ("complete", "average"):
                    spec = FamilyMethodSpec(linkage.upper() + "_LINKAGE", "WP5", radius="0.20", minimum_support=2, linkage=linkage)
                    self.assertEqual(hierarchical(matrix, spec), hierarchical_optimized(matrix, spec))
                pam = FamilyMethodSpec("BOUNDED_PAM", "WP5", k=min(2, n), minimum_support=2, max_assignment_distance="0.30", max_iterations=5)
                self.assertEqual(bounded_pam(matrix, pam), bounded_pam_optimized(matrix, pam))

    def test_scheduler_keeps_complete_scientific_dag_when_capacity_unresolved(self) -> None:
        t0 = CapacityBudget.from_values("T0", max_wall_seconds="14400", max_rss_bytes=16 * 1024**3, max_external_bytes=10 * 1024**3)
        t1 = CapacityBudget.from_values("T1", max_wall_seconds="86400", max_rss_bytes=32 * 1024**3, max_external_bytes=100 * 1024**3)
        methods = ("AVERAGE_LINKAGE", "BOUNDED_PAM", "COMPLETE_LINKAGE", "GREEDY_LEXICOGRAPHIC_MEDOID_STAR")
        contracts: list[dict[str, object]] = [{"node_id": "distance", "node_type": "DISTANCE", "dependency_ids": [], "wall_seconds": None, "peak_rss_bytes": None, "external_bytes": None, "measurement_class": "UNRESOLVED", "reusable": True}]
        contracts.extend({"node_id": f"family.{m}", "node_type": "FAMILY_METHOD", "method_id": m, "configuration_id": "C", "dependency_ids": ["distance"], "wall_seconds": "1", "peak_rss_bytes": 1, "external_bytes": 1, "measurement_class": "MEASURED", "required": True} for m in methods)
        plan = build_capacity_plan(contracts, required_method_configurations=tuple((m, "C") for m in methods), t0=t0, t1=t1)
        self.assertEqual(5, len(plan["execution_order"])); self.assertEqual(4, len(plan["blocked_nodes"]))
        self.assertEqual("PROHIBITED", plan["partial_benchmark_escape_hatch"]); self.assertEqual("NONE", plan["scientific_effect"])

    def test_backend_lock_and_authority_state_are_fail_closed(self) -> None:
        lock = json.loads(BACKEND_LOCK.read_text(encoding="utf-8"))
        self.assertEqual("ADMITTED_EQUIVALENT", lock["distance_backend"]["status"])
        self.assertEqual("ADMITTED_EQUIVALENT", lock["family_backend"]["status"])
        self.assertEqual("CANDIDATE_UNADMITTED", lock["conditional_backends"]["numpy"]["status"])
        self.assertEqual("PROHIBITED", lock["lock_rules"]["silent_backend_switch"])
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual("DENIED", state["authority"]["wp9"]); self.assertEqual("DENIED", state["authority"]["june"])
        self.assertEqual("LOCKED_UNCONSUMED", state["authority"]["validation_2025"])
        self.assertEqual("NONE", state["authority"]["method_representation_distance_family_sensitivity_promotion"])
        self.assertEqual("PRESERVE_DO_NOT_MERGE", state["pr_371"])

    def test_logical_identities_do_not_depend_on_temp_paths(self) -> None:
        payload = {"representation": "R", "distance_spec": "S", "method": "M"}
        digest = logical_sha256(payload); self.assertEqual(digest, logical_sha256(dict(payload)))
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            self.assertNotIn(left, digest); self.assertNotIn(right, digest)


if __name__ == "__main__":
    unittest.main()
