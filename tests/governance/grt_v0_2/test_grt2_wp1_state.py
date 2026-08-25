from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP1 = ROOT / "docs/programmes/grt-v0-2/wp1"
STATE_ROOT = ROOT / "registries/implementation/grt_v0_2"
REGISTRIES = ROOT / "registries/governance/grt_v0_2"
WP1_STATE = STATE_ROOT / "OVC_GRT2_STATE_v0_3.json"
READINESS_STATE = STATE_ROOT / "OVC_GRT2_STATE_v0_7.json"
G2_STATE = STATE_ROOT / "OVC_GRT2_STATE_v0_8.json"
PILOT_STATE = STATE_ROOT / "OVC_GRT2_STATE_v0_10.json"
THRESHOLD_STATE = STATE_ROOT / "OVC_GRT2_STATE_v0_11.json"
BLOCKER_STATE = STATE_ROOT / "OVC_GRT2_STATE_v0_12.json"
CORRECTION_RUNNING_STATE = STATE_ROOT / "OVC_GRT2_STATE_v0_13.json"
CURRENT_STATE = STATE_ROOT / "OVC_GRT2_STATE_v0_14.json"
GATE_READY_STATE = STATE_ROOT / "OVC_GRT2_STATE_v0_15.json"
SUPERSEDING_GATE_READY_STATE = STATE_ROOT / "OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json"


