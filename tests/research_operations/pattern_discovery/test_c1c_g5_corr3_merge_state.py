from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROGRAMME_STATE = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/final-gate/C1C_G5_CORR3_PROGRAMME_STATE.json"
REGISTRY_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json"
IMPLEMENTATION_MERGE_RECEIPT = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/corr3/C1C_G5_CORR3_MERGE_RECEIPT.json"
OPERATOR_PASS_MERGE_RECEIPT = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/final-gate/C1C_G5_CORR3_OPERATOR_PASS_MERGE_RECEIPT.json"


class C1cG5Corr3MergeStateTests(unittest.TestCase):
    def test_historical_corr3_implementation_merge_remains_bound(self) -> None:
        receipt = json.loads(IMPLEMENTATION_MERGE_RECEIPT.read_text(encoding="utf-8"))
        state = json.loads(PROGRAMME_STATE.read_text(encoding="utf-8"))
        self.assertEqual(receipt["packet_id"], "C1C-G5-CORR3")
        self.assertEqual(receipt["merge_commit"], "85c9805db69d487ffdb043eca18414101cf03387")
        self.assertEqual(receipt["merge_method"], "SQUASH")
        self.assertEqual(receipt["decision"], "PASS")
        self.assertEqual(receipt["decision_authority"], "DELEGATED_AUTO_EXECUTABLE")
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["merge_commit"], receipt["merge_commit"])
        self.assertEqual(state["authorised_candidate_window_id"], "PDPILOT-CANDIDATE-bab63b935155e4d9033aed81")

    def test_operator_pass_receipt_and_registry_close_exact_blocker(self) -> None:
        receipt = json.loads(OPERATOR_PASS_MERGE_RECEIPT.read_text(encoding="utf-8"))
        registry = json.loads(REGISTRY_STATE.read_text(encoding="utf-8"))
        self.assertEqual(receipt["gate_id"], "C1C-G5-CORRECTIVE-PILOT-REVIEW")
        self.assertEqual(receipt["decision"], "PASS")
        self.assertEqual(receipt["decision_authority"], "OPERATOR")
        self.assertEqual(receipt["merge_commit"], "1d4065b7a4fa9a7c6d832528309a5b4f56fd2991")
        self.assertEqual(receipt["merge_method"], "SQUASH")
        self.assertEqual(
            registry["status"],
            "C1C_G5_CORRECTIVE_PILOT_REVIEW_COMPLETED_OPERATOR_PASS",
        )
        self.assertEqual(registry["corr3"]["status"], "COMPLETED_IN_MAIN")
        final_pass = registry["final_operator_pass"]
        self.assertEqual(final_pass["decision"], "PASS")
        self.assertEqual(final_pass["decision_authority"], "OPERATOR")
        self.assertEqual(final_pass["decision_merge_commit"], receipt["merge_commit"])
        self.assertEqual(final_pass["remaining_deferred_object_count"], 0)
        self.assertEqual(final_pass["candidate_or_family_promotion"], "NOT_AUTHORISED")
        self.assertEqual(registry["blocker"]["blocker_id"], "C1C-G5-BLOCK-004")
        self.assertEqual(registry["blocker"]["status"], "CLOSED_BY_OPERATOR_PASS")
        self.assertEqual(registry["blocker"]["second_machine_replay"], "DENIED_NOT_REQUIRED")
        self.assertEqual(registry["continuation"], "BEGIN_RO3_WP3_RETEST_AFTER_C1_CORRECTIVE_PROGRAMME")
        self.assertEqual(registry["next_packet"], "RO3-WP3_RETEST_AFTER_C1_CORRECTIVE_PROGRAMME")
        self.assertEqual(registry["next_gate"], "RO3-G3")

    def test_all_reserved_authority_remains_denied_or_none(self) -> None:
        registry = json.loads(REGISTRY_STATE.read_text(encoding="utf-8"))
        retained = registry["retained_authority"]
        self.assertEqual(retained["canonical_discovery_processing"], "DENIED")
        self.assertEqual(retained["canonical_append"], "DENIED")
        self.assertEqual(retained["selector_mutation"], "DENIED")
        self.assertEqual(retained["release_mutation"], "DENIED")
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
