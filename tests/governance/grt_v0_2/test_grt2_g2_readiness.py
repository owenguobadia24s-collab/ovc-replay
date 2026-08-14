from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
G2 = ROOT / "docs/programmes/grt-v0-2/g2"
STATE = ROOT / "registries/implementation/grt_v0_2"


class GRT2G2ReadinessStateTests(unittest.TestCase):
    def test_g2_fails_closed_until_required_evidence_exists(self) -> None:
        packet = json.loads((G2 / "GRT2_G2_READINESS_PACKET.json").read_text(encoding="utf-8"))
        decision = json.loads((G2 / "GRT2_G2_DECISION.json").read_text(encoding="utf-8"))
        qa = json.loads((G2 / "GRT2_G2_QA_PACKET.json").read_text(encoding="utf-8"))
        self.assertEqual(packet["recommended_decision"], "BLOCK")
        self.assertEqual(decision["decision"], "BLOCK")
        self.assertEqual(qa["qa_recommendation"], "BLOCK")
        self.assertIn("G2_MEASURED_PERFORMANCE_BUDGET_MISSING", decision["reason_codes"])
        self.assertIn("G2_A8_REAL_CI_SHADOW_REVIEW_MISSING", decision["reason_codes"])

    def test_historical_block_state_is_preserved_after_g2_pass(self) -> None:
        state = json.loads((STATE / "OVC_GRT2_STATE_v0_7.json").read_text(encoding="utf-8"))
        pointer = json.loads((STATE / "CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
        current = json.loads((STATE / "OVC_GRT2_STATE_v0_8.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "BLOCKED")
        self.assertEqual(state["g2_status"], "BLOCKED_MISSING_REQUIRED_EVIDENCE")
        self.assertEqual(state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(state["active_enforcement"], "NONE")
        self.assertIsNone(state["debt_floor_generation"])
        self.assertEqual(state["g2_5_status"], "PENDING_UNCONSUMED_UNTIL_G2_COMPLETE")
        self.assertEqual(pointer["current_state"], "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_8.json")
        self.assertEqual(pointer["status"], "APPROVED")
        self.assertEqual(pointer["next_packet"], "GRT2-G2.5-GATE-PREPARATION")
        self.assertEqual(current["g2_status"], "APPROVED_DELEGATED_PASS")
        self.assertEqual(current["active_enforcement"], "NONE")
        self.assertIsNone(current["debt_floor_generation"])


if __name__ == "__main__":
    unittest.main()
