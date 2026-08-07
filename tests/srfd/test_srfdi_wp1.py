from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.schema import SRFDValidationError, VALID_OBJECT_TYPES, validate_document
from ovc.opt_b.srfd.serialization import canonical_json_bytes, logical_sha256, stable_id

ROOT = Path(__file__).resolve().parents[2]


class SRFDIWP1Tests(unittest.TestCase):
    def test_schema_bundle_declares_all_durable_objects(self) -> None:
        schema = json.loads((ROOT / "schemas/opt_b/srfd/srfd_object_bundle_v0_1.schema.json").read_text())
        self.assertEqual(set(VALID_OBJECT_TYPES), set(schema["properties"]["object_type"]["enum"]))

    def test_valid_representation_spec_and_namespace_contract(self) -> None:
        document = {
            "object_type": "SRFDRepresentationSpec",
            "schema_version": "0.1",
            "authority_state": "FIXTURE_ONLY",
            "representation_pack_id": "REP.FX.1",
            "implementation_class_id": "SRFDI-R1",
            "lawful_inputs": ["C2.fixture"],
            "output_schema": {"namespaces": {"structural_raw": {"x": "decimal"}}},
            "missingness_policy": "EXPLICIT",
            "comparability_domain_id": "FIXTURE_SAME_DOMAIN_v0_1",
            "ordering_semantics": "STATIC_VECTOR",
            "canonical_serialization": "SORTED_KEYS_FIXED_DECIMAL_EXPLICIT_NULLS",
            "prohibited_interpretation": ["semantic_family", "prediction"],
        }
        validate_document(document)
        invalid = {**document, "output_schema": {"namespaces": {"hidden_semantics": {}}}}
        with self.assertRaisesRegex(SRFDValidationError, "QA_SCHEMA_FAILURE"):
            validate_document(invalid)

    def test_reserved_authority_and_outcome_fields_fail_closed(self) -> None:
        base = {"object_type": "SRFDDecisionPacket", "schema_version": "0.1", "authority_state": "ACTIVE"}
        with self.assertRaisesRegex(SRFDValidationError, "AUTH_SCOPE_EXPANSION"):
            validate_document(base)
        leaked = {"object_type": "SRFDDecisionPacket", "schema_version": "0.1", "authority_state": "FIXTURE_ONLY", "outcome": "UP"}
        with self.assertRaisesRegex(SRFDValidationError, "AUTH_SCOPE_EXPANSION"):
            validate_document(leaked)

    def test_preregistration_requires_pre_run_decision_fields(self) -> None:
        required = {
            "object_type": "SRFDPreregistration", "schema_version": "0.1", "authority_state": "FIXTURE_ONLY",
            "research_questions": [], "hypotheses": [], "falsifiers": [], "eligible_population": {},
            "representation_candidates": [], "segmentation_candidates": [], "distance_candidates": [],
            "family_method_candidates": [], "configuration_bounds": {}, "stability_metrics": [],
            "family_strength_rules": {}, "invariant_core_rules": {}, "ambiguity_rules": {},
            "residual_rules": {}, "failure_attribution_order": [], "capacity_limits": {},
            "stop_conditions": [], "required_output_tables": [], "operator_decision_surfaces": [],
        }
        validate_document(required)
        broken = dict(required)
        broken.pop("falsifiers")
        with self.assertRaisesRegex(SRFDValidationError, "QA_SCHEMA_FAILURE"):
            validate_document(broken)

    def test_canonical_identity_is_key_order_machine_path_and_worker_independent(self) -> None:
        left = {"b": Decimal("1.2300"), "a": datetime(2026, 8, 7, tzinfo=timezone.utc), "worker_id": "A", "local_path": "/tmp/a"}
        right = {"local_path": "C:/other", "a": datetime(2026, 8, 7, tzinfo=timezone.utc), "worker_id": "B", "b": Decimal("1.23")}
        self.assertEqual(stable_id("SRFD.FX.", left), stable_id("SRFD.FX.", right))
        self.assertEqual(canonical_json_bytes({"x": 1, "y": 2}), canonical_json_bytes({"y": 2, "x": 1}))
        self.assertEqual(logical_sha256({"x": None}), logical_sha256({"x": None}))

    def test_representation_registry_has_exact_implementation_classes_and_crosswalks(self) -> None:
        text = (ROOT / "registries/research/srfd/representations.yaml").read_text()
        for index in range(1, 10):
            self.assertEqual(1, text.count(f"implementation_class_id: SRFDI-R{index}\n"))
        for architecture_id in ("R0", "R3", "R4", "R6", "R7", "R8"):
            self.assertIn(f"architecture_candidate_id: {architecture_id}", text)

    def test_conditional_dependencies_are_disabled_by_default(self) -> None:
        text = (ROOT / "registries/research/srfd/family_methods.yaml").read_text()
        for method in ("HDBSCAN", "OPTICS", "MATRIX_PROFILE"):
            self.assertIn(f"id: {method}", text)
        self.assertEqual(3, text.count("enabled: false"))
        self.assertIn("BASELINE_SHADOW_BENCHMARK_ONLY", text)

    def test_contracts_preserve_fixture_only_authority(self) -> None:
        contract_root = ROOT / "contracts/opt_b/srfd"
        files = sorted(contract_root.glob("*.yaml"))
        self.assertEqual(6, len(files))
        for path in files:
            text = path.read_text()
            self.assertIn("authority_state: FIXTURE_ONLY", text, path.name)
            self.assertNotIn("canonical: true", text.lower())


if __name__ == "__main__":
    unittest.main()
