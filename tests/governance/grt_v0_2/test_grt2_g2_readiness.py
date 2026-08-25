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

    def test_historical_block_state_is_preserved_after_g2_pass_pilot_and_correction(self) -> None:
        state = json.loads((STATE / "OVC_GRT2_STATE_v0_7.json").read_text(encoding="utf-8"))
        g2_state = json.loads((STATE / "OVC_GRT2_STATE_v0_8.json").read_text(encoding="utf-8"))
        pilot_state = json.loads((STATE / "OVC_GRT2_STATE_v0_10.json").read_text(encoding="utf-8"))
        threshold_state = json.loads((STATE / "OVC_GRT2_STATE_v0_11.json").read_text(encoding="utf-8"))
        blocker_state = json.loads((STATE / "OVC_GRT2_STATE_v0_12.json").read_text(encoding="utf-8"))
        correction_running_state = json.loads((STATE / "OVC_GRT2_STATE_v0_13.json").read_text(encoding="utf-8"))
        current_state = json.loads((STATE / "OVC_GRT2_STATE_v0_14.json").read_text(encoding="utf-8"))
        gate_ready_state = json.loads((STATE / "OVC_GRT2_STATE_v0_15.json").read_text(encoding="utf-8"))
        superseding_gate_ready_state = json.loads((STATE / "OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json").read_text(encoding="utf-8"))
        pointer = json.loads((STATE / "CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "BLOCKED")
        self.assertEqual(state["g2_status"], "BLOCKED_MISSING_REQUIRED_EVIDENCE")
        self.assertEqual(state["active_enforcement"], "NONE")
        self.assertIsNone(state["debt_floor_generation"])
        self.assertEqual(g2_state["g2_status"], "APPROVED_DELEGATED_PASS")
        self.assertEqual(g2_state["active_enforcement"], "NONE")
        self.assertIsNone(g2_state["debt_floor_generation"])
        self.assertEqual(pilot_state["g2_5_status"], "APPROVED_OPERATOR_PASS_PILOT_ACTIVE")
        self.assertEqual(pilot_state["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertIsNone(pilot_state["debt_floor_generation"])
        self.assertTrue(threshold_state["pilot_observation_threshold_met"])
        self.assertEqual(threshold_state["pilot_eligible_candidate_count"], 8)
        self.assertEqual(blocker_state["status"], "BLOCKED")

        self.assertEqual(correction_running_state["status"], "RUNNING")
        self.assertEqual(correction_running_state["g3_status"], "NOT_AUTHORISED_CORRECTIVE_IMPLEMENTATION_RUNNING")
        self.assertEqual(correction_running_state["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertIsNone(correction_running_state["debt_floor_generation"])

        self.assertEqual(pointer["current_state"], "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json")
        self.assertEqual(pointer["status"], "GATE_READY_OPERATOR_REQUIRED_PENDING_EXACT_FINAL_PR_ASSURANCE")
        self.assertEqual(pointer["gate_id"], "GRT2-G3")
        self.assertEqual(pointer["packet_id"], "GRT2-G3-SUPERSEDING-GATE-READY")
        self.assertEqual(pointer["next_packet"], "GRT2-G3-SUPERSEDING-OPERATOR-DECISION")
        self.assertEqual(current_state["status"], "APPROVED")
        self.assertEqual(current_state["g2_status"], "APPROVED_DELEGATED_PASS_SUPERSEDING_IMPLEMENTATION_QUALIFICATION")
        self.assertEqual(current_state["g3_status"], "NOT_AUTHORISED_READINESS_EVIDENCE_NEXT")
        self.assertEqual(current_state["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertIsNone(current_state["debt_floor_generation"])
        self.assertEqual(current_state["authority_delta"], "NONE_CORRECTIVE_IMPLEMENTATION_ONLY")
        self.assertEqual(gate_ready_state["status"], "GATE_READY_OPERATOR_REQUIRED")
        self.assertEqual(gate_ready_state["authority_effect"], "NONE_GATE_PREPARATION_ONLY")
        self.assertTrue(gate_ready_state["operator_decision_required"])
        self.assertEqual(superseding_gate_ready_state["status"], "GATE_READY_OPERATOR_REQUIRED_PENDING_EXACT_FINAL_PR_ASSURANCE")
        self.assertEqual(superseding_gate_ready_state["authority_effect"], "NONE_GATE_PREPARATION_ONLY")
        self.assertEqual(superseding_gate_ready_state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertIsNone(superseding_gate_ready_state["debt_floor_generation"])


if __name__ == "__main__":
    unittest.main()
