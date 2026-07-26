from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "docs/releases/opt-b-c2-v2/c2-g7/C2_G7_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/opt-b-c2-v2/c2-g7/C2_G7_OPERATOR_DECISION.md"
REGISTRY = ROOT / "registries/research/C2_PROSPECTIVE_EVIDENCE_ACCEPTANCE.yaml"


class C2G7AcceptanceTests(unittest.TestCase):
    def test_gate_accepts_wp7_without_fabricating_evidence(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["decision"], "PASS_PROSPECTIVE_EVIDENCE_OPERATION_ACCEPTED")
        self.assertEqual(gate["blocking_issues"], 0)
        self.assertTrue(gate["prerequisites"]["zero_baseline"])
        self.assertFalse(gate["prerequisites"]["historical_backfill"])

    def test_operation_is_append_only_and_fail_closed(self) -> None:
        text = REGISTRY.read_text(encoding="utf-8")
        self.assertIn("state: ACTIVE_PROSPECTIVE_EVIDENCE_ACCUMULATION", text)
        self.assertIn("append_policy: APPEND_ONLY_AFTER_C2_G7", text)
        self.assertIn("validator_mode: FAIL_CLOSED", text)

    def test_retained_boundaries_are_unchanged(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        retained = gate["retained"]
        self.assertEqual(retained["validation_consumption"], "LOCKED_UNCONSUMED")
        for key in ("c2e_authority", "probability_authority", "exposure_authority", "trading_authority", "execution_authority"):
            self.assertEqual(retained[key], "NONE")
        for key in ("direct_r2_write", "selector_mutation", "release_mutation"):
            self.assertEqual(retained[key], "DENIED")

    def test_operator_decision_names_next_boundary(self) -> None:
        text = DECISION.read_text(encoding="utf-8")
        self.assertIn("first real prospective evidence batch", text)
        self.assertIn("No evidence observation is created", text)


if __name__ == "__main__":
    unittest.main()
