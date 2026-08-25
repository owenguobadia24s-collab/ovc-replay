from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
G2 = ROOT / "docs/programmes/grt-v0-2/g2"
STATE = ROOT / "registries/implementation/grt_v0_2"


class GRT2G2FinalStateTests(unittest.TestCase):
    def test_g2_final_decision_is_delegated_pass_with_zero_reserved_authority(self) -> None:
        decision = json.loads((G2 / "GRT2_G2_FINAL_DECISION.json").read_text(encoding="utf-8"))
        renewal = json.loads((G2 / "GRT2_G2_CURRENT_MAIN_RENEWAL.json").read_text(encoding="utf-8"))
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["decision_class"], "DELEGATED_AUTO_RATIFICATION")
        self.assertEqual(decision["qa_recommendation"], "PASS")
        self.assertEqual(decision["reserved_authority_effect"], "NONE")
        self.assertEqual(decision["active_enforcement_after_decision"], "NONE")
        self.assertIsNone(decision["debt_floor_generation_after_decision"])
        self.assertEqual(decision["g2_5_status"], "PENDING_OPERATOR_REQUIRED")
        self.assertEqual(renewal["result"], "PASS")
        self.assertEqual(renewal["renewed_baseline_commit"], decision["baseline_commit"])
        self.assertEqual(renewal["real_ci_renewal"]["current_head_census"], "PASS_RESOLVED_ZERO_NOT_EVALUABLE_COMPONENTS")
        self.assertEqual(renewal["real_ci_renewal"]["current_head_a8_shadow"], "PASS_ZERO_UNRESOLVED_FALSE_NEGATIVES_ZERO_BLOCKING_FALSE_POSITIVES_ZERO_PILOT_ESCAPES")

    def test_programme_state_preserves_g2_pass_while_current_pointer_advances_to_correction(self) -> None:
        state = json.loads((STATE / "OVC_GRT2_STATE_v0_8.json").read_text(encoding="utf-8"))
        pilot_state = json.loads((STATE / "OVC_GRT2_STATE_v0_10.json").read_text(encoding="utf-8"))
        threshold_state = json.loads((STATE / "OVC_GRT2_STATE_v0_11.json").read_text(encoding="utf-8"))
        blocker_state = json.loads((STATE / "OVC_GRT2_STATE_v0_12.json").read_text(encoding="utf-8"))
        correction_running_state = json.loads((STATE / "OVC_GRT2_STATE_v0_13.json").read_text(encoding="utf-8"))
        current_state = json.loads((STATE / "OVC_GRT2_STATE_v0_14.json").read_text(encoding="utf-8"))
        gate_ready_state = json.loads((STATE / "OVC_GRT2_STATE_v0_15.json").read_text(encoding="utf-8"))
        pointer = json.loads((STATE / "CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "APPROVED")
        self.assertEqual(state["g2_status"], "APPROVED_DELEGATED_PASS")
        self.assertEqual(state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(state["active_enforcement"], "NONE")
        self.assertIsNone(state["debt_floor_generation"])
        self.assertEqual(pilot_state["g2_5_status"], "APPROVED_OPERATOR_PASS_PILOT_ACTIVE")
        self.assertEqual(pilot_state["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertEqual(pilot_state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertIsNone(pilot_state["debt_floor_generation"])
        self.assertTrue(threshold_state["pilot_observation_threshold_met"])
        self.assertEqual(threshold_state["pilot_eligible_candidate_count"], 8)
        self.assertEqual(threshold_state["g3_status"], "NOT_AUTHORISED_READINESS_EVIDENCE_INCOMPLETE")
        self.assertEqual(blocker_state["status"], "BLOCKED")
        self.assertIn("GRT2_G3_FULL_ENFORCEMENT_REPLAY_SURFACE_NOT_MATERIALIZED", blocker_state["blockers"])

        self.assertEqual(correction_running_state["status"], "RUNNING")
        self.assertEqual(correction_running_state["g3_status"], "NOT_AUTHORISED_CORRECTIVE_IMPLEMENTATION_RUNNING")
        self.assertEqual(correction_running_state["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertIsNone(correction_running_state["debt_floor_generation"])

        self.assertEqual(pointer["current_state"], "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json")
        self.assertEqual(pointer["status"], "GATE_READY_OPERATOR_REQUIRED_PENDING_EXACT_FINAL_PR_ASSURANCE")
        self.assertEqual(pointer["packet_id"], "GRT2-G3-SUPERSEDING-GATE-READY")
        self.assertEqual(pointer["gate_id"], "GRT2-G3")
        self.assertEqual(pointer["next_packet"], "GRT2-G3-SUPERSEDING-OPERATOR-DECISION")
        self.assertEqual(current_state["status"], "APPROVED")
        self.assertEqual(current_state["g2_status"], "APPROVED_DELEGATED_PASS_SUPERSEDING_IMPLEMENTATION_QUALIFICATION")
        self.assertEqual(current_state["g3_status"], "NOT_AUTHORISED_READINESS_EVIDENCE_NEXT")
        self.assertEqual(current_state["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertEqual(current_state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertIsNone(current_state["debt_floor_generation"])
        self.assertEqual(gate_ready_state["status"], "GATE_READY_OPERATOR_REQUIRED")
        self.assertEqual(gate_ready_state["authority_effect"], "NONE_GATE_PREPARATION_ONLY")
        self.assertTrue(gate_ready_state["operator_decision_required"])
        self.assertEqual(current_state["authority_delta"], "NONE_CORRECTIVE_IMPLEMENTATION_ONLY")


if __name__ == "__main__":
    unittest.main()
