from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.wp10_preflight import WP10PreflightError, validate_frozen_stability_metric_rules

ROOT = Path(__file__).resolve().parents[2]
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_3.json"
BASE_PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_2.json"
BLOCKER = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-3/SRFDI_WP10_V03_PREFLIGHT_BLOCKER.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-3/SRFDI_WP10_V03_PREFLIGHT_QA_PACKET.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_7.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIWP10V03PreflightBlockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prereg = json.loads(PREREG.read_text())
        cls.base_prereg = json.loads(BASE_PREREG.read_text())
        cls.blocker = json.loads(BLOCKER.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_frozen_preregistration_fails_closed_on_missing_metric_rule_specs(self) -> None:
        with self.assertRaises(WP10PreflightError) as caught:
            validate_frozen_stability_metric_rules(self.prereg, base_preregistration=self.base_prereg)
        self.assertEqual("WP10_STABILITY_METRIC_RULE_UNBOUND", caught.exception.reason_code)
        self.assertIn("stability_metrics", self.base_prereg)
        self.assertNotIn("stability_metric_specs", self.base_prereg)
        self.assertEqual("SEGMENTATION_EXECUTION_SPECIFICATION_ONLY", self.prereg["supersession"]["supersession_scope"])

    def test_block_occurs_before_any_scientific_execution_or_token_consumption(self) -> None:
        self.assertEqual("BLOCKED_PRE_RUN", self.blocker["status"])
        self.assertFalse(self.blocker["authority"]["token_consumed"])
        execution = self.blocker["scientific_execution"]
        self.assertFalse(execution["token_consumed"])
        self.assertFalse(execution["segmentation_executed"])
        self.assertFalse(execution["representation_grid_executed"])
        self.assertFalse(execution["distance_grid_executed"])
        self.assertFalse(execution["family_grid_executed"])
        self.assertFalse(execution["sensitivity_or_stability_results_generated"])
        self.assertFalse(execution["g10_generated"])
        self.assertFalse(execution["wp11_generated"])

    def test_source_and_authority_preflight_passed_without_provider_or_validation(self) -> None:
        passed = self.blocker["preflight_passed"]
        self.assertTrue(passed["source_file_hashes_match_accepted_output_manifest"])
        self.assertEqual(10, passed["bound_c1_c2_file_count"])
        self.assertFalse(passed["provider_fetch_performed"])
        self.assertEqual("LOCKED_UNCONSUMED", passed["validation_2025"])
        self.assertFalse(passed["benchmark_scientific_outputs_generated"])
        self.assertEqual("148cf9c6958ffc737a3b5fd1800c48c1544bf34e835a97c884e77d4b49904067", self.blocker["authority"]["manifest_binding_sha256"])

    def test_qa_requires_versioned_preregistration_supersession(self) -> None:
        self.assertEqual("BLOCK", self.qa["qa_result"])
        self.assertEqual("WP10_STABILITY_METRIC_RULE_UNBOUND", self.qa["reason_code"])
        self.assertEqual("FAIL", self.qa["acceptance"]["frozen_executable_stability_metric_rule_specs"])
        self.assertEqual("BLOCK_PRE_RUN_AND_REQUIRE_VERSIONED_PREREGISTRATION_SUPERSESSION", self.qa["recommended_disposition"])

    def test_authoritative_candidate_state_preserves_unused_authority_and_firewalls(self) -> None:
        self.assertEqual("BLOCKED_PRE_RUN", self.state["status"])
        self.assertEqual("SRFDI-WP10-v0.3", self.state["active_packet"])
        self.assertTrue(self.state["operator_decision_required"])
        self.assertFalse(self.state["exact_bindings"]["authority_token_consumed"])
        self.assertEqual("DENIED", self.state["authority"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("NONE", self.state["authority"]["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])
        self.assertEqual("registries/implementation/srfd/OVC_SRFDI_STATE_v0_7.json", self.pointer["authoritative_state"])
        self.assertEqual("BLOCKED_PRE_RUN", self.pointer["status"])
        self.assertTrue(self.pointer["operator_decision_required"])
        self.assertFalse(self.pointer["authority_token_consumed"])


if __name__ == "__main__":
    unittest.main()
