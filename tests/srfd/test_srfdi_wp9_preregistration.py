from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.schema import validate_document
from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_1.json"
HASH_RECEIPT = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_WP9_PREREGISTRATION_HASH_RECEIPT.json"
MANIFEST = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFD_JUNE_RUN_MANIFEST_TEMPLATE_v0_1.json"
DEP_CAPACITY = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_WP9_DEPENDENCY_CAPACITY_STATE.json"
G8_MERGE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g8-represented/SRFDI_G8_REPRESENTED_MERGE_RECEIPT.json"
G9_DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_G9_OPERATOR_DECISION.json"
G9_MERGE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_G9_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_1.json"


class SRFDIWP9PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prereg_bytes = PREREG.read_bytes()
        cls.prereg = json.loads(cls.prereg_bytes)
        cls.hash_receipt = json.loads(HASH_RECEIPT.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.dep_capacity = json.loads(DEP_CAPACITY.read_text())
        cls.g8_merge = json.loads(G8_MERGE.read_text())
        cls.g9_decision = json.loads(G9_DECISION.read_text())
        cls.g9_merge = json.loads(G9_MERGE.read_text())
        cls.state = json.loads(STATE.read_text())

    def test_preregistration_schema_and_exact_hashes_remain_unchanged(self) -> None:
        validate_document(self.prereg, "SRFDPreregistration")
        byte_hash = sha256(self.prereg_bytes).hexdigest()
        logical_hash = logical_sha256(self.prereg)
        self.assertEqual("76a18f79596772343f398256582dab9c37e219d01345c606204230c554599792", byte_hash)
        self.assertEqual("a832daad99b6df49199eced0c35632b15974f86b58a8e6481350294a87d3d32e", logical_hash)
        self.assertEqual(byte_hash, self.hash_receipt["byte_sha256"])
        self.assertEqual(logical_hash, self.hash_receipt["logical_sha256"])
        self.assertEqual(byte_hash, self.g9_decision["preregistration"]["byte_sha256"])
        self.assertEqual(logical_hash, self.g9_decision["preregistration"]["logical_sha256"])
        self.assertEqual(byte_hash, self.g9_merge["preregistration"]["byte_sha256"])
        self.assertEqual(logical_hash, self.g9_merge["preregistration"]["logical_sha256"])

    def test_candidate_grid_is_exact_predeclared_and_dependency_bounded(self) -> None:
        bounds = self.prereg["configuration_bounds"]
        self.assertEqual([f"SRFDI-R{i}" for i in range(1, 10)], bounds["representation_ids"])
        self.assertEqual(
            ["C2E_CAUSAL_ADAPTER", "RUN_CHANGE_SEGMENTATION", "DIRECTIONAL_CHANGE", "PELT_REFERENCE", "NULL_BOUNDARY_CONTROL"],
            bounds["segmentation_ids"],
        )
        self.assertEqual(["L1_TYPED", "L2_TYPED", "GOWER_MIXED", "DTW_SEQUENCE"], bounds["distance_ids"])
        self.assertEqual(
            ["GREEDY_LEXICOGRAPHIC_MEDOID_STAR", "COMPLETE_LINKAGE", "AVERAGE_LINKAGE", "BOUNDED_PAM"],
            bounds["family_method_ids"],
        )
        self.assertEqual(["0.04", "0.08", "0.16"], bounds["family_parameter_ladders"]["medoid_star_radius"])
        self.assertEqual([2, 4, 8], bounds["family_parameter_ladders"]["shared_minimum_support"])
        self.assertEqual([], self.dep_capacity["dependency_state"]["new_dependencies_added_by_wp9"])
        self.assertEqual("CANDIDATE_UNADMITTED", self.dep_capacity["dependency_state"]["numpy"])

    def test_strong_family_rule_is_frozen_non_composite_and_not_full_assignment(self) -> None:
        rule = self.prereg["family_strength_rules"]["strong_family_evidence"]
        self.assertEqual("SUPPORT_NUMERATOR_EQUALS_SUPPORT_DENOMINATOR", rule["core_support_rule"])
        self.assertEqual(3, rule["minimum_distinct_qualifying_configurations"])
        self.assertEqual(2, rule["minimum_distinct_enabled_family_methods"])
        self.assertFalse(rule["full_assignment_required"])
        self.assertTrue(rule["residual_visibility_required"])
        self.assertTrue(rule["ambiguity_visibility_required"])
        self.assertEqual("FORBIDDEN", self.prereg["family_strength_rules"]["global_composite_score"])
        self.assertEqual("FORBIDDEN", self.prereg["post_result_choices"])

    def test_population_is_procedure_only_and_8598_is_not_adopted(self) -> None:
        population = self.prereg["eligible_population"]
        self.assertEqual("PROCEDURE_FROZEN_COUNT_NOT_BOUND", population["binding_state"])
        reference = population["existing_metadata_reference"]
        self.assertEqual("NON_BINDING_CAPACITY_AND_COVERAGE_REFERENCE_ONLY", reference["binding"])
        self.assertEqual(8598, reference["target_c2_state_count_reference"])
        joined = " ".join(population["binding_procedure"])
        self.assertIn("not adopted as the eligible population", joined)
        self.assertEqual("DENIED", self.manifest["run_authority"])

    def test_capacity_and_manifest_keep_june_and_validation_denied(self) -> None:
        capacity = self.prereg["capacity_limits"]
        self.assertEqual(14400, capacity["max_wall_seconds"])
        self.assertEqual(17179869184, capacity["max_peak_rss_bytes"])
        self.assertEqual(10737418240, capacity["max_external_bytes"])
        self.assertFalse(capacity["parallel_speedup_credit"])
        self.assertFalse(capacity["cache_reuse_credit"])
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.manifest["run_authority_gate"])
        self.assertEqual("LOCKED_UNCONSUMED", self.manifest["validation_2025"])
        self.assertEqual("FORBIDDEN", self.manifest["required_before_run_authority"]["source"]["provider_fetch"])

    def test_completed_g8_and_g9_lifecycle_are_preserved_through_g9s_supersession(self) -> None:
        self.assertEqual("0f3ae4379978a1381f479cfe1c5fe9c269981c19", self.g8_merge["merge_commit"])
        self.assertEqual("FREEZE_MEASURED_CAPACITY", self.g8_merge["decision"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.g9_decision["decision"])
        self.assertEqual("d56986b90796b5547bc2b5d17146e6c7b62f43cf", self.g9_merge["merge_commit"])
        wp9 = next(p for p in self.state["packets"] if p["packet_id"] == "SRFDI-WP9")
        self.assertEqual("COMPLETED", wp9["status"])
        self.assertEqual(self.g9_merge["merge_commit"], wp9["merge_commit"])
        self.assertEqual("SRFDI-WP9S", self.state["active_packet"])
        self.assertEqual("SRFDI-G9S-FREEZE", self.state["current_gate"])
        self.assertEqual("READY", self.state["status"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertTrue(self.state["authority"]["june"].startswith("DENIED"))
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("APPROVED_BOUNDED_SRFDI_WP9S_ONLY", self.state["authority"]["preregistration_supersession"])
        self.assertEqual("FROZEN_HISTORICAL_SUPERSEDED_FOR_EXECUTION", self.state["g9_disposition"]["status"])

    def test_required_outputs_and_stop_conditions_are_explicit(self) -> None:
        self.assertIn("ARTIFACT_MANIFEST_AND_HASH_TABLE", self.prereg["required_output_tables"])
        self.assertIn("POST_RESULT_CONFIGURATION_OR_THRESHOLD_CHANGE", self.prereg["stop_conditions"])
        self.assertIn("UNAUTHORISED_JUNE_EXECUTION_ATTEMPT", self.prereg["stop_conditions"])
        self.assertIn("PROVIDER_FETCH_ATTEMPT", self.prereg["stop_conditions"])
        self.assertIn("VALIDATION_2025_READ_ATTEMPT", self.prereg["stop_conditions"])


if __name__ == "__main__":
    unittest.main()
