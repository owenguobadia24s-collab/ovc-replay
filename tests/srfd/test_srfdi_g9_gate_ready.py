from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_G9_OPERATOR_PACKET.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_WP9_QA_PACKET.json"
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_G9_OPERATOR_DECISION.json"
MERGE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_G9_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_1.json"


class SRFDIG9GateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = json.loads(GATE.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.decision = json.loads(DECISION.read_text()) if DECISION.exists() else None
        cls.merge = json.loads(MERGE.read_text()) if MERGE.exists() else None
        cls.state = json.loads(STATE.read_text())

    def test_historical_gate_identity_and_decision_surface_are_immutable(self) -> None:
        self.assertEqual("SRFDI-G9", self.gate["gate_id"])
        self.assertEqual("OPERATOR_ACKNOWLEDGEMENT", self.gate["gate_class"])
        self.assertEqual("GATE_READY", self.gate["status"])
        self.assertEqual(["PREREGISTRATION_FREEZE", "ADJUST", "DEFER"], self.gate["allowed_decisions"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.gate["recommended_decision"])
        self.assertEqual("OVC APPROVE SRFDI-G9 PREREGISTRATION_FREEZE", self.gate["exact_operator_command"])

    def test_historical_g9_qa_remains_pass_without_june_or_scientific_authority(self) -> None:
        self.assertEqual("PASS", self.qa["qa_result"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.qa["qa_recommendation"])
        self.assertEqual([], self.qa["unresolved_issues"])
        self.assertEqual("DENIED_PENDING_SRFDI_G_JUNE_AUTH", self.qa["authority_check"]["june"])
        self.assertEqual("LOCKED_UNCONSUMED", self.qa["authority_check"]["validation_2025"])
        self.assertEqual("NONE", self.qa["authority_check"]["scientific_promotion"])
        self.assertEqual("NONE", self.qa["authority_check"]["selector"])

    def test_completed_g9_is_preserved_when_later_corrective_gate_is_active(self) -> None:
        self.assertIsNotNone(self.decision)
        self.assertIsNotNone(self.merge)
        self.assertEqual("PREREGISTRATION_FREEZE", self.decision["decision"])
        self.assertEqual("OVC APPROVE SRFDI-G9 PREREGISTRATION_FREEZE", self.decision["operator_command"])
        self.assertEqual("d56986b90796b5547bc2b5d17146e6c7b62f43cf", self.merge["merge_commit"])
        wp9 = next(p for p in self.state["packets"] if p["packet_id"] == "SRFDI-WP9")
        self.assertEqual("COMPLETED", wp9["status"])
        self.assertEqual(self.merge["merge_commit"], wp9["merge_commit"])
        self.assertEqual("PREREGISTRATION_FREEZE", wp9["decision"])
        self.assertEqual("docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_G9_OPERATOR_DECISION.json", wp9["decision_record"])
        self.assertIn("FROZEN_REPRESENTATION_PACK_FIELD_MAPPING_NOT_MATERIALISED", wp9["blockers"])

    def test_later_state_does_not_retroactively_grant_june(self) -> None:
        self.assertEqual("SRFDI-G9S-FREEZE", self.state["current_gate"])
        self.assertEqual("SRFDI-WP9S", self.state["active_packet"])
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertTrue(self.state["operator_decision_required"])
        self.assertTrue(self.state["authority"]["june"].startswith("DENIED"))
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("WP9S_IMPLEMENTED_CANDIDATE_GATE_READY", self.state["authority"]["preregistration_supersession"])
        self.assertEqual("SRFDI-G9S-FREEZE", self.state["stop_at"])
        self.assertEqual("FROZEN_HISTORICAL_SUPERSEDED_FOR_EXECUTION", self.state["g9_disposition"]["status"])
        wp9s = next(p for p in self.state["packets"] if p["packet_id"] == "SRFDI-WP9S")
        self.assertEqual("GATE_READY", wp9s["status"])

    def test_gate_keeps_population_unbound_and_june_separate(self) -> None:
        summary = self.gate["frozen_protocol_summary"]
        self.assertEqual("PROCEDURE_FROZEN_COUNT_NOT_BOUND", summary["population_binding"])
        self.assertEqual("NON_BINDING_CAPACITY_AND_COVERAGE_REFERENCE_ONLY", summary["historical_8598_reference"])
        self.assertEqual("NONE", self.gate["proposed_authority_delta"]["june_execution_effect"])
        self.assertIn("SRFDI-G-JUNE-AUTH", " ".join(self.gate["exact_work_after_approval"]))
        self.assertEqual("UNBOUND_PENDING_SRFDI_G_JUNE_AUTH", self.decision["population_binding"]["exact_population"])
        self.assertEqual("DENIED_PENDING_SRFDI_G_JUNE_AUTH_AUTHORIZE_JUNE", self.decision["authority_effect"]["june_execution"])


if __name__ == "__main__":
    unittest.main()
