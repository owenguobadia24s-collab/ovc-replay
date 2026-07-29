from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROGRAMME_STATE = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/final-gate/C1C_G5_CORR3_PROGRAMME_STATE.json"
REGISTRY_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json"
MERGE_RECEIPT = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/corr3/C1C_G5_CORR3_MERGE_RECEIPT.json"


class C1cG5Corr3MergeStateTests(unittest.TestCase):
    def test_merge_receipt_and_programme_state_bind_exact_main_commit(self) -> None:
        receipt = json.loads(MERGE_RECEIPT.read_text(encoding="utf-8"))
        state = json.loads(PROGRAMME_STATE.read_text(encoding="utf-8"))
        self.assertEqual(receipt["packet_id"], "C1C-G5-CORR3")
        self.assertEqual(receipt["merge_commit"], "85c9805db69d487ffdb043eca18414101cf03387")
        self.assertEqual(receipt["merge_method"], "SQUASH")
        self.assertEqual(receipt["decision"], "PASS")
        self.assertEqual(receipt["decision_authority"], "DELEGATED_AUTO_EXECUTABLE")
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["merge_commit"], receipt["merge_commit"])
        self.assertEqual(state["authorised_candidate_window_id"], "PDPILOT-CANDIDATE-bab63b935155e4d9033aed81")

    def test_registry_stops_only_at_exact_operator_local_blocker(self) -> None:
        registry = json.loads(REGISTRY_STATE.read_text(encoding="utf-8"))
        self.assertEqual(
            registry["status"],
            "C1C_G5_CORR3_COMPLETED_IN_MAIN_OPERATOR_LOCAL_ONE_OBJECT_REREVIEW_REQUIRED",
        )
        self.assertEqual(registry["corr3"]["status"], "COMPLETED_IN_MAIN")
        self.assertEqual(registry["corr3"]["merge_commit"], "85c9805db69d487ffdb043eca18414101cf03387")
        self.assertEqual(registry["blocker"]["blocker_id"], "C1C-G5-BLOCK-004")
        self.assertEqual(registry["blocker"]["status"], "OPEN_OPERATOR_LOCAL_ONE_OBJECT_REREVIEW_REQUIRED")
        self.assertEqual(registry["blocker"]["second_machine_replay"], "DENIED_NOT_REQUIRED")
        self.assertEqual(registry["continuation"], "RUN_OPERATOR_LOCAL_C1C_G5_CORR3_ONE_OBJECT_REREVIEW")
        self.assertEqual(registry["next_gate"], "C1C-G5-CORRECTIVE-PILOT-REVIEW")

    def test_all_reserved_authority_remains_denied_or_none(self) -> None:
        registry = json.loads(REGISTRY_STATE.read_text(encoding="utf-8"))
        retained = registry["retained_authority"]
        self.assertEqual(retained["canonical_append"], "DENIED")
        self.assertEqual(retained["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(retained["trigger_distance_clustering_threshold_or_model_change"], "NONE")
        for field in (
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
            self.assertEqual(retained[field], "NONE")


if __name__ == "__main__":
    unittest.main()
