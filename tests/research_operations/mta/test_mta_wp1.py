from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from ovc.research_operations.mta.registry import (
    RegistryValidationError,
    classify_attempt,
    load_registry_bundle,
    validate_amendment,
    validate_registry_bundle,
)

ROOT = Path(__file__).resolve().parents[3]


def load(relative: str) -> dict:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(relative)
    return value


class MTAWP1RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = load_registry_bundle(ROOT)
        cls.fixtures = load("fixtures/research_operations/mta/MTA_WP1_REGISTRY_FIXTURES_v0_1.json")

    def test_validator_script_passes(self) -> None:
        path = ROOT / "scripts/research_operations/validate_mta_wp1.py"
        spec = importlib.util.spec_from_file_location("validate_mta_wp1", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.main(), 0)

    def test_registry_bundle_is_complete_and_deterministic(self) -> None:
        first = validate_registry_bundle(self.bundle)
        second = validate_registry_bundle(load_registry_bundle(ROOT))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["entry_counts"]["MARKER_FUNCTION"], 8)
        self.assertEqual(first["entry_counts"]["COMPUTABILITY_STATUS"], 11)

    def test_every_marker_is_audit_only(self) -> None:
        markers = self.bundle["MARKER_FUNCTION"]["entries"]
        self.assertEqual({item["name"] for item in markers}, {
            "BOUNDARY_ZONE_ENTRY",
            "BREACH_ACTIVE",
            "RETURN_INSIDE",
            "COMPRESSION_TO_DISPLACEMENT",
            "LONG_PERSISTENCE",
            "REPEATED_SWITCHING",
            "LOCAL_PARENT_CONFLICT",
            "ALIGNMENT_GAINED",
        })
        for marker in markers:
            self.assertEqual(marker["authority"]["semantic_promotion"], "DENIED")
            self.assertEqual(marker["authority"]["selector_or_release_mutation"], "DENIED")
            self.assertIn(marker["functional_class"], {
                "STATE_CHANGE",
                "LEVEL_INTERACTION",
                "PERSISTENCE",
                "SEQUENCE_INSTABILITY",
                "CROSS_SCALE_CONTEXT",
            })

    def test_non_evaluable_is_never_silently_not_fired(self) -> None:
        for attempt in self.fixtures["valid_attempts"]:
            result = classify_attempt(
                self.bundle,
                status=attempt["status"],
                reason_code=attempt["reason_code"],
            )
            self.assertEqual(result["status"], attempt["status"])
        with self.assertRaisesRegex(RegistryValidationError, "EVALUATED_ATTEMPT_HAS_REASON"):
            classify_attempt(
                self.bundle,
                status="EVALUATED_NOT_FIRED",
                reason_code="LOCATION_NOT_EVALUABLE",
            )

    def test_status_reason_family_must_match(self) -> None:
        with self.assertRaisesRegex(RegistryValidationError, "STATUS_REASON_MISMATCH"):
            classify_attempt(
                self.bundle,
                status="NOT_EVALUABLE_PARENT_MISSING",
                reason_code="MOTION_NOT_EVALUABLE",
            )

    def test_material_amendment_requires_ack_and_rerun(self) -> None:
        valid = self.fixtures["valid_amendment"]
        self.assertTrue(validate_amendment(valid)["material"])
        no_ack = copy.deepcopy(valid)
        no_ack["operator_acknowledgement_required"] = False
        with self.assertRaisesRegex(RegistryValidationError, "MATERIAL_AMENDMENT_WITHOUT_OPERATOR_ACK"):
            validate_amendment(no_ack)
        no_rerun = copy.deepcopy(valid)
        no_rerun["rerun_required"] = False
        with self.assertRaisesRegex(RegistryValidationError, "MATERIAL_AMENDMENT_WITHOUT_RERUN"):
            validate_amendment(no_rerun)

    def test_metric_denominators_are_explicit(self) -> None:
        for metric in self.bundle["METRIC"]["entries"]:
            if metric["unit"] == "COUNT":
                self.assertEqual(metric["zero_denominator"], "ZERO")
            else:
                self.assertTrue(metric["denominator"])
                self.assertEqual(metric["zero_denominator"], "NOT_EVALUABLE")

    def test_ro4_and_deferred_layers_are_not_promoted(self) -> None:
        flow = {entry["name"]: entry for entry in self.bundle["FLOW_OBJECT"]["entries"]}
        self.assertEqual(flow["RO4 sequence window"]["status"], "REFERENCE_ONLY")
        self.assertEqual(flow["RO4 friction record"]["status"], "REFERENCE_ONLY")
        self.assertEqual(flow["OPT-B.C2E episode"]["status"], "DEFERRED")
        self.assertEqual(flow["OPT-B.C2.5 event"]["status"], "PROHIBITED")
        self.assertEqual(flow["OPT-B.C3 structural meaning"]["status"], "PROHIBITED")

    def test_duplicate_registry_entry_is_rejected(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["MARKER_FUNCTION"]["entries"].append(copy.deepcopy(bundle["MARKER_FUNCTION"]["entries"][0]))
        with self.assertRaisesRegex(RegistryValidationError, "DUPLICATE_ENTRY_ID"):
            validate_registry_bundle(bundle)

    def test_semantic_promotion_is_rejected(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["MARKER_FUNCTION"]["entries"][0]["authority"]["semantic_promotion"] = "ALLOWED"
        with self.assertRaisesRegex(RegistryValidationError, "SEMANTIC_PROMOTION_NOT_DENIED"):
            validate_registry_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
