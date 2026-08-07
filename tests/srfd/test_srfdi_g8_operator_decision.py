from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp8/SRFDI_G8_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_1.json"


class SRFDIG8OperatorDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

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

    def test_programme_state_routes_to_redesign_and_blocks_wp9(self) -> None:
        self.assertEqual("REDESIGN_REQUIRED", self.state["status"])
        self.assertFalse(self.state["operator_decision_required"])
        wp8 = next(p for p in self.state["packets"] if p["packet_id"] == "SRFDI-WP8")
        wp9 = next(p for p in self.state["packets"] if p["packet_id"] == "SRFDI-WP9")
        self.assertEqual("REDESIGN_APPROVED", wp8["status"])
        self.assertEqual("REDESIGN", wp8["decision"])
        self.assertIn("CAPACITY_REDESIGN_REQUIRED_BEFORE_WP9", wp8["blockers"])
        self.assertIn("SRFDI_G8_REDESIGN_NOT_YET_GOVERNED", wp9["blockers"])
        self.assertIn("DO_NOT_START_WP9", self.state["next_action"])

    def test_redesign_preserves_no_hidden_sampling_boundary(self) -> None:
        preserved = set(self.decision["redesign_boundary"]["must_preserve"])
        self.assertIn("no hidden sampling or approximation", preserved)
        self.assertIn("exact and visible population accounting", preserved)
        self.assertIn("June benchmark denial and Validation lock", preserved)


if __name__ == "__main__":
    unittest.main()
