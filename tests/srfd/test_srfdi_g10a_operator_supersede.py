from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a/SRFDI_G10A_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_15.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIG10AOperatorSupersedeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decision = json.loads(DECISION.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_supersede_is_exact_and_bounded(self) -> None:
        self.assertEqual("SRFDI-G10A", self.decision["gate_id"])
        self.assertEqual("SUPERSEDE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("SRFDI-WP10A", self.decision["authority_delta"]["authorize_packet"])
        self.assertEqual("REAL_DATA_FAMILY_GRID_CAPACITY_REMEDIATION_ONLY", self.decision["authority_delta"]["mode"])
        self.assertEqual("SRFDI-G10A-FREEZE", self.decision["authority_delta"]["next_operator_gate"])

    def test_blocker_and_consumed_token_are_admitted_not_reset(self) -> None:
        blocker = self.decision["admitted_blocker"]
        self.assertEqual(433, blocker["pr"])
        self.assertEqual("f9bbeba065cf85f5a5f5c0a88e9c9d0ea6fa96d7", blocker["head"])
        self.assertEqual("CONSUMED_NOT_REUSABLE", blocker["token_state"])
        self.assertTrue(self.pointer["authority_token_consumed"])
        self.assertIn("NO_RETRY", self.pointer["june_execution"])

    def test_science_and_population_remain_frozen(self) -> None:
        frozen = self.decision["frozen_bindings"]
        self.assertEqual(8598, frozen["eligible_record_count"])
        self.assertEqual(36, frozen["comparability_domain_count"])
        self.assertEqual(1944, frozen["family_configuration_count"])
        self.assertEqual("FORBIDDEN", frozen["mutation"])
        self.assertEqual("f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3", frozen["preregistration_logical_sha256"])

    def test_state_and_pointer_authorize_only_wp10a(self) -> None:
        self.assertEqual("APPROVED", self.state["status"])
        self.assertEqual("SRFDI-WP10A", self.state["active_packet"])
        self.assertEqual("SRFDI-G10A-FREEZE", self.state["current_gate"])
        self.assertEqual("AUTHORIZED_BOUNDED_REAL_DATA_FAMILY_GRID_CAPACITY_REMEDIATION_ONLY", self.state["authority"]["wp10a_execution"])
        self.assertTrue(self.state["authority"]["fresh_june_scientific_run"].startswith("DENIED"))
        self.assertEqual("NONE", self.state["authority"]["scientific_promotion"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])
        self.assertEqual("registries/implementation/srfd/OVC_SRFDI_STATE_v0_15.json", self.pointer["authoritative_state"])
        self.assertEqual("SRFDI-WP10A", self.pointer["next_packet"])


if __name__ == "__main__":
    unittest.main()
