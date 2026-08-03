from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DECISION = json.loads(
    (ROOT / "docs/releases/market-translation-audit-v0-2/mta-g8/MTA_G8_OPERATOR_DECISION.json").read_text(encoding="utf-8")
)
STATE = json.loads(
    (ROOT / "registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json").read_text(encoding="utf-8")
)


class MTAG8OperatorDecisionTests(unittest.TestCase):
    def test_exact_operator_decisions_are_recorded(self) -> None:
        self.assertEqual(DECISION["status"], "APPROVED")
        self.assertEqual(DECISION["decisions"]["MTA-G8-CLOCK"]["decision"], "PASS")
        self.assertEqual(DECISION["decisions"]["MTA-G8-C2E"]["decision"], "PASS")
        self.assertEqual(DECISION["decisions"]["MTA-G8-C2.5"]["decision"], "PASS")
        self.assertEqual(DECISION["decisions"]["MTA-G8-C3"]["decision"], "DEFER")

    def test_c2_5_scope_is_bounded(self) -> None:
        self.assertEqual(
            DECISION["decisions"]["MTA-G8-C2.5"]["bounded_rule_set"],
            ["BOUNDARY_ZONE_ENTRY", "BREACH_ACTIVE", "LONG_PERSISTENCE", "REPEATED_SWITCHING"],
        )
        self.assertNotIn("LOCAL_PARENT_CONFLICT", DECISION["decisions"]["MTA-G8-C2.5"]["bounded_rule_set"])
        self.assertNotIn("ALIGNMENT_GAINED", DECISION["decisions"]["MTA-G8-C2.5"]["bounded_rule_set"])

    def test_decision_creates_plan_authority_only(self) -> None:
        boundary = DECISION["authority_boundary"]
        self.assertTrue(all(value in {"DENIED", "NONE"} for value in boundary.values()))
        self.assertEqual(
            DECISION["authorised_next_packets"],
            ["MTA-PLAN-CLOCK", "MTA-PLAN-C2E", "MTA-PLAN-C2.5"],
        )
        self.assertEqual(DECISION["deferred_packets"], ["MTA-PLAN-C3"])

    def test_programme_state_is_complete_and_consistent(self) -> None:
        self.assertEqual(STATE["programme_status"], "COMPLETED")
        self.assertFalse(STATE["operator_decision_required"])
        self.assertEqual(STATE["operator_decision_id"], DECISION["decision_id"])
        self.assertEqual(STATE["authorised_next_packets"], DECISION["authorised_next_packets"])
        self.assertEqual(STATE["deferred_packets"], DECISION["deferred_packets"])
        self.assertEqual(STATE["authority"]["c3_plan_preparation"], "DEFERRED_DENIED")
        self.assertEqual(STATE["authority"]["c2e_c2_5_c3_activation"], "DENIED")


if __name__ == "__main__":
    unittest.main()
