from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp8/SRFDI_G8_OPERATOR_DECISION.json"
REPRESENTED_DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g8-represented/SRFDI_G8_REPRESENTED_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_1.json"


class SRFDIG8OperatorDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))
        cls.represented_decision = (
            json.loads(REPRESENTED_DECISION.read_text(encoding="utf-8"))
            if REPRESENTED_DECISION.exists()
            else None
        )

    def test_operator_decision_is_exact_redesign(self) -> None:
        self.assertEqual("SRFDI-G8", self.decision["gate_id"])
        self.assertEqual("OVC APPROVE SRFDI-G8 REDESIGN", self.decision["operator_command"])
        self.assertEqual("REDESIGN", self.decision["decision"])
        self.assertEqual("4a458bb98860434481a111ecf8d8276358a1a434", self.decision["predecision_head"])

    def test_redesign_grants_no_market_or_method_authority(self) -> None:
        effect = self.decision["decision_effect"]
        self.assertEqual("DENIED", effect["capacity_freeze"])
        self.assertEqual("AUTHORISED_BOUNDED_DESIGN_ONLY", effect["capacity_redesign_preparation"])
        self.assertTrue(effect["wp9_start"].startswith("DENIED"))
        self.assertEqual("DENIED", effect["june_benchmark"])
        self.assertEqual("LOCKED_UNCONSUMED", effect["validation_2025"])
        self.assertEqual("NONE", effect["distance_or_family_method_selection"])
        self.assertEqual("PRESERVE_DO_NOT_MERGE", effect["pr_371"])

    def test_programme_state_preserves_original_redesign_across_represented_gate(self) -> None:
        wp8 = next(p for p in self.state["packets"] if p["packet_id"] == "SRFDI-WP8")
        wp9 = next(p for p in self.state["packets"] if p["packet_id"] == "SRFDI-WP9")

        if self.state["current_gate"] == "SRFDI-G8":
            self.assertEqual("REDESIGN_REQUIRED", self.state["status"])
            self.assertEqual("REDESIGN_APPROVED", wp8["status"])
            self.assertEqual("REDESIGN", wp8["decision"])
            self.assertIn("CAPACITY_REDESIGN_REQUIRED_BEFORE_WP9", wp8["blockers"])
            self.assertIn("SRFDI_G8_REDESIGN_NOT_YET_GOVERNED", wp9["blockers"])
            return

        self.assertEqual("REDESIGN", wp8["original_g8_decision"])
        self.assertEqual("COMPLETED_ACCEPTED", wp8["capacity_redesign_subprogramme"])
        self.assertEqual("DENIED_PENDING_SRFDI_G_JUNE_AUTH", self.state["g8_disposition"]["june"])
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])

        if self.state["current_gate"] == "SRFDI-G8-REPRESENTED" and self.state["status"] == "GATE_READY":
            self.assertTrue(self.state["operator_decision_required"])
            self.assertEqual("G8_REPRESENTED_GATE_READY", wp8["status"])
            self.assertEqual("PENDING_OPERATOR", wp8["decision"])
            self.assertIn("OPERATOR_SRFDI_G8_REPRESENTED_DECISION_REQUIRED", wp8["blockers"])
            self.assertIn("SRFDI_G8_REPRESENTED_NOT_YET_FREEZE_MEASURED_CAPACITY", wp9["blockers"])
            self.assertEqual("PENDING_OPERATOR", self.state["g8_disposition"]["capacity_freeze"])
            return

        self.assertIsNotNone(self.represented_decision)
        self.assertEqual("FREEZE_MEASURED_CAPACITY", self.represented_decision["decision"])
        self.assertEqual(
            "OVC APPROVE SRFDI-G8-REPRESENTED FREEZE_MEASURED_CAPACITY",
            self.represented_decision["operator_command"],
        )
        self.assertEqual("FREEZE_MEASURED_CAPACITY", wp8["decision"])
        self.assertIn(self.state["g8_disposition"]["capacity_freeze"], {"APPROVED_PENDING_MERGE", "FROZEN_MEASURED_T0"})
        self.assertNotEqual("AUTHORIZED", self.state["authority"]["june"])

    def test_represented_freeze_grants_no_scientific_or_june_authority(self) -> None:
        if self.represented_decision is None:
            self.skipTest("represented gate has not yet been decided")
        effect = self.represented_decision["decision_effect"]
        self.assertEqual("FREEZE_MEASURED_CAPACITY", effect["capacity_freeze"])
        self.assertEqual("DENIED_PENDING_SRFDI_G_JUNE_AUTH", effect["june_benchmark"])
        self.assertEqual("LOCKED_UNCONSUMED", effect["validation_2025"])
        self.assertEqual("NONE", effect["representation_normalization_distance_family_sensitivity_promotion"])
        self.assertEqual("NONE", effect["selector"])
        self.assertEqual("NONE", effect["publication"])
        self.assertEqual("NONE", effect["probability_risk_exposure_execution"])
        self.assertEqual("PRESERVE_DO_NOT_MERGE", effect["pr_371"])

    def test_redesign_preserves_no_hidden_sampling_boundary(self) -> None:
        preserved = set(self.decision["redesign_boundary"]["must_preserve"])
        self.assertIn("no hidden sampling or approximation", preserved)
        self.assertIn("exact and visible population accounting", preserved)
        self.assertIn("June benchmark denial and Validation lock", preserved)


if __name__ == "__main__":
    unittest.main()
