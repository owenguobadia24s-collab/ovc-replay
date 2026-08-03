from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from ovc.research_operations.planned_closure_continuity import PCCRPlanError, validate_fixture, validate_gate, validate_programme_state

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads((ROOT / "fixtures/research_operations/planned_closure_continuity/valid_scheduled_closure_fixture_v0_1.json").read_text(encoding="utf-8"))
GATE = json.loads((ROOT / "docs/releases/planned-closure-continuity-remediation-v0-1/pccr-g0/PCCR_G0_OPERATOR_GATE_PACKET.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "registries/research_operations/planned_closure_continuity/OVC_PCCR_PROGRAMME_STATE_v0_1.json").read_text(encoding="utf-8"))

class PCCRPlanTests(unittest.TestCase):
    def test_fixture_passes(self):
        self.assertEqual(validate_fixture(FIXTURE)["status"], "PASS")

    def test_gate_and_state_pass(self):
        self.assertEqual(validate_gate(GATE)["status"], "PASS")
        self.assertEqual(validate_programme_state(STATE)["status"], "PASS")

    def test_synthetic_bar_blocks(self):
        value = copy.deepcopy(FIXTURE)
        value["closures"][0]["bars_created"] = 1
        with self.assertRaises(PCCRPlanError):
            validate_fixture(value)

    def test_provider_gap_relaxation_blocks(self):
        value = copy.deepcopy(GATE)
        value["authority_boundary"]["provider_gap_handling"] = "RELAXED"
        with self.assertRaises(PCCRPlanError):
            validate_gate(value)

    def test_new_instrument_blocks(self):
        value = copy.deepcopy(FIXTURE)
        value["instrument"] = "XAUUSD"
        with self.assertRaises(PCCRPlanError):
            validate_fixture(value)

    def test_activation_blocks(self):
        value = copy.deepcopy(GATE)
        value["authority_boundary"]["continuity_activation"] = "APPROVED"
        with self.assertRaises(PCCRPlanError):
            validate_gate(value)

if __name__ == "__main__":
    unittest.main()
