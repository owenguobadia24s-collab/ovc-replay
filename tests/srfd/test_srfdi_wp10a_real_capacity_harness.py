from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.distance import DistanceSpec, compute_distance
from ovc.opt_b.srfd.real_source_packs import compile_real_source_representation
from ovc.opt_b.srfd.wp10a_real_capacity import (
    FROZEN_C2_FILE_SHA256,
    FROZEN_DOMAIN_COUNT,
    FROZEN_ELIGIBLE_COUNT,
    FROZEN_FAMILY_CONFIGURATION_COUNT,
    FROZEN_PAIR_COUNT,
    _capacity_adapted_record,
    execute_domain_family_grid,
    gower_distance_matrix,
    gower_pattern_surface,
    verify_gower_batch_against_reference,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_MANIFEST = ROOT / "docs/releases/pattern-discovery-v0-3/pd-june-full-month-mdr/wp2-replay/output-manifest.json"
PACK_REGISTRY = ROOT / "registries/research/srfd/real_source_representation_packs_v0_2.json"


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


def c2_row() -> dict[str, object]:
    axes = {
        name: {"status": "EVALUATED", "value": value, "reason_code": None}
        for name, value in {
            "LOCATION": "MID",
            "MOTION": "UP",
            "ORGANISATION": "ORDERED",
            "INTERACTION": "NONE",
            "QUALITY": "GOOD",
        }.items()
    }
    return {
        "active_c2_model_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        "axes": axes,
        "c1_manifest_id": "C1.MANIFEST",
        "c1_release_id": "C1.RELEASE",
        "c2_state_id": "C2.TEST",
        "clock": "15M",
        "container_ids": [],
        "continuity": "CONTIGUOUS",
        "eligibility_class": "TARGET_JUNE",
        "evaluation_scope_id": "15M-LOCAL",
        "first_valid_time": "2026-06-01T00:15:00Z",
        "level_ids": [],
        "live_prospective_append": "DENIED",
        "operation_mode": "TIME_GATED_REPLAY",
        "opt_a_manifest_id": "A.MANIFEST",
        "opt_a_release_id": "A.RELEASE",
        "parameter_pack_id": "C2.PARAM",
        "parent_c1_record_id": "C1.TEST",
        "parent_opt_a_bar_id": "A.BAR",
        "persistence": {},
        "relation_set_id": "REL.SET",
        "release_membership": False,
        "role": "DISCOVERY",
        "side": "BID",
        "source_slice_id": "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1",
        "target_eligible": True,
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

    def test_capacity_adapter_preserves_v02_envelope_and_compiles_r1(self) -> None:
        adapted = _capacity_adapted_record(c2_row())
        self.assertEqual("SCHEMA_PRESERVING_NO_REPRESENTATION_FIELD_SELECTION", adapted["adapter_semantics"])
        self.assertEqual("SRFDI-SOURCE-ADAPTER-v0.2", adapted["adapter_id"])
        self.assertEqual("MIXED_TYPED_C2", adapted["units"])
        self.assertEqual("EVALUABLE", adapted["computability_status"])
        self.assertEqual("PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9", adapted["source_lineage"]["source_release_id"])
        registry = json.loads(PACK_REGISTRY.read_text())
        compiled = compile_real_source_representation(
            adapted,
            registry,
            "SRFDI-R1",
            source_population_id="SRFD.TEST.POP",
        )
        self.assertEqual("SRFDI-R1", compiled["implementation_class_id"])
        self.assertEqual(adapted["source_lineage"], compiled["source_lineage"])

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
