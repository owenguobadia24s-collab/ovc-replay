from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP3 = ROOT / "docs/programmes/grt-v0-2/wp3"
STATE = ROOT / "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_6.json"
CORRECTION_RUNNING_STATE = ROOT / "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_13.json"
CURRENT_STATE = ROOT / "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_14.json"
POINTER = ROOT / "registries/implementation/grt_v0_2/CURRENT_STATE_POINTER.json"


class GRT2Stack797CloseoutTests(unittest.TestCase):
    def test_operator_stack_label_is_not_misrecorded_as_pr_797(self) -> None:
        closeout = json.loads((WP3 / "GRT2_STACK_797_CLOSEOUT.json").read_text(encoding="utf-8"))
        self.assertEqual(closeout["operator_stack_label"], "Stack #797")
        self.assertFalse(closeout["github_pr_797_exists"])
        self.assertEqual(closeout["github_pr_797_lookup"], "NOT_FOUND_404")

    def test_native_stack_is_preserved_and_exact_replacements_are_recorded(self) -> None:
        closeout = json.loads((WP3 / "GRT2_STACK_797_CLOSEOUT.json").read_text(encoding="utf-8"))
        rows = closeout["original_stack"]
        self.assertEqual([row["original_pr"] for row in rows], [791, 792, 793, 795])
        self.assertEqual([row["replacement_pr"] for row in rows], [798, 799, 800, 801])
        self.assertTrue(all(row["disposition"] == "CLOSED_SUPERSEDED_BY_CURRENT_MAIN_RECONCILIATION" for row in rows))
        self.assertFalse(closeout["force_push_used"])
        self.assertFalse(closeout["history_rewrite_used"])
        self.assertFalse(closeout["payload_loss_detected"])
        self.assertEqual(closeout["authority_delta"], "NONE")
        self.assertEqual(closeout["terminal_main"], "ee3371cd9f25d51a7c424e9091cf21f13376a05f")

    def test_closeout_qa_and_decision_are_authority_neutral(self) -> None:
        qa = json.loads((WP3 / "GRT2_STACK_797_QA_PACKET.json").read_text(encoding="utf-8"))
        decision = json.loads((WP3 / "GRT2_STACK_797_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(qa["qa_recommendation"], "PASS")
        self.assertEqual(qa["qa_scope"], "STACK_RECONCILIATION_CLOSEOUT_ONLY")
        self.assertTrue(all(value == "PASS" for value in qa["acceptance"].values()))
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["decision_class"], "DELEGATED_AUTO_RATIFICATION")
        self.assertEqual(decision["authority_delta"], "NONE")
        self.assertEqual(decision["g2_status"], "NOT_EVALUATED")
        self.assertEqual(decision["reserved_authority_effect"], "NONE")

    def test_stack_closeout_state_remains_historical_while_correction_is_current(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        correction_running = json.loads(CORRECTION_RUNNING_STATE.read_text(encoding="utf-8"))
        current = json.loads(CURRENT_STATE.read_text(encoding="utf-8"))
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertEqual(state["packet_id"], "GRT2-WP3E")
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["g2_status"], "NOT_EVALUATED")
        self.assertEqual(state["active_enforcement"], "NONE")
        self.assertIsNone(state["debt_floor_generation"])
        self.assertEqual(state["next_packet"], "GRT2-G2-READINESS-EVIDENCE")

        self.assertEqual(correction_running["status"], "RUNNING")
        self.assertEqual(correction_running["g3_status"], "NOT_AUTHORISED_CORRECTIVE_IMPLEMENTATION_RUNNING")
        self.assertEqual(correction_running["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertIsNone(correction_running["debt_floor_generation"])

        self.assertEqual(pointer["current_state"], "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_14.json")
        self.assertEqual(pointer["packet_id"], "GRT2-G3-FULL-ENFORCEMENT-REPLAY-SURFACE-CORRECTION")
        self.assertEqual(pointer["gate_id"], "GRT2-G2-SUPERSEDING-QUALIFICATION")
        self.assertEqual(pointer["next_packet"], "GRT2-G3-READINESS-EVIDENCE")
        self.assertEqual(pointer["status"], "APPROVED")
        self.assertEqual(current["status"], "APPROVED")
        self.assertEqual(current["g2_status"], "APPROVED_DELEGATED_PASS_SUPERSEDING_IMPLEMENTATION_QUALIFICATION")
        self.assertEqual(current["g3_status"], "NOT_AUTHORISED_READINESS_EVIDENCE_NEXT")
        self.assertEqual(current["active_enforcement"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertEqual(current["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertIsNone(current["debt_floor_generation"])
        self.assertEqual(current["authority_delta"], "NONE_CORRECTIVE_IMPLEMENTATION_ONLY")


if __name__ == "__main__":
    unittest.main()
