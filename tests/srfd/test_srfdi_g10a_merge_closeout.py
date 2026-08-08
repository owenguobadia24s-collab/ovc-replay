from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a"
RECEIPT = BASE / "SRFDI_G10A_MERGE_RECEIPT.json"
QA = BASE / "SRFDI_G10A_CLOSEOUT_QA.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_16.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIG10AMergeCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_supersede_merge_is_exact(self) -> None:
        self.assertEqual("SRFDI-G10A", self.receipt["gate_id"])
        self.assertEqual("SUPERSEDE", self.receipt["decision"])
        self.assertEqual("OPERATOR", self.receipt["decision_authority"])
        self.assertEqual(442, self.receipt["pr_number"])
        self.assertEqual("20fcc4632847e6013f0ae58ba2bff4470a0493e2", self.receipt["tested_final_head"])
        self.assertEqual("b73805d1a846b82cca358815da743041cf2d2d54", self.receipt["merge_commit"])
        self.assertEqual("SUCCESS", self.receipt["assurance"]["repository_suite_result"])
        self.assertEqual("SUCCESS", self.receipt["assurance"]["tiered_profile_compatibility_merge_readiness_result"])

    def test_consumed_token_and_blocker_remain_preserved(self) -> None:
        effect = self.receipt["court_record_effect"]
        self.assertEqual("ADMITTED_PRESERVED_EXACT_HEAD_UNMERGED", effect["pr_433_blocker"])
        self.assertEqual("CONSUMED_NOT_REUSABLE", effect["authority_token_v0_4"])
        self.assertTrue(self.state["exact_bindings"]["authority_token_consumed"])
        self.assertTrue(self.pointer["authority_token_consumed"])
        self.assertIn("NO_RETRY", self.pointer["june_execution"])

    def test_state_is_ready_for_wp10a_capacity_only(self) -> None:
        self.assertEqual("AUTHORITATIVE_CURRENT", self.state["state_role"])
        self.assertEqual("READY", self.state["status"])
        self.assertEqual("SRFDI-WP10A", self.state["active_packet"])
        self.assertEqual("SRFDI-G10A-FREEZE", self.state["current_gate"])
        self.assertEqual("AUTHORIZED_BOUNDED_REAL_DATA_FAMILY_GRID_CAPACITY_REMEDIATION_ONLY", self.state["authority"]["wp10a_execution"])
        self.assertTrue(self.state["authority"]["fresh_june_scientific_run"].startswith("DENIED"))
        self.assertEqual("NONE", self.state["authority"]["scientific_promotion"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])

    def test_pointer_routes_to_v16_and_wp10a(self) -> None:
        self.assertEqual("registries/implementation/srfd/OVC_SRFDI_STATE_v0_16.json", self.pointer["authoritative_state"])
        self.assertEqual("READY", self.pointer["status"])
        self.assertEqual("SRFDI-WP10A", self.pointer["next_packet"])
        self.assertEqual("SRFDI-G10A-FREEZE", self.pointer["current_gate"])
        self.assertEqual("b73805d1a846b82cca358815da743041cf2d2d54", self.pointer["effective_after_main"])

    def test_closeout_is_delegated_zero_delta_pass(self) -> None:
        self.assertEqual("PASS", self.qa["qa_result"])
        self.assertEqual("NONE_CLOSEOUT_ONLY", self.qa["authority_delta"])
        self.assertTrue(self.qa["auto_ratifiable"])
        self.assertEqual("PASS", self.qa["delegated_decision"])
        self.assertEqual("SRFDI-WP10A", self.qa["next_packet"])
        self.assertEqual("SRFDI-G10A-FREEZE", self.qa["next_operator_gate"])


if __name__ == "__main__":
    unittest.main()
