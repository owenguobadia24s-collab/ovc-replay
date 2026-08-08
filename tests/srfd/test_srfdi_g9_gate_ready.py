from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_G9_OPERATOR_PACKET.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_WP9_QA_PACKET.json"
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_G9_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_1.json"


class SRFDIG9GateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = json.loads(GATE.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.decision = json.loads(DECISION.read_text()) if DECISION.exists() else None
        cls.state = json.loads(STATE.read_text())

    def test_gate_is_one_operator_acknowledgement_with_exact_decisions(self) -> None:
        self.assertEqual("SRFDI-G9", self.gate["gate_id"])
        self.assertEqual("OPERATOR_ACKNOWLEDGEMENT", self.gate["gate_class"])
        self.assertEqual("GATE_READY", self.gate["status"])
        self.assertEqual(["PREREGISTRATION_FREEZE", "ADJUST", "DEFER"], self.gate["allowed_decisions"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.gate["recommended_decision"])
        self.assertEqual("OVC APPROVE SRFDI-G9 PREREGISTRATION_FREEZE", self.gate["exact_operator_command"])

    def test_qa_passes_without_june_or_scientific_authority(self) -> None:
        self.assertEqual("PASS", self.qa["qa_result"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.qa["qa_recommendation"])
        self.assertEqual([], self.qa["unresolved_issues"])
        self.assertEqual("DENIED_PENDING_SRFDI_G_JUNE_AUTH", self.qa["authority_check"]["june"])
        self.assertEqual("LOCKED_UNCONSUMED", self.qa["authority_check"]["validation_2025"])
        self.assertEqual("NONE", self.qa["authority_check"]["scientific_promotion"])
        self.assertEqual("NONE", self.qa["authority_check"]["selector"])

    def test_state_stops_at_g9_until_explicit_decision_then_routes_only_to_june_auth_packet(self) -> None:
        self.assertEqual("SRFDI-WP9", self.state["active_packet"])
        self.assertEqual("SRFDI-G9", self.state["current_gate"])
        self.assertEqual("DENIED_PENDING_SRFDI_G_JUNE_AUTH", self.state["authority"]["june"])
        wp9 = next(p for p in self.state["packets"] if p["packet_id"] == "SRFDI-WP9")

        if self.decision is None:
            self.assertEqual("GATE_READY", self.state["status"])
            self.assertTrue(self.state["operator_decision_required"])
            self.assertEqual("GATE_READY", wp9["status"])
            self.assertIsNone(wp9["decision_record"])
            self.assertIsNone(wp9["merge_commit"])
            self.assertIn("SRFDI_G9_PREREGISTRATION_ACKNOWLEDGEMENT_REQUIRED_BEFORE_FREEZE", wp9["blockers"])
            return

        self.assertEqual("PREREGISTRATION_FREEZE", self.decision["decision"])
        self.assertEqual("OVC APPROVE SRFDI-G9 PREREGISTRATION_FREEZE", self.decision["operator_command"])
        self.assertEqual("APPROVED", self.state["status"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual("FROZEN_EXACT_VERSION", self.state["authority"]["preregistration"])
        self.assertEqual("APPROVED", wp9["status"])
        self.assertEqual("PREREGISTRATION_FREEZE", wp9["decision"])
        self.assertEqual(
            "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_G9_OPERATOR_DECISION.json",
            wp9["decision_record"],
        )
        self.assertIsNone(wp9["merge_commit"])
        self.assertNotIn("SRFDI_G9_PREREGISTRATION_ACKNOWLEDGEMENT_REQUIRED_BEFORE_FREEZE", wp9["blockers"])
        self.assertIn("JUNE_BENCHMARK_DENIED_PENDING_SRFDI_G_JUNE_AUTH", wp9["blockers"])
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.state["stop_at"])

    def test_gate_keeps_population_unbound_and_june_separate(self) -> None:
        summary = self.gate["frozen_protocol_summary"]
        self.assertEqual("PROCEDURE_FROZEN_COUNT_NOT_BOUND", summary["population_binding"])
        self.assertEqual("NON_BINDING_CAPACITY_AND_COVERAGE_REFERENCE_ONLY", summary["historical_8598_reference"])
        self.assertEqual("NONE", self.gate["proposed_authority_delta"]["june_execution_effect"])
        self.assertIn("SRFDI-G-JUNE-AUTH", " ".join(self.gate["exact_work_after_approval"]))
        if self.decision is not None:
            self.assertEqual("UNBOUND_PENDING_SRFDI_G_JUNE_AUTH", self.decision["population_binding"]["exact_population"])
            self.assertEqual(
                "DENIED_PENDING_SRFDI_G_JUNE_AUTH_AUTHORIZE_JUNE",
                self.decision["authority_effect"]["june_execution"],
            )


if __name__ == "__main__":
    unittest.main()
