from __future__ import annotations

import json
from pathlib import Path
import unittest

from srfd._current_pointer_compat import assert_lawful_v10_pointer

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp11"
SCORECARD = BASE / "SRFDI_WP11_SCIENTIFIC_SCORECARD.json"
FAILURE = BASE / "SRFDI_WP11_FAILURE_ATTRIBUTION.json"
QA = BASE / "SRFDI_WP11_QA_PACKET.json"
G11 = BASE / "SRFDI_WP11_G11_DECISION_PACKET.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_53_WP11_G11_GATE_READY.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
RUN = "SRFD.RUN.55601cfe14d85173c767315be04c8b6c333dc8c07103a8064733086c26606dbf"


class SRFDIWP11G11GateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = json.loads(SCORECARD.read_text())
        cls.failure = json.loads(FAILURE.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.g11 = json.loads(G11.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_exact_june_denominators_and_controls_are_visible(self):
        d = self.score["denominators"]
        self.assertEqual(9420, d["source_records"])
        self.assertEqual(8598, d["eligible_records"])
        self.assertEqual(36, d["comparability_domains"])
        self.assertEqual(35380668, d["exact_pair_opportunities"])
        self.assertEqual(1944, d["family_configurations"])
        self.assertEqual(2020, d["work_units"])
        f = self.score["family_evidence"]
        self.assertEqual(1619, f["family_evidence_configurations"])
        self.assertEqual(325, f["no_stable_family_configurations"])
        self.assertEqual(324, f["null_control_configuration_count"])
        self.assertEqual(324, f["null_control_no_stable_family_count"])
        self.assertEqual("PASS_324_OF_324_NO_STABLE_FAMILY", self.score["counterexample_and_negative_evidence"]["null_control_behavior"])

    def test_method_dependence_and_invariant_core_evidence_are_not_hidden(self):
        s = self.score["stability"]
        self.assertEqual(249507, s["cross_method_and_sensitivity_survival_numerator"])
        self.assertEqual(475686, s["cross_method_and_sensitivity_survival_denominator"])
        self.assertEqual("DESCRIPTIVE_JUNE_FAMILY_TEMPORAL_SPAN_ONLY_NOT_INDEPENDENT_LONG_HORIZON_STABILITY", s["chronology_interpretation"])
        c = self.score["invariant_core_and_disagreement"]
        self.assertEqual(298, c["invariant_core_count"])
        self.assertEqual(30, c["core_bearing_domains"])
        self.assertEqual(6, c["zero_core_domains"])
        self.assertEqual(1, c["unanimous_54_of_54_core_count"])
        self.assertEqual(38461, c["method_disagreement_count"])
        self.assertEqual(30, c["domains_with_method_disagreement"])

    def test_failure_attribution_preserves_unexecuted_surfaces(self):
        self.assertEqual("COMPLETE_FAILURE_ATTRIBUTION_WITH_LAWFUL_UNRESOLVED_SURFACES", self.failure["status"])
        self.assertEqual([], self.failure["implementation_failures"])
        self.assertEqual([], self.failure["reproducibility_failures"])
        surfaces = {x["surface"] for x in self.failure["scientific_surface_gaps"]}
        for expected in {
            "REPRESENTATION_SRFDI-R2_C2E_AGGREGATE",
            "REPRESENTATION_SRFDI-R3_ORDERED_TRANSITIONS",
            "REPRESENTATION_SRFDI-R4_NORMALIZED_PATH",
            "REPRESENTATION_SRFDI-R5_HYBRID",
            "REPRESENTATION_SRFDI-R7_CONTEXT_VARIANTS",
            "SEGMENTATION_C2E_CAUSAL_ADAPTER",
            "SEGMENTATION_DIRECTIONAL_CHANGE",
            "SEGMENTATION_PELT_REFERENCE",
            "DISTANCE_L1_TYPED",
            "DISTANCE_L2_TYPED",
            "DISTANCE_DTW_SEQUENCE",
        }:
            self.assertIn(expected, surfaces)

    def test_all_ten_decomposed_g11_decisions_use_allowed_vocabularies(self):
        decisions = self.g11["decomposed_scientific_decisions"]
        self.assertEqual(10, len(decisions))
        expected = {
            "REPRESENTATION": "UNRESOLVED",
            "C2E_EPISODE_UNIT": "UNRESOLVED",
            "DISTANCE_MODEL": "UNRESOLVED",
            "GREEDY_MEDOID_STAR": "RETAIN_BENCHMARK",
            "ALTERNATIVE_FAMILY_METHOD": "BENCHMARK_ONLY",
            "FAMILY_STRUCTURE": "METHOD_DEPENDENT_ONLY",
            "SENSITIVITY_AND_HIERARCHY": "UNRESOLVED",
            "INVARIANT_CORE": "PARTIALLY_SUPPORTED",
            "UPPER_LAYER_CONFORMANCE_PROGRAMME": "DEFER",
            "LONG_HORIZON_DISCOVERY_READINESS": "NOT_READY",
        }
        self.assertEqual(set(expected), set(decisions))
        for key, recommendation in expected.items():
            self.assertEqual(recommendation, decisions[key]["recommendation"])
            self.assertIn(recommendation, decisions[key]["allowed"])

    def test_g11_is_operator_required_scientific_record_only(self):
        self.assertEqual(RUN, self.g11["run_id"])
        self.assertEqual("PASS", self.g11["recommended_decision"])
        self.assertEqual("SCIENTIFIC_DISPOSITION_RECORD_ONLY", self.g11["authority"]["proposed_delta"])
        self.assertTrue(self.g11["operator_required"])
        self.assertEqual("PASS_TO_PRESENT_G11", self.qa["qa_result"])
        self.assertTrue(self.qa["operator_decision_required"])
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertEqual("OPERATOR_REQUIRED_SCIENTIFIC_DISPOSITION", self.state["stop_condition"])
        self.assertIsNone(self.state["decision_record"])
        self.assertIsNone(self.state["next_packet"])
        self.assertTrue(assert_lawful_v10_pointer(self, self.pointer))

    def test_all_reserved_firewalls_remain_closed(self):
        for source in (self.score["firewalls"], self.failure["firewalls"], self.state["authority"]):
            self.assertEqual("DENIED", source["provider_fetch"])
            self.assertEqual("LOCKED_UNCONSUMED", source["validation_2025"])
            self.assertEqual("NONE", source["active_selector_or_replacement"])
            self.assertEqual("NONE", source["method_or_family_promotion"])
            self.assertEqual("NONE", source["c2e_activation"])
            self.assertEqual("NONE", source["semantic_promotion"])
            self.assertEqual("NONE", source["canonical_r2_publication"])
            self.assertEqual("NONE", source["probability_risk_exposure_execution"])
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])


if __name__ == "__main__":
    unittest.main()
