from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "registries/implementation/irof_golden2/OVC_IROF_GOLDEN2_STATE_v0_1.json"
POINTER = ROOT / "registries/implementation/irof_golden2/CURRENT_STATE_POINTER.json"
RECEIPT = ROOT / "docs/releases/irof-golden2-v0-1/g3/GOLDEN2_G3_TERMINAL_MERGE_RECEIPT.json"
DECISION = ROOT / "docs/releases/irof-golden2-v0-1/g3/GOLDEN2_G3_DECISION.json"


class Golden2TerminalReceiptTests(unittest.TestCase):
    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_terminal_state_binds_exact_primary_merge_and_has_no_next_packet(self) -> None:
        state = self._load(STATE)
        self.assertEqual("COMPLETED", state["status"])
        self.assertEqual("SYNTHETIC_WEEKLY_E2E_ASSURANCE_PASS", state["terminal_state"])
        self.assertIsNone(state["current_packet"])
        self.assertIsNone(state["current_gate"])
        self.assertIsNone(state["next_packet"])
        self.assertEqual("PROGRAMME_COMPLETED_NO_NEXT_PACKET", state["next_action"])
        self.assertEqual("110e563ccda0b84d4f7dc8d6156ee9e6997de54e", state["merge_commit"])
        self.assertEqual([], state["blockers"])
        self.assertEqual([], state["conformance_warnings"])
        self.assertEqual("NONE", state["authority_delta"])
        self.assertEqual("LOCKED_UNCONSUMED", state["validation"])

    def test_receipt_binds_final_head_main_merge_ref_checks_and_squash(self) -> None:
        receipt = self._load(RECEIPT)
        self.assertEqual(520, receipt["primary_pr"])
        self.assertEqual("15226ae6feee65a59a1a0fe51e837b24ea05127c", receipt["final_assurance_head"])
        self.assertEqual("3d397df3810964c177012109a28b0e5373e203ba", receipt["tested_main_base"])
        self.assertEqual("9c81be7ad2a120e0b64236749598dadaa84fdff8", receipt["tested_merge_ref"])
        self.assertEqual("110e563ccda0b84d4f7dc8d6156ee9e6997de54e", receipt["squash_merge_commit"])
        self.assertEqual(831, receipt["assurance"]["repository_suite"]["test_count"])
        self.assertEqual("PASS", receipt["assurance"]["repository_suite"]["status"])
        self.assertEqual("PASS", receipt["assurance"]["tiered_profile"]["status"])
        self.assertEqual("PASS", receipt["assurance"]["merge_readiness"]["status"])
        self.assertEqual(0, receipt["assurance"]["review_thread_count"])
        self.assertEqual([], receipt["assurance"]["conformance_warnings"])
        self.assertEqual("NONE", receipt["authority_delta"])
        self.assertFalse("publication" in receipt)

    def test_pointer_is_terminal_and_premerge_decision_remains_preserved(self) -> None:
        pointer = self._load(POINTER)
        decision = self._load(DECISION)
        self.assertEqual("COMPLETED", pointer["status"])
        self.assertIsNone(pointer["current_packet"])
        self.assertIsNone(pointer["current_gate"])
        self.assertFalse(pointer["operator_decision_required"])
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("DELEGATED_BY_OPERATOR_APPROVED_SYNTHETIC_PLAN", decision["decision_authority"])
        self.assertIsNone(decision["merge_commit"])
        self.assertEqual("NONE", decision["authority_delta"])


if __name__ == "__main__":
    unittest.main()
