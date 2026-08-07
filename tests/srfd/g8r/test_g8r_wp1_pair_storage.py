from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from ovc.opt_b.srfd.distance import DistanceSpec
from ovc.opt_b.srfd.distance_surface import (
    DistanceSurfaceError,
    TileHeader,
    coefficient_to_decimal,
    coefficient_width,
    compact_pair_coefficients,
    decimal_to_coefficient,
    radius_adjacency_exact,
    radius_bounded_distance_exact,
    read_exact_tile,
    reconstruct_logical_pairs,
    write_exact_tile,
)
from ovc.opt_b.srfd.pair_index import (
    PairIndexError,
    canonical_ids,
    exact_pair_count,
    index_to_pair,
    iter_pairs,
    pair_ranges,
    pair_to_index,
)
from ovc.opt_b.srfd.serialization import logical_sha256


class G8RWP1PairIndexTests(unittest.TestCase):
    def test_exhaustive_bijection_n_0_to_128(self) -> None:
        for n in range(129):
            seen: set[tuple[int, int]] = set()
            for k in range(exact_pair_count(n)):
                i, j = index_to_pair(k, n)
                self.assertEqual(k, pair_to_index(i, j, n))
                self.assertLess(i, j)
                seen.add((i, j))
            self.assertEqual(exact_pair_count(n), len(seen))

    def test_large_n_boundaries_and_tiles_are_exact(self) -> None:
        n = 100_000
        total = exact_pair_count(n)
        self.assertEqual((0, 1), index_to_pair(0, n))
        self.assertEqual((n - 2, n - 1), index_to_pair(total - 1, n))
        ranges = pair_ranges(513, tile_pair_count=1024)
        self.assertEqual(0, ranges[0].k_start)
        self.assertEqual(exact_pair_count(513), ranges[-1].k_end)
        self.assertEqual(exact_pair_count(513), sum(item.count for item in ranges))
        flat = [k for item in ranges for k, _, _ in iter_pairs(513, item)]
        self.assertEqual(list(range(exact_pair_count(513))), flat)

    def test_duplicate_ids_fail_closed(self) -> None:
        with self.assertRaises(PairIndexError) as raised:
            canonical_ids(["A", "A"])
        self.assertEqual("G8R_PAIR_DUPLICATE_ID", raised.exception.reason_code)


class G8RWP1DistanceSurfaceTests(unittest.TestCase):
    @staticmethod
    def records() -> list[dict[str, object]]:
        values = ["0.1000", "0.1500", "0.4000", "0.9000"]
        return [
            {
                "representation_id": f"R{index}",
                "comparability_domain_id": "D0",
                "ordering_semantics": "STATIC",
                "missingness": {},
                "structural_raw": {"x": value},
            }
            for index, value in enumerate(values)
        ]

    def setUp(self) -> None:
        self.spec = DistanceSpec("G8R.L1", "L1_TYPED", ("x",), precision_places=4)

    def test_fixed_point_round_trip_and_width_guards(self) -> None:
        coefficient = decimal_to_coefficient("0.1250", 4)
        self.assertEqual(1250, coefficient)
        self.assertEqual("0.1250", coefficient_to_decimal(coefficient, 4))
        self.assertEqual(8, coefficient_width([-(2**63), 2**63 - 1]))
        self.assertEqual(16, coefficient_width([2**63]))
        with self.assertRaises(DistanceSurfaceError):
            coefficient_width([2**127])

    def test_compact_reconstruction_matches_reference_logic(self) -> None:
        records = self.records()
        coefficients, reference = compact_pair_coefficients(records, self.spec)
        reconstructed = reconstruct_logical_pairs(records, self.spec, coefficients)
        self.assertEqual(len(reference), len(reconstructed))
        for expected, actual in zip(reference, reconstructed):
            self.assertEqual(expected["pair_id"], actual["pair_id"])
            self.assertEqual(expected["distance"], actual["distance"])
            self.assertTrue(actual["exact"])

    def test_tile_atomic_round_trip_relocation_and_corruption_detection(self) -> None:
        records = self.records()
        coefficients, _ = compact_pair_coefficients(records, self.spec)
        width = coefficient_width(coefficients)
        header = TileHeader(
            format_version="G8R.TILE.v1",
            endian="big",
            coefficient_width=width,
            precision_places=self.spec.precision_places,
            population_hash=logical_sha256([item["representation_id"] for item in records]),
            domain_hash=logical_sha256("D0"),
            distance_spec_hash=self.spec.logical_hash,
            k_start=0,
            k_end=len(coefficients),
            expected_count=len(coefficients),
        )
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "a" / "tile.bin"
            receipt = write_exact_tile(path, header, coefficients)
            self.assertEqual("COMPLETE", receipt.status)
            loaded_header, loaded = read_exact_tile(path, receipt.to_dict())
            self.assertEqual(asdict(header), asdict(loaded_header))
            self.assertEqual(coefficients, loaded)
            relocated = Path(root) / "b" / "renamed.bin"
            relocated.parent.mkdir()
            path.replace(relocated)
            _, loaded_again = read_exact_tile(relocated, receipt.to_dict())
            self.assertEqual(coefficients, loaded_again)
            raw = bytearray(relocated.read_bytes())
            raw[-1] ^= 1
            relocated.write_bytes(raw)
            with self.assertRaises(DistanceSurfaceError) as raised:
                read_exact_tile(relocated, receipt.to_dict())
            self.assertEqual("QA_CACHE_CORRUPTION", raised.exception.reason_code)

    def test_radius_surfaces_are_exact_and_explicitly_not_generic(self) -> None:
        _, logical = compact_pair_coefficients(self.records(), self.spec)
        adjacency = radius_adjacency_exact(logical, radius="0.3000", configuration_id="CFG.R030")
        bounded = radius_bounded_distance_exact(logical, r_max="0.3000", configuration_id="CFG.R030")
        expected = sorted(item["pair_id"] for item in logical if item["distance"] <= "0.3000")
        self.assertEqual(expected, adjacency["edge_pair_ids"])
        self.assertEqual(expected, sorted(item["pair_id"] for item in bounded["retained"]))
        self.assertEqual("DISTANCE_GREATER_THAN_RADIUS", adjacency["absence_semantics"])
        self.assertFalse(bounded["generic_all_distance_surface"])

    def test_not_comparable_never_becomes_compact_distance(self) -> None:
        records = self.records()
        records[1]["comparability_domain_id"] = "OTHER"
        with self.assertRaises(DistanceSurfaceError) as raised:
            compact_pair_coefficients(records, self.spec)
        self.assertEqual("G8R_SURFACE_NOT_COMPARABLE", raised.exception.reason_code)


if __name__ == "__main__":
    unittest.main()
