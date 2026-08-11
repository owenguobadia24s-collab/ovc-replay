from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp11"
GATE = BASE / "SRFDI_WP11_G11_DECISION_PACKET.json"
DECISION = BASE / "SRFDI_G11_OPERATOR_DECISION_PASS.json"
GATE_READY_STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_53_WP11_G11_GATE_READY.json"
APPROVED_STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_54_WP11_G11_APPROVED_PENDING_MERGE.json"
RUN = "SRFD.RUN.55601cfe14d85173c767315be04c8b6c333dc8c07103a8064733086c26606dbf"


class SRFDIG11OperatorDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = json.loads(GATE.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.gate_ready = json.loads(GATE_READY_STATE.read_text())
        cls.approved = json.loads(APPROVED_STATE.read_text())

    def test_operator_pass_is_exact_and_preserves_gate_candidate(self):
        self.assertEqual("OVC APPROVE SRFDI-G11 PASS", self.decision["operator_command"])
        self.assertEqual("PASS", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("SRFDI-G11", self.decision["gate_id"])
        self.assertEqual("GATE_READY", self.gate_ready["status"])
        self.assertEqual("PASS", self.gate["recommended_decision"])
        self.assertEqual(RUN, self.decision["run_id"])

    def test_all_ten_recommended_dispositions_are_accepted_exactly(self):
        expected = {key: value["recommendation"] for key, value in self.gate["decomposed_scientific_decisions"].items()}
        self.assertEqual(10, len(expected))
        self.assertEqual(expected, self.decision["accepted_decomposed_scientific_dispositions"])
        self.assertEqual(expected, self.approved["accepted_decomposed_scientific_dispositions"])

    def test_pass_is_record_only_and_grants_no_activation_or_promotion(self):
        delta = self.decision["authority_delta"]
        self.assertEqual("APPROVED_RECORD_ONLY", delta["scientific_disposition_record"])
        for key in (
            "active_selector_or_replacement",
            "method_or_family_promotion",
            "c2e_activation",
            "semantic_promotion",
            "canonical_r2_publication",
            "probability_risk_exposure_execution",
        ):
            self.assertEqual("NONE", delta[key])
        self.assertEqual("DENIED", delta["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", delta["validation_2025"])

    def test_approved_state_routes_only_to_merge_closeout(self):
        self.assertEqual("APPROVED", self.approved["status"])
        self.assertFalse(self.approved["operator_decision_required"])
        self.assertEqual("PASS", self.approved["operator_decision"])
        self.assertEqual("SRFDI-G11-MERGE-CLOSEOUT", self.approved["next_packet"])
        self.assertIsNone(self.approved["merge_commit"])
        self.assertEqual([], self.approved["blockers"])
        self.assertEqual("NONE_PENDING_FINAL_HEAD_ASSURANCE_OR_BLOCKER", self.approved["stop_condition"])

    def test_unresolved_scientific_surfaces_remain_unresolved(self):
        accepted = self.approved["accepted_decomposed_scientific_dispositions"]
        self.assertEqual("UNRESOLVED", accepted["REPRESENTATION"])
        self.assertEqual("UNRESOLVED", accepted["C2E_EPISODE_UNIT"])
        self.assertEqual("UNRESOLVED", accepted["DISTANCE_MODEL"])
        self.assertEqual("UNRESOLVED", accepted["SENSITIVITY_AND_HIERARCHY"])
        self.assertEqual("NOT_READY", accepted["LONG_HORIZON_DISCOVERY_READINESS"])
        self.assertEqual("DEFER", accepted["UPPER_LAYER_CONFORMANCE_PROGRAMME"])


if __name__ == "__main__":
    unittest.main()
