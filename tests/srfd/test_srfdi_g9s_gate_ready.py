from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g9s/SRFDI_G9S_OPERATOR_PACKET.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g9s/SRFDI_G9S_QA_PACKET.json"
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g9s/SRFDI_G9S_OPERATOR_DECISION.json"
GAP = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp2c/SRFDI_WP2C_REPRESENTATION_PACK_GAP_AUDIT.json"
WP2C_MERGE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp2c/SRFDI_WP2C_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_1.json"


class SRFDIG9SSupersessionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = json.loads(PACKET.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.gap = json.loads(GAP.read_text())
        cls.wp2c_merge = json.loads(WP2C_MERGE.read_text())
        cls.state = json.loads(STATE.read_text())

    def test_gate_was_operator_required_and_recommended_supersession(self) -> None:
        self.assertEqual("SRFDI-G9S", self.packet["gate_id"])
        self.assertEqual("OPERATOR_REQUIRED", self.packet["gate_class"])
        self.assertEqual("GATE_READY", self.packet["status"])
        self.assertEqual("SUPERSEDE", self.packet["recommended_decision"])
        self.assertEqual(["SUPERSEDE", "DEFER", "BLOCK", "QUARANTINE"], self.packet["allowed_decisions"])
        self.assertEqual("OVC APPROVE SRFDI-G9S SUPERSEDE", self.packet["exact_operator_command"])

    def test_triggering_gap_is_exactly_the_wp2c_downstream_blocker(self) -> None:
        code = "FROZEN_REPRESENTATION_PACK_FIELD_MAPPING_NOT_MATERIALISED"
        self.assertEqual(code, self.gap["audit_result"])
        self.assertEqual(code, self.packet["triggering_blocker"]["code"])
        self.assertEqual(code, self.wp2c_merge["downstream_blocker"])
        self.assertEqual("BLOCK", self.packet["evidence"]["downstream_qa"])
        self.assertEqual("PASS_ENGINEERING_ONLY", self.packet["evidence"]["wp2c_qa"])

    def test_operator_decision_grants_only_bounded_wp9s_remediation(self) -> None:
        self.assertEqual("SUPERSEDE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("SRFDI-WP9S", self.decision["authority_delta"]["authorize_packet"])
        self.assertEqual("SRFDI-G9S-FREEZE", self.decision["required_next_operator_gate"])
        self.assertEqual("DENIED", self.decision["authority_delta"]["june_execution"])
        self.assertEqual("DENIED", self.decision["authority_delta"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.decision["authority_delta"]["validation_2025"])
        self.assertEqual("NONE", self.decision["authority_delta"]["scientific_promotion"])
        self.assertEqual("NONE", self.decision["authority_delta"]["selector_change"])
        self.assertEqual("NONE", self.decision["authority_delta"]["publication"])

    def test_qa_requires_new_version_not_silent_post_freeze_choice(self) -> None:
        self.assertEqual("BLOCK_CURRENT_G9_V0_1_FOR_JUNE", self.qa["qa_result"])
        self.assertEqual("SUPERSEDE", self.qa["qa_recommendation"])
        self.assertEqual("FAIL", self.qa["qa_checks"]["authoritative_real_source_pack_mapping_exists"])
        self.assertEqual("FAIL", self.qa["qa_checks"]["june_can_be_lawfully_authorized_under_current_frozen_v0_1"])
        self.assertEqual("PASS", self.qa["qa_checks"]["silent_post_freeze_mapping_choice_forbidden"])
        self.assertEqual("SRFDI-G9S-FREEZE", self.qa["required_future_stop"])

    def test_programme_state_advances_only_to_wp9s_and_preserves_firewalls(self) -> None:
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertEqual("SRFDI-WP9S", self.state["active_packet"])
        self.assertEqual("SRFDI-G9S-FREEZE", self.state["current_gate"])
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual("WP9S_IMPLEMENTED_CANDIDATE_GATE_READY", self.state["authority"]["preregistration_supersession"])
        self.assertTrue(self.state["authority"]["june"].startswith("DENIED"))
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("NONE", self.state["authority"]["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])
        self.assertEqual("PRESERVE_DO_NOT_MERGE", self.state["pr_371"])
        row = next(row for row in self.state["packets"] if row["packet_id"] == "SRFDI-G9S")
        self.assertEqual("COMPLETED", row["status"])
        self.assertEqual("SUPERSEDE", row["decision"])
        wp9s = next(row for row in self.state["packets"] if row["packet_id"] == "SRFDI-WP9S")
        self.assertEqual("GATE_READY", wp9s["status"])


if __name__ == "__main__":
    unittest.main()
