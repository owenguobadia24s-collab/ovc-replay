from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/corr2"
STATE = ROOT / "registries/research_operations/pattern_discovery/PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json"
RECEIPT = RELEASE / "C1C_G5_CORR2_IMPLEMENTATION_RECEIPT.json"
MERGE = RELEASE / "C1C_G5_CORR2_MERGE_RECEIPT.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(path)
    return value


class C1cG5Corr2MergeStateTests(unittest.TestCase):
    def test_packet_is_completed_on_exact_squash_merge(self) -> None:
        state = load(STATE)
        receipt = load(RECEIPT)
        merge = load(MERGE)
        expected = "66593aa2bca3b781058e1bc81f96bf2e57b18005"
        self.assertEqual(state["status"], "C1C_G5_CORR2_COMPLETED_IN_MAIN_OPERATOR_LOCAL_REREVIEW_REQUIRED")
        self.assertEqual(state["corr2"]["status"], "COMPLETED_IN_MAIN")
        self.assertEqual(state["corr2"]["merge_commit"], expected)
        self.assertEqual(receipt["status"], "COMPLETED_IN_MAIN_OPERATOR_LOCAL_REREVIEW_REQUIRED")
        self.assertEqual(receipt["merge_commit"], expected)
        self.assertEqual(merge["merge_commit"], expected)
        self.assertEqual(receipt["merge_method"], "SQUASH")
        self.assertEqual(merge["merge_method"], "SQUASH")
        self.assertEqual(merge["pull_request"], 137)

    def test_exact_final_checks_and_qa_pass_are_recorded(self) -> None:
        state = load(STATE)
        receipt = load(RECEIPT)
        merge = load(MERGE)
        expected_runs = {30405881435, 30405881448, 30405881334, 30405881354, 30405881330}
        self.assertEqual({item["workflow_run"] for item in state["corr2"]["tests"]}, expected_runs)
        self.assertEqual({item["workflow_run"] for item in receipt["tests"]}, expected_runs)
        self.assertEqual({item["workflow_run"] for item in merge["tests"]}, expected_runs)
        self.assertTrue(all(item["result"] == "PASS" for item in merge["tests"]))
        self.assertEqual(state["corr2"]["qa_result"], "PASS")
        self.assertEqual(receipt["qa_result"], "PASS")
        self.assertEqual(merge["qa_result"], "PASS")
        self.assertEqual(merge["review_state"]["blocking_implementation_issues"], 0)

    def test_operator_local_blocker_is_open_and_machine_replay_remains_denied(self) -> None:
        state = load(STATE)
        merge = load(MERGE)
        blocker = state["blocker"]
        self.assertEqual(blocker["blocker_id"], "C1C-G5-BLOCK-003")
        self.assertEqual(blocker["status"], "OPEN_OPERATOR_LOCAL_TWO_OBJECT_REREVIEW_REQUIRED")
        self.assertEqual(blocker["second_machine_replay"], "DENIED_NOT_REQUIRED")
        self.assertEqual(merge["operator_local_blocker"]["blocker_id"], "C1C-G5-BLOCK-003")
        self.assertEqual(len(merge["operator_local_blocker"]["deferred_candidate_ids"]), 2)
        self.assertEqual(len(merge["operator_local_blocker"]["commands"]), 3)
        self.assertEqual(state["next_packet"], "C1C-G5-CORR2-LOCAL-REVIEW")
        self.assertEqual(state["next_gate"], "C1C-G5-CORRECTIVE-PILOT-REVIEW")

    def test_retained_authority_is_identical_and_fail_closed(self) -> None:
        state = load(STATE)["retained_authority"]
        merge = load(MERGE)["retained_authority"]
        for key in (
            "canonical_discovery_processing",
            "canonical_append",
            "selector_mutation",
            "release_mutation",
        ):
            self.assertEqual(state[key], "DENIED")
            self.assertEqual(merge[key], "DENIED")
        self.assertEqual(state["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(merge["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(merge["second_machine_replay"], "DENIED_NOT_REQUIRED")
        for key in (
            "semantic_promotion",
            "family_promotion",
            "candidate_promotion",
            "novelty_promotion",
            "probability",
            "risk",
            "exposure",
            "trading",
            "execution",
            "agent_write",
        ):
            self.assertEqual(state[key], "NONE")
            self.assertEqual(merge[key], "NONE")


if __name__ == "__main__":
    unittest.main()
