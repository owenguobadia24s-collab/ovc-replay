from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.real_source_packs import RealSourcePackError, compile_real_source_representation, find_pack
from ovc.opt_b.srfd.schema import validate_document
from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registries/research/srfd/real_source_representation_packs_v0_2.json"
V1 = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_1.json"
V2 = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_2.json"
RECEIPT = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9s/SRFDI_WP9S_PREREGISTRATION_HASH_RECEIPT.json"
MANIFEST = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9s/SRFD_JUNE_RUN_MANIFEST_TEMPLATE_v0_2.json"
DEPENDENCY = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9s/SRFDI_WP9S_DEPENDENCY_STATE.json"
FIXTURES = ROOT / "fixtures/srfd/wp9s/real_source_pack_cases_v0_2.json"


class WP9SPreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry_bytes = REGISTRY.read_bytes(); cls.registry = json.loads(cls.registry_bytes)
        cls.v1_bytes = V1.read_bytes(); cls.v1 = json.loads(cls.v1_bytes)
        cls.v2_bytes = V2.read_bytes(); cls.v2 = json.loads(cls.v2_bytes)
        cls.receipt = json.loads(RECEIPT.read_text()); cls.manifest = json.loads(MANIFEST.read_text())
        cls.dependency = json.loads(DEPENDENCY.read_text()); cls.fixtures = json.loads(FIXTURES.read_text())
        cls.full = deepcopy(next(x["record"] for x in cls.fixtures["records"] if x["case_id"] == "FULLY_EVALUATED"))
        cls.missing = deepcopy(next(x["record"] for x in cls.fixtures["records"] if x["case_id"] == "MOTION_NOT_EVALUATED"))

    def test_historical_v1_and_new_candidate_hashes(self) -> None:
        self.assertEqual("76a18f79596772343f398256582dab9c37e219d01345c606204230c554599792", sha256(self.v1_bytes).hexdigest())
        self.assertEqual("a832daad99b6df49199eced0c35632b15974f86b58a8e6481350294a87d3d32e", logical_sha256(self.v1))
        validate_document(self.v2, "SRFDPreregistration")
        self.assertEqual(self.receipt["preregistration"]["byte_sha256"], sha256(self.v2_bytes).hexdigest())
        self.assertEqual(self.receipt["preregistration"]["logical_sha256"], logical_sha256(self.v2))
        self.assertEqual(self.receipt["representation_pack_registry"]["byte_sha256"], sha256(self.registry_bytes).hexdigest())
        self.assertEqual(self.receipt["representation_pack_registry"]["logical_sha256"], logical_sha256(self.registry))

    def test_all_nine_pack_dispositions_are_exact(self) -> None:
        packs = {p["id"]: p for p in self.registry["packs"]}
        self.assertEqual({f"SRFDI-R{i}" for i in range(1, 10)}, set(packs))
        for pid in ("SRFDI-R1", "SRFDI-R6", "SRFDI-R8", "SRFDI-R9"):
            self.assertEqual("AVAILABLE_PREBENCHMARK", packs[pid]["status"])
            self.assertEqual(["GOWER_MIXED"], packs[pid]["allowed_distance_ids"])
        expected = {
            "SRFDI-R2":"C2E_REAL_SOURCE_DEPENDENCY_UNAVAILABLE",
            "SRFDI-R3":"TYPED_MULTICHANNEL_SEQUENCE_DISTANCE_UNAVAILABLE",
            "SRFDI-R4":"PREBENCHMARK_NORMALIZATION_FIT_ARTIFACT_UNAVAILABLE",
            "SRFDI-R5":"C2E_AND_TYPED_SEQUENCE_DEPENDENCIES_UNAVAILABLE",
            "SRFDI-R7":"FROZEN_PARENT_CONTEXT_SOURCE_UNAVAILABLE",
        }
        for pid, reason in expected.items():
            self.assertEqual("DEPENDENCY_UNAVAILABLE", packs[pid]["status"])
            self.assertEqual(reason, packs[pid]["reason_code"])
            self.assertEqual([], packs[pid]["allowed_distance_ids"])

    def test_available_pack_compilation_and_missingness(self) -> None:
        raw = compile_real_source_representation(self.full, self.registry, "SRFDI-R1", source_population_id="SYN.POP")
        self.assertEqual({f"{a}.value" for a in ("LOCATION","MOTION","ORGANISATION","INTERACTION","QUALITY")}, set(raw["structural_raw"]))
        with self.assertRaisesRegex(RealSourcePackError, "REP_REQUIRED_DIMENSION_MISSING"):
            compile_real_source_representation(self.missing, self.registry, "SRFDI-R1", source_population_id="SYN.POP")
        miss = compile_real_source_representation(self.missing, self.registry, "SRFDI-R8", source_population_id="SYN.POP")
        self.assertEqual("MISSING::NOT_EVALUATED::NO_CONTIGUOUS_PRIOR_STATE", miss["structural_raw"]["MOTION.token"])
        null = compile_real_source_representation(self.full, self.registry, "SRFDI-R9", source_population_id="SYN.POP")
        self.assertEqual({}, null["structural_raw"]); self.assertTrue(null["comparison_only"]["null_control_token"].startswith("SRFD.NULL."))

    def test_ablation_is_predeclared_and_unavailable_packs_fail_closed(self) -> None:
        r6 = find_pack(self.registry, "SRFDI-R6")
        self.assertEqual(5, len(r6["variants"]))
        out = compile_real_source_representation(self.missing, self.registry, "SRFDI-R6", source_population_id="SYN.POP", variant_id="SRFDI-R6-DROP-MOTION")
        self.assertNotIn("MOTION.value", out["structural_raw"]); self.assertEqual(["MOTION.value"], out["structural_derived"]["ablation_fields"])
        with self.assertRaisesRegex(RealSourcePackError, "REP_VARIANT_REQUIRED"):
            compile_real_source_representation(self.full, self.registry, "SRFDI-R6", source_population_id="SYN.POP")
        for pid in ("SRFDI-R2","SRFDI-R3","SRFDI-R4","SRFDI-R5","SRFDI-R7"):
            with self.assertRaises(RealSourcePackError):
                compile_real_source_representation(self.full, self.registry, pid, source_population_id="SYN.POP")

    def test_population_normalization_and_authority_firewalls(self) -> None:
        ep = self.v2["eligible_population"]
        self.assertEqual("PARENT_C1_OPEN_TIME_PLUS_SOURCE_LINEAGE_AUTHORITY_AND_FIVE_AXIS_SCHEMA_ONLY", ep["population_membership_rule"])
        self.assertEqual("APPLIED_AFTER_POPULATION_BINDING_CANNOT_CHANGE_MEMBERSHIP", ep["representation_computability_rule"])
        r4 = find_pack(self.registry, "SRFDI-R4")["normalization"]
        self.assertEqual("MINMAX_V0_1", r4["estimator"]); self.assertEqual("UNBOUND_PREBENCHMARK_NON_TARGET", r4["fit_population_id"])
        self.assertEqual("FORBIDDEN", self.v2["configuration_bounds"]["normalization_policy"]["benchmark_target_fit"])
        self.assertEqual("DENIED_PENDING_SRFDI_G9S_FREEZE_AND_SRFDI_G_JUNE_AUTH", self.v2["authority_firewalls"]["june_benchmark"])
        self.assertEqual("LOCKED_UNCONSUMED", self.v2["authority_firewalls"]["validation_2025"])

    def test_only_synthetic_schema_fixtures_were_used_and_manifest_is_inert(self) -> None:
        self.assertEqual("SYNTHETIC_SCHEMA_FIXTURE_ONLY", self.fixtures["authority_state"])
        self.assertNotIn("2026-06-", FIXTURES.read_text())
        self.assertEqual(0, self.dependency["market_records_read_during_pack_design"])
        self.assertEqual(0, self.dependency["validation_records_read"]); self.assertEqual(0, self.dependency["provider_fetches"])
        self.assertEqual("DENIED", self.manifest["run_authority"])
        self.assertEqual("SRFDI-G9S-FREEZE", self.manifest["prerequisite_gate"])
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.manifest["run_authority_gate"])
        self.assertEqual("FORBIDDEN", self.manifest["required_before_run_authority"]["source"]["provider_fetch"])

    def test_compilation_is_deterministic_and_lineage_preserved(self) -> None:
        a = compile_real_source_representation(self.full, self.registry, "SRFDI-R1", source_population_id="SYN.POP")
        b = compile_real_source_representation(deepcopy(self.full), self.registry, "SRFDI-R1", source_population_id="SYN.POP")
        self.assertEqual(a, b); self.assertEqual(self.full["source_lineage"], a["source_lineage"])
        self.assertEqual("CANDIDATE_NOT_FROZEN", a["authority_state"])


if __name__ == "__main__":
    unittest.main()
