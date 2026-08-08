from __future__ import annotations

import inspect
import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd import segmentation

ROOT = Path(__file__).resolve().parents[2]
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_2.json"
SEGMENTATION_REGISTRY = ROOT / "registries/research/srfd/segmentation_methods.yaml"
BLOCKER = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10/SRFDI_WP10_PREFLIGHT_BLOCKER.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10/SRFDI_WP10_QA_PACKET.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_4.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIWP10PreflightBlockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prereg = json.loads(PREREG.read_text())
        cls.registry_text = SEGMENTATION_REGISTRY.read_text()
        cls.blocker = json.loads(BLOCKER.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_frozen_preregistration_names_segmentation_candidates_but_no_parameter_surface(self) -> None:
        expected_ids = [
            "C2E_CAUSAL_ADAPTER",
            "RUN_CHANGE_SEGMENTATION",
            "DIRECTIONAL_CHANGE",
            "PELT_REFERENCE",
            "NULL_BOUNDARY_CONTROL",
        ]
        self.assertEqual(expected_ids, self.prereg["configuration_bounds"]["segmentation_ids"])
        self.assertNotIn("segmentation_parameter_ladders", self.prereg["configuration_bounds"])
        candidates = {item["id"]: item for item in self.prereg["segmentation_candidates"]}
        for candidate_id in expected_ids:
            self.assertIn(candidate_id, candidates)
        for candidate_id in ("RUN_CHANGE_SEGMENTATION", "DIRECTIONAL_CHANGE", "PELT_REFERENCE", "NULL_BOUNDARY_CONTROL"):
            candidate = candidates[candidate_id]
            self.assertNotIn("boundary_pack_id", candidate)
            self.assertNotIn("source_fields", candidate)
            self.assertNotIn("parameter_grid", candidate)
            self.assertNotIn("delay_policy", candidate)

    def test_fixture_segmentation_registry_does_not_materialise_execution_parameters(self) -> None:
        self.assertIn("authority_state: FIXTURE_ONLY", self.registry_text)
        for method_id in ("RUN_CHANGE_SEGMENTATION", "DIRECTIONAL_CHANGE", "PELT_REFERENCE", "NULL_BOUNDARY_CONTROL"):
            self.assertIn(method_id, self.registry_text)
        for missing_identity_field in ("boundary_pack", "source_fields", "state_field", "value_field", "threshold", "penalty", "min_length"):
            self.assertNotIn(missing_identity_field, self.registry_text)

    def test_reference_implementations_require_unfrozen_execution_parameters(self) -> None:
        run_params = inspect.signature(segmentation.segment_runs).parameters
        dc_params = inspect.signature(segmentation.directional_change).parameters
        pelt_params = inspect.signature(segmentation.pelt_reference).parameters
        self.assertIn("state_field", run_params)
        self.assertIn("value_field", dc_params)
        self.assertIn("threshold", dc_params)
        self.assertIn("penalty", pelt_params)
        self.assertIs(inspect._empty, run_params["state_field"].default)
        self.assertIs(inspect._empty, dc_params["value_field"].default)
        self.assertIs(inspect._empty, dc_params["threshold"].default)
        self.assertIs(inspect._empty, pelt_params["penalty"].default)

    def test_preflight_fails_before_any_scientific_run_consumption(self) -> None:
        self.assertEqual("BLOCKED_PRE_RUN", self.blocker["status"])
        self.assertEqual("BLOCK", self.blocker["preflight_result"])
        consumption = self.blocker["benchmark_consumption"]
        self.assertFalse(consumption["wp10_benchmark_started"])
        self.assertFalse(consumption["june_scientific_outputs_generated"])
        self.assertFalse(consumption["june_scientific_outputs_inspected"])
        self.assertFalse(consumption["distance_surface_executed"])
        self.assertFalse(consumption["family_catalog_executed"])
        self.assertFalse(consumption["segmentation_surface_executed"])
        self.assertFalse(consumption["authority_token_consumed"])
        self.assertEqual("BLOCK_PRE_RUN", self.qa["qa_result"])

    def test_programme_state_preserves_valid_but_unused_authorization(self) -> None:
        self.assertEqual("BLOCKED", self.state["status"])
        self.assertEqual("SRFDI-WP10", self.state["active_packet"])
        self.assertTrue(self.state["operator_decision_required"])
        self.assertFalse(self.state["exact_bindings"]["authority_token_consumed"])
        self.assertFalse(self.state["benchmark_consumption"]["benchmark_executed_state"])
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("DENIED", self.state["authority"]["provider_fetch"])
        self.assertEqual("NONE", self.state["authority"]["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])
        self.assertEqual("registries/implementation/srfd/OVC_SRFDI_STATE_v0_4.json", self.pointer["authoritative_state"])
        self.assertEqual("BLOCKED", self.pointer["status"])
        self.assertTrue(self.pointer["operator_decision_required"])
        self.assertFalse(self.pointer["authority_token_consumed"])


if __name__ == "__main__":
    unittest.main()
