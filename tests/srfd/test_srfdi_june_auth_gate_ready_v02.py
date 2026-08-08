from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd import june_authority_v02
from ovc.opt_b.srfd.june_authority import JuneAuthorityError

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1"
MANIFEST = BASE / "srfdi-june-auth/SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v0_2.json"
BINDING = BASE / "srfdi-june-auth/SRFD_JUNE_SOURCE_POPULATION_BINDING_v0_2.json"
FREEZE_RECEIPT = BASE / "srfdi-wp9s/SRFDI_G9S_FREEZE_MERGE_RECEIPT.json"
WP2D_RECEIPT = BASE / "srfdi-wp2d/SRFDI_WP2D_MERGE_RECEIPT.json"


class SRFDIJuneAuthGateReadyV02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.binding = json.loads(BINDING.read_text())
        cls.freeze = json.loads(FREEZE_RECEIPT.read_text())
        cls.wp2d = json.loads(WP2D_RECEIPT.read_text())

    def test_prerequisite_freeze_and_corrective_merge_are_exact(self) -> None:
        self.assertEqual("f3b6c011ef2b7975340d0696025cd2da9b24b50e", self.freeze["merge_commit"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.freeze["decision"])
        self.assertEqual("fca974ef48e4178be299bf65e520e2268e8b67c3", self.wp2d["merge_commit"])
        self.assertEqual("PASS", self.wp2d["decision"])

    def test_manifest_candidate_is_exact_inert_and_operator_reserved(self) -> None:
        self.assertEqual(june_authority_v02.MANIFEST_SCHEMA, self.manifest["schema"])
        self.assertEqual(june_authority_v02.PENDING_RUN_STATE, self.manifest["run_authority"])
        self.assertEqual(june_authority_v02.GATE_ID, self.manifest["run_authority_gate"])
        self.assertNotIn("authority_binding", self.manifest)
        self.assertEqual(
            "2a0d3c529ea5aca6a1d8c67adc29d3f6dd55a3efcd75992661a69e205cea010c",
            june_authority_v02.manifest_binding_sha256(self.manifest),
        )
        with self.assertRaisesRegex(JuneAuthorityError, "operator decision is required"):
            june_authority_v02.verify_june_run_authority(
                None,
                self.manifest,
                expected_implementation_commit="fca974ef48e4178be299bf65e520e2268e8b67c3",
            )

    def test_exact_source_and_population_binding_are_frozen(self) -> None:
        source = self.manifest["source_binding"]
        population = self.manifest["population_binding"]
        self.assertEqual("PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9", source["source_release_id"])
        self.assertEqual("4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7", source["source_binding_sha256"])
        self.assertEqual("FORBIDDEN", source["provider_fetch"])
        self.assertEqual("FORBIDDEN", source["upstream_mutation"])
        self.assertEqual("SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd", population["population_id"])
        self.assertEqual(9420, population["source_record_count"])
        self.assertEqual(8598, population["eligible_record_count"])
        self.assertEqual("fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e", population["eligible_record_ids_sha256"])
        self.assertEqual(822, population["context_record_count"])
        self.assertEqual(0, population["exclusion_count"])
        self.assertEqual({"EVALUABLE": 4996, "NOT_EVALUATED": 3602}, population["computability_counts_within_eligible_population"])
        self.assertEqual("MATCHED_EXACT_COUNT_AND_ID_HASH_NOW_BOUND", population["historical_8598_reference"])
        self.assertEqual(source, self.binding["source_binding"])
        self.assertEqual(population, self.binding["population_binding"])

    def test_frozen_v02_preregistration_pack_registry_and_capacity_are_unchanged(self) -> None:
        self.assertEqual(june_authority_v02.PREREG_BYTE_SHA256, self.manifest["preregistration_byte_sha256"])
        self.assertEqual(june_authority_v02.PREREG_LOGICAL_SHA256, self.manifest["preregistration_logical_sha256"])
        self.assertEqual(june_authority_v02.PREREG_FREEZE_GATE, self.manifest["prerequisite_gate"])
        self.assertEqual(june_authority_v02.PACK_REGISTRY_BYTE_SHA256, self.manifest["representation_pack_registry"]["byte_sha256"])
        self.assertEqual(june_authority_v02.PACK_REGISTRY_LOGICAL_SHA256, self.manifest["representation_pack_registry"]["logical_sha256"])
        self.assertEqual(["SRFDI-R1", "SRFDI-R6", "SRFDI-R8", "SRFDI-R9"], self.manifest["available_representation_ids"])
        self.assertEqual(["SRFDI-R2", "SRFDI-R3", "SRFDI-R4", "SRFDI-R5", "SRFDI-R7"], self.manifest["dependency_unavailable_representation_ids"])
        self.assertEqual(14400, self.manifest["capacity_binding"]["max_wall_seconds"])
        self.assertTrue(self.manifest["capacity_binding"]["stop_on_capacity_exceeded"])

    def test_all_reserved_authority_remains_denied_before_gate_decision(self) -> None:
        self.assertEqual("LOCKED_UNCONSUMED", self.manifest["validation_2025"])
        self.assertEqual("NONE", self.manifest["selector_change"])
        self.assertEqual("NONE", self.manifest["scientific_promotion"])
        self.assertEqual("NONE", self.manifest["publication"])
        self.assertEqual("NONE", self.manifest["probability_risk_exposure_execution"])
        self.assertEqual("fca974ef48e4178be299bf65e520e2268e8b67c3", self.manifest["implementation_commit"])
        self.assertEqual("88ad3ec673493cb82b6b6d4fda90c077535e88d9f630a0535d56df887944ae3f", self.manifest["dependency_manifest_hash"])


if __name__ == "__main__":
    unittest.main()
