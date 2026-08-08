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
    gower_distance_matrix,
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


class SRFDIWP10ARealCapacityHarnessTests(unittest.TestCase):
    def test_frozen_c2_hashes_are_anchored_in_accepted_output_manifest(self) -> None:
        manifest = json.loads(OUTPUT_MANIFEST.read_text())
        observed: dict[str, str] = {}
        for item in manifest["outputs"]:
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
        receipt = verify_gower_batch_against_reference(records, matrix, sample_pairs=99)
        self.assertEqual("PASS", receipt["result"])
        self.assertEqual(3, receipt["checked_pairs"])
        spec = DistanceSpec(
            "CHECK",
            "GOWER_MIXED",
            ("LOCATION.value", "MOTION.value"),
        )
        self.assertEqual("0.500000000000", compute_distance(records[0], records[1], spec)["distance"])
        self.assertEqual("1.000000000000", compute_distance(records[0], records[2], spec)["distance"])

    def test_null_control_gower_domain_is_all_one(self) -> None:
        records = []
        for item in ("N1", "N2", "N3"):
            records.append(
                {
                    "representation_id": item,
                    "structural_raw": {},
                    "structural_derived": {},
                    "structural_normalized": {},
                    "comparison_only": {"null_control_token": f"UNIQUE::{item}"},
                    "missingness": [],
                    "comparability_domain_id": "NULL",
                    "ordering_semantics": "STATIC_VECTOR",
                }
            )
        matrix = gower_distance_matrix(records)
        self.assertTrue(all(value == "1.000000000000" for value in matrix.values.values()))
        self.assertEqual("PASS", verify_gower_batch_against_reference(records, matrix)["result"])

    def test_frozen_capacity_totals_remain_exact(self) -> None:
        self.assertEqual(8598, FROZEN_ELIGIBLE_COUNT)
        self.assertEqual(36, FROZEN_DOMAIN_COUNT)
        self.assertEqual(35380668, FROZEN_PAIR_COUNT)
        self.assertEqual(1944, FROZEN_FAMILY_CONFIGURATION_COUNT)
        self.assertEqual(54, FROZEN_FAMILY_CONFIGURATION_COUNT // FROZEN_DOMAIN_COUNT)


if __name__ == "__main__":
    unittest.main()
