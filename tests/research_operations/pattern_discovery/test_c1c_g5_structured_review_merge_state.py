from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "registries/research_operations/pattern_discovery/PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json"
QA = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/structured-review-v2/C1C_G5_STRUCTURED_REVIEW_V2_QA_PACKET.json"
RECEIPT = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/structured-review-v2/C1C_G5_STRUCTURED_REVIEW_V2_MERGE_RECEIPT.json"


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(path)
    return value


class C1cG5StructuredReviewMergeStateTests(unittest.TestCase):
    def test_implementation_merge_is_exact_and_complete(self) -> None:
        state = load(STATE)
        correction = state["structured_review_correction"]
        self.assertEqual(correction["status"], "COMPLETED_IN_MAIN")
        self.assertEqual(correction["decision"], "PASS")
        self.assertEqual(correction["decision_authority"], "DELEGATED_AUTO_EXECUTABLE")
        self.assertEqual(correction["tested_candidate_head"], "fed68083ea642ed9c4821b9e73ac2013bc922d44")
        self.assertEqual(correction["merge_commit"], "d2dedd3f65a3b7fa32ba334693aa18b74ba295c9")
        self.assertEqual(correction["pull_request"], 133)
        self.assertEqual(len(correction["tests"]), 2)
        self.assertTrue(all(item["result"] == "PASS" for item in correction["tests"]))

    def test_operator_gate_and_blocker_remain_open(self) -> None:
        state = load(STATE)
        self.assertEqual(state["status"], "BLOCKED_OPERATOR_LOCAL_STRUCTURED_V2_REVIEW_REQUIRED")
        self.assertEqual(state["blocker_id"], "C1C-G5-BLOCK-002")
        self.assertEqual(state["next_gate"], "C1C-G5-CORRECTIVE-PILOT-REVIEW")
        self.assertEqual(
            state["continuation_command"],
            ".\\scripts\\run_c1c_g5_structured_review_v2.ps1 preflight",
        )
        self.assertFalse(state["corrective_rerun"]["second_machine_replay_required"])
        self.assertEqual(state["corrective_rerun"]["canonical_append"], "DENIED")
        retained = state["retained_authority"]
        self.assertEqual(retained["validation_consumption"], "LOCKED_UNCONSUMED")
        for key in (
            "semantic_promotion",
            "family_promotion",
            "novelty_promotion",
            "threshold_change",
            "probability",
            "risk",
            "exposure",
            "trading",
            "execution",
            "agent_write",
        ):
            self.assertEqual(retained[key], "NONE", key)

    def test_qa_and_merge_receipt_reconcile(self) -> None:
        qa = load(QA)
        receipt = load(RECEIPT)
        self.assertEqual(qa["qa_status"], "PASS_IMPLEMENTATION_MERGED_BLOCKED_OPERATOR_LOCAL_STRUCTURED_REVIEW")
        self.assertEqual(qa["qa_recommendation"], "PASS")
        self.assertEqual(qa["unresolved_issues"], [])
        self.assertEqual(qa["merge_commit"], receipt["merge_commit"])
        self.assertEqual(receipt["merge_commit"], "d2dedd3f65a3b7fa32ba334693aa18b74ba295c9")
        self.assertEqual(receipt["merge_method"], "SQUASH")
        self.assertEqual(receipt["operator_local_blocker"]["blocker_id"], "C1C-G5-BLOCK-002")
        self.assertEqual(receipt["operator_local_blocker"]["status"], "OPEN")
        self.assertFalse(receipt["operator_local_blocker"]["second_machine_replay_required"])
        self.assertEqual(receipt["retained_authority"]["canonical_discovery_processing"], "DENIED")
        self.assertEqual(receipt["retained_authority"]["canonical_append"], "DENIED")


if __name__ == "__main__":
    unittest.main()
