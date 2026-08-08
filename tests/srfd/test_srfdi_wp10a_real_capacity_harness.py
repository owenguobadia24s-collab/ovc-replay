from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.distance import DistanceSpec, compute_distance
from ovc.opt_b.srfd.wp10a_real_capacity import (
    FROZEN_C2_FILE_SHA256,
    FROZEN_DOMAIN_COUNT,
    FROZEN_ELIGIBLE_COUNT,
    FROZEN_FAMILY_CONFIGURATION_COUNT,
    FROZEN_PAIR_COUNT,
    execute_domain_family_grid,
    gower_distance_matrix,
    gower_pattern_surface,
    verify_gower_batch_against_reference,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_MANIFEST = ROOT / "docs/releases/pattern-discovery-v0-3/pd-june-full-month-mdr/wp2-replay/output-manifest.json"


def record(record_id: str, values: dict[str, str], *, domain: str = "D") -> dict[str, object]:
    return {
        "representation_id": record_id,
        "structural_raw": values,
        "structural_derived": {},
        "structural_normalized": {},
        "comparison_only": {},
        "missingness": [],
        "comparability_domain_id": domain,
        "ordering_semantics": "STATIC_VECTOR",
    }


def null_record(record_id: str) -> dict[str, object]:
    return {
        "representation_id": record_id,
        "structural_raw": {},
        "structural_derived": {},
        "structural_normalized": {},
        "comparison_only": {"null_control_token": f"UNIQUE::{record_id}"},
        "missingness": [],
        "comparability_domain_id": "NULL",
        "ordering_semantics": "STATIC_VECTOR",
    }


class SRFDIWP10ARealCapacityHarnessTests(unittest.TestCase):
    def test_frozen_c2_hashes_are_anchored_in_accepted_output_manifest(self) -> None:
        manifest = json.loads(OUTPUT_MANIFEST.read_text())
        observed: dict[str, str] = {}
        for item in manifest["files"]:
            path = item["path"]
            if "/c2/states/" not in path:
                continue
            if "15M/ASK/GBPUSD-15M-LOCAL" in path:
                observed["C2_15M_ASK_LOCAL"] = item["sha256"]
            elif "15M/ASK/GBPUSD-15M-WITH-2H-PARENT" in path:
                observed["C2_15M_ASK_PARENT"] = item["sha256"]
            elif "15M/BID/GBPUSD-15M-LOCAL" in path:
                observed["C2_15M_BID_LOCAL"] = item["sha256"]
            elif "15M/BID/GBPUSD-15M-WITH-2H-PARENT" in path:
                observed["C2_15M_BID_PARENT"] = item["sha256"]
            elif "2H_A_L/ASK/GBPUSD-2H-A-L-LOCAL" in path:
                observed["C2_2H_ASK_LOCAL"] = item["sha256"]
            elif "2H_A_L/BID/GBPUSD-2H-A-L-LOCAL" in path:
                observed["C2_2H_BID_LOCAL"] = item["sha256"]
        self.assertEqual(FROZEN_C2_FILE_SHA256, observed)

    def test_direct_gower_batch_is_exactly_reference_equivalent(self) -> None:
        records = [
            record("A", {"LOCATION.value": "LOW", "MOTION.value": "UP"}),
            record("B", {"LOCATION.value": "LOW", "MOTION.value": "DOWN"}),
            record("C", {"LOCATION.value": "HIGH", "MOTION.value": "DOWN"}),
        ]
        matrix = gower_distance_matrix(records)
        surface = gower_pattern_surface(records)
        receipt = verify_gower_batch_against_reference(records, surface, sample_pairs=99)
        self.assertEqual("PASS", receipt["result"])
        self.assertEqual(3, receipt["checked_pairs"])
        self.assertEqual(matrix.ids, surface.ids)
        for left in matrix.ids:
            for right in matrix.ids:
                self.assertEqual(matrix.distance(left, right), surface.distance(left, right))
        spec = DistanceSpec(
            "CHECK",
            "GOWER_MIXED",
            ("LOCATION.value", "MOTION.value"),
        )
        self.assertEqual("0.500000000000", compute_distance(records[0], records[1], spec)["distance"])
        self.assertEqual("1.000000000000", compute_distance(records[0], records[2], spec)["distance"])

    def test_null_control_gower_domain_is_all_one(self) -> None:
        records = [null_record(item) for item in ("N1", "N2", "N3")]
        matrix = gower_distance_matrix(records)
        surface = gower_pattern_surface(records)
        self.assertTrue(all(value == "1.000000000000" for value in matrix.values.values()))
        self.assertEqual("PASS", verify_gower_batch_against_reference(records, surface)["result"])

    def test_domain_receipt_is_full_grid_and_catalog_hash_is_repeatable(self) -> None:
        records = [
            record(f"R{index:02d}", {"A": str(index % 3), "B": str((index // 2) % 2)})
            for index in range(12)
        ]
        first = execute_domain_family_grid("REPEAT", records)
        second = execute_domain_family_grid("REPEAT", list(reversed(records)))
        self.assertEqual(54, first["configuration_count"])
        self.assertEqual(66, first["pair_count"])
        self.assertEqual(first["catalog_hashes_sha256"], second["catalog_hashes_sha256"])
        self.assertEqual(first["unique_pattern_count"], second["unique_pattern_count"])
        self.assertFalse(first["null_control_fast_path"])

    def test_null_domain_uses_exact_all_residual_fast_path(self) -> None:
        records = [null_record(f"N{index:02d}") for index in range(12)]
        receipt = execute_domain_family_grid("NULL-FAST", records)
        self.assertEqual(54, receipt["configuration_count"])
        self.assertEqual(66, receipt["pair_count"])
        self.assertEqual(12, receipt["unique_pattern_count"])
        self.assertTrue(receipt["null_control_fast_path"])

    def test_frozen_capacity_totals_remain_exact(self) -> None:
        self.assertEqual(8598, FROZEN_ELIGIBLE_COUNT)
        self.assertEqual(36, FROZEN_DOMAIN_COUNT)
        self.assertEqual(35380668, FROZEN_PAIR_COUNT)
        self.assertEqual(1944, FROZEN_FAMILY_CONFIGURATION_COUNT)
        self.assertEqual(54, FROZEN_FAMILY_CONFIGURATION_COUNT // FROZEN_DOMAIN_COUNT)


if __name__ == "__main__":
    unittest.main()
