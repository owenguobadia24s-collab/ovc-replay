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

    def test_programme_state_preserves_g2_pass_while_pointer_advances_to_operator_gate(self) -> None:
        state = json.loads((STATE / "OVC_GRT2_STATE_v0_8.json").read_text(encoding="utf-8"))
        pointer = json.loads((STATE / "CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
        gate_state = json.loads((STATE / "OVC_GRT2_STATE_v0_9.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "APPROVED")
        self.assertEqual(state["g2_status"], "APPROVED_DELEGATED_PASS")
        self.assertEqual(state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(state["active_enforcement"], "NONE")
        self.assertIsNone(state["debt_floor_generation"])
        self.assertEqual(state["g2_5_status"], "PENDING_OPERATOR_REQUIRED_GATE_PREPARATION")
        self.assertEqual(state["next_packet"], "GRT2-G2.5-GATE-PREPARATION")
        self.assertEqual(pointer["current_state"], "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_9.json")
        self.assertEqual(pointer["status"], "GATE_READY")
        self.assertEqual(pointer["packet_id"], "GRT2-G2.5-GATE-PREPARATION")
        self.assertEqual(pointer["gate_id"], "GRT2-G2.5")
        self.assertEqual(pointer["next_packet"], "GRT2-G2.5-PILOT-START_AFTER_OPERATOR_PASS")
        self.assertEqual(gate_state["g2_status"], "APPROVED_DELEGATED_PASS_MERGED_C4AFF0FA34AA1123031244D9E003BD32B2115706")
        self.assertEqual(gate_state["g2_5_status"], "GATE_READY_OPERATOR_REQUIRED")
        self.assertEqual(gate_state["active_enforcement"], "NONE")
        self.assertIsNone(gate_state["debt_floor_generation"])


if __name__ == "__main__":
    unittest.main()
