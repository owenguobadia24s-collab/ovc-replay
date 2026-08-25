from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATES = ROOT / "docs/programmes/grt-v0-2/gates"
STATE = ROOT / "registries/implementation/grt_v0_2"
AUTH = ROOT / "registries/authority"


class GRT2G25OperatorPassTests(unittest.TestCase):
    def test_operator_pass_activates_only_limited_new_artifact_enforcement(self) -> None:
        decision = json.loads((GATES / "GRT2_G2_5_OPERATOR_DECISION.json").read_text(encoding="utf-8"))
        authority = json.loads((AUTH / "GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_1.json").read_text(encoding="utf-8"))
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["approved_authority_delta"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT_ONLY")
        self.assertEqual(decision["active_enforcement_after_decision"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertIsNone(decision["debt_floor_generation_after_decision"])
        self.assertEqual(decision["g3_authority_effect"], "NONE")
        self.assertEqual(authority["authority_status"], "ACTIVE")
        self.assertEqual(authority["enforcement_mode"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertEqual(authority["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertIsNone(authority["debt_floor_generation"])
        self.assertEqual(authority["g3_status"], "NOT_AUTHORISED")

    def test_programme_state_preserves_pilot_activation_and_current_correction_boundary(self) -> None:
        pilot_state = json.loads((STATE / "OVC_GRT2_STATE_v0_10.json").read_text(encoding="utf-8"))
        threshold_state = json.loads((STATE / "OVC_GRT2_STATE_v0_11.json").read_text(encoding="utf-8"))
        blocker_state = json.loads((STATE / "OVC_GRT2_STATE_v0_12.json").read_text(encoding="utf-8"))
        correction_running_state = json.loads((STATE / "OVC_GRT2_STATE_v0_13.json").read_text(encoding="utf-8"))
        current_state = json.loads((STATE / "OVC_GRT2_STATE_v0_14.json").read_text(encoding="utf-8"))
        gate_ready_state = json.loads((STATE / "OVC_GRT2_STATE_v0_15.json").read_text(encoding="utf-8"))
        monitoring = json.loads((GATES / "GRT2_G2_5_PILOT_MONITORING_PLAN.json").read_text(encoding="utf-8"))
        ledger = json.loads((GATES / "GRT2_G2_5_PILOT_LEDGER.json").read_text(encoding="utf-8"))
        self.assertEqual(pilot_state["status"], "RUNNING")
        self.assertEqual(pilot_state["g2_5_status"], "APPROVED_OPERATOR_PASS_PILOT_ACTIVE")
        self.assertEqual(pilot_state["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertEqual(pilot_state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertIsNone(pilot_state["debt_floor_generation"])
        self.assertEqual(pilot_state["g3_status"], "PENDING_PILOT_EVIDENCE_AND_OPERATOR_REQUIRED")
        self.assertTrue(threshold_state["pilot_observation_threshold_met"])
        self.assertEqual(threshold_state["pilot_eligible_candidate_count"], 8)
        self.assertEqual(threshold_state["g3_status"], "NOT_AUTHORISED_READINESS_EVIDENCE_INCOMPLETE")
        self.assertEqual(blocker_state["status"], "BLOCKED")
        self.assertIn("GRT2_G3_FULL_ENFORCEMENT_REPLAY_SURFACE_NOT_MATERIALIZED", blocker_state["blockers"])

        self.assertEqual(correction_running_state["status"], "RUNNING")
        self.assertEqual(correction_running_state["g3_status"], "NOT_AUTHORISED_CORRECTIVE_IMPLEMENTATION_RUNNING")
        self.assertEqual(correction_running_state["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertEqual(correction_running_state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertIsNone(correction_running_state["debt_floor_generation"])

        self.assertEqual(current_state["status"], "APPROVED")
        self.assertEqual(current_state["g2_status"], "APPROVED_DELEGATED_PASS_SUPERSEDING_IMPLEMENTATION_QUALIFICATION")
        self.assertEqual(current_state["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertEqual(current_state["g3_status"], "NOT_AUTHORISED_READINESS_EVIDENCE_NEXT")
        self.assertEqual(current_state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertIsNone(current_state["debt_floor_generation"])
        self.assertEqual(gate_ready_state["status"], "GATE_READY_OPERATOR_REQUIRED")
        self.assertEqual(gate_ready_state["authority_effect"], "NONE_GATE_PREPARATION_ONLY")
        self.assertTrue(gate_ready_state["operator_decision_required"])
        self.assertEqual(current_state["authority_delta"], "NONE_CORRECTIVE_IMPLEMENTATION_ONLY")

        self.assertEqual(monitoring["status"], "ACTIVE_COLLECTING_EVIDENCE")
        self.assertEqual(monitoring["threshold"]["minimum_elapsed_hours"], 24)
        self.assertEqual(monitoring["threshold"]["minimum_eligible_candidate_evaluations"], 8)
        self.assertEqual(ledger["eligible_candidate_count"], 8)
        self.assertTrue(ledger["threshold_met"])
        self.assertFalse(ledger["g3_ready"])


if __name__ == "__main__":
    unittest.main()