class GRT2WP1StateTests(unittest.TestCase):
    def test_wp0_merge_receipt_and_wp1_preflight_are_source_bound(self) -> None:
        merge = json.loads((WP1 / "GRT2_WP0_MERGE_RECEIPT.json").read_text(encoding="utf-8"))
        preflight = json.loads((WP1 / "GRT2_WP1_PREFLIGHT.json").read_text(encoding="utf-8"))
        self.assertEqual(merge["pull_request"], 726)
        self.assertEqual(merge["merge_commit"], "d41a29f9895482de0d1515efc2ca0aebf8016b45")
        self.assertEqual(merge["merge_tree"], "7f4fba22eec37ab7c257334fb6ac1624bd4bf23f")
        self.assertEqual(merge["authority_effect"], "NONE_PRE_ENFORCEMENT")
        self.assertEqual(preflight["baseline_commit"], merge["merge_commit"])
        self.assertEqual(preflight["baseline_tree"], merge["merge_tree"])
        self.assertEqual(preflight["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(preflight["activation"], "INACTIVE")
        self.assertEqual(preflight["authority_effect"], "NONE_PRE_ENFORCEMENT")

    def test_historical_wp1_state_is_preserved_while_current_pointer_advances(self) -> None:
        pointer = json.loads((STATE_ROOT / "CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
        state = json.loads(WP1_STATE.read_text(encoding="utf-8"))
        readiness = json.loads(READINESS_STATE.read_text(encoding="utf-8"))
        g2 = json.loads(G2_STATE.read_text(encoding="utf-8"))
        pilot = json.loads(PILOT_STATE.read_text(encoding="utf-8"))
        threshold = json.loads(THRESHOLD_STATE.read_text(encoding="utf-8"))
        blocker = json.loads(BLOCKER_STATE.read_text(encoding="utf-8"))
        correction_running = json.loads(CORRECTION_RUNNING_STATE.read_text(encoding="utf-8"))
        current = json.loads(CURRENT_STATE.read_text(encoding="utf-8"))
        gate_ready = json.loads(GATE_READY_STATE.read_text(encoding="utf-8"))
        superseding_gate_ready = json.loads(SUPERSEDING_GATE_READY_STATE.read_text(encoding="utf-8"))
        constitution = json.loads((REGISTRIES / "GRT_REPOSITORY_CONSTITUTION_v0_2.json").read_text(encoding="utf-8"))
        self.assertEqual(pointer["current_state"], "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json")
        self.assertEqual(pointer["status"], "GATE_READY_OPERATOR_REQUIRED_PENDING_EXACT_FINAL_PR_ASSURANCE")
        self.assertEqual(pointer["packet_id"], "GRT2-G3-SUPERSEDING-GATE-READY")
        self.assertEqual(pointer["next_packet"], "GRT2-G3-SUPERSEDING-OPERATOR-DECISION")
        self.assertEqual(readiness["status"], "BLOCKED")
        self.assertEqual(readiness["packet_id"], "GRT2-G2-READINESS-EVIDENCE")
        self.assertEqual(readiness["next_packet"], "GRT2-G2-QUALIFICATION-EVIDENCE")
        self.assertEqual(readiness["g2_status"], "BLOCKED_MISSING_REQUIRED_EVIDENCE")
        self.assertEqual(g2["status"], "APPROVED")
        self.assertEqual(g2["g2_status"], "APPROVED_DELEGATED_PASS")
        self.assertEqual(g2["active_enforcement"], "NONE")
        self.assertIsNone(g2["debt_floor_generation"])
        self.assertEqual(pilot["status"], "RUNNING")
        self.assertEqual(pilot["g2_5_status"], "APPROVED_OPERATOR_PASS_PILOT_ACTIVE")
        self.assertEqual(pilot["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertIsNone(pilot["debt_floor_generation"])
        self.assertTrue(threshold["pilot_observation_threshold_met"])
        self.assertEqual(threshold["g3_status"], "NOT_AUTHORISED_READINESS_EVIDENCE_INCOMPLETE")
        self.assertEqual(blocker["status"], "BLOCKED")

        self.assertEqual(correction_running["status"], "RUNNING")
        self.assertEqual(correction_running["g3_status"], "NOT_AUTHORISED_CORRECTIVE_IMPLEMENTATION_RUNNING")
        self.assertEqual(correction_running["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertIsNone(correction_running["debt_floor_generation"])

        self.assertEqual(current["status"], "APPROVED")
        self.assertEqual(current["g2_status"], "APPROVED_DELEGATED_PASS_SUPERSEDING_IMPLEMENTATION_QUALIFICATION")
        self.assertEqual(current["g3_status"], "NOT_AUTHORISED_READINESS_EVIDENCE_NEXT")
        self.assertEqual(current["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertEqual(current["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertIsNone(current["debt_floor_generation"])
        self.assertEqual(gate_ready["status"], "GATE_READY_OPERATOR_REQUIRED")
        self.assertEqual(gate_ready["authority_effect"], "NONE_GATE_PREPARATION_ONLY")
        self.assertTrue(gate_ready["operator_decision_required"])
        self.assertEqual(superseding_gate_ready["status"], "GATE_READY_OPERATOR_REQUIRED_PENDING_EXACT_FINAL_PR_ASSURANCE")
        self.assertEqual(superseding_gate_ready["authority_effect"], "NONE_GATE_PREPARATION_ONLY")
        self.assertEqual(superseding_gate_ready["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertIsNone(superseding_gate_ready["debt_floor_generation"])
        self.assertEqual(current["authority_delta"], "NONE_CORRECTIVE_IMPLEMENTATION_ONLY")

        self.assertEqual(state["status"], "APPROVED")
        self.assertEqual(state["packet_id"], "GRT2-WP1")
        self.assertEqual(state["gate_id"], "GRT2-G1")
        self.assertEqual(state["active_enforcement"], "NONE")
        self.assertIsNone(state["debt_floor_generation"])
        self.assertIsNone(state["debt_floor_hash"])
        self.assertEqual(state["constitution_hash"], constitution["canonical_hash"])
        self.assertEqual(state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(state["blockers"], [])
        self.assertEqual(state["qa_packet"], "docs/programmes/grt-v0-2/wp1/GRT2_WP1_QA_PACKET.json")
        self.assertEqual(state["decision_record"], "docs/programmes/grt-v0-2/wp1/GRT2_G1_DECISION.json")

    def test_wp1_historical_closeout_and_current_state_preserve_g3_boundary(self) -> None:
        state = json.loads(WP1_STATE.read_text(encoding="utf-8"))
        g2 = json.loads(G2_STATE.read_text(encoding="utf-8"))
        pilot = json.loads(PILOT_STATE.read_text(encoding="utf-8"))
        correction_running = json.loads(CORRECTION_RUNNING_STATE.read_text(encoding="utf-8"))
        current = json.loads(CURRENT_STATE.read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "APPROVED")
        self.assertNotIn("GRT2-G2 PASS", state["prerequisites"])
        self.assertEqual(state["active_enforcement"], "NONE")
        self.assertIn("GRT2-G2.5 and GRT2-G3 remain reserved.", state["warnings"])
        self.assertEqual(g2["g2_status"], "APPROVED_DELEGATED_PASS")
        self.assertEqual(g2["g2_5_status"], "PENDING_OPERATOR_REQUIRED_GATE_PREPARATION")
        self.assertEqual(pilot["g2_5_status"], "APPROVED_OPERATOR_PASS_PILOT_ACTIVE")
        self.assertEqual(pilot["g3_status"], "PENDING_PILOT_EVIDENCE_AND_OPERATOR_REQUIRED")
        self.assertEqual(correction_running["g3_status"], "NOT_AUTHORISED_CORRECTIVE_IMPLEMENTATION_RUNNING")
        self.assertEqual(correction_running["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertIsNone(correction_running["debt_floor_generation"])
        self.assertEqual(current["g3_status"], "NOT_AUTHORISED_READINESS_EVIDENCE_NEXT")
        self.assertEqual(current["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(current["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertIsNone(current["debt_floor_generation"])
        self.assertEqual(current["authority_delta"], "NONE_CORRECTIVE_IMPLEMENTATION_ONLY")


if __name__ == "__main__":
    unittest.main()
