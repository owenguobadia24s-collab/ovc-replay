from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GATE_ROOT = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/operator-gate"
BUNDLE = GATE_ROOT / "C1C_G5_CORRECTIVE_PILOT_REVIEW_GATE_READY_BUNDLE.json"
DECISION = GATE_ROOT / "C1C_G5_CORRECTIVE_PILOT_REVIEW_OPERATOR_DECISION.json"
STATE = ROOT / "registries/research_operations/pattern_discovery/PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json"


class C1cG5CorrectivePilotReviewDeferTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_operator_defer_matches_gate_ready_recommendation(self) -> None:
        self.assertEqual(self.bundle["gate_id"], "C1C-G5-CORRECTIVE-PILOT-REVIEW")
        self.assertEqual(self.bundle["recommended_decision"]["decision"], "DEFER")
        self.assertEqual(self.decision["decision"], "DEFER")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        self.assertEqual(
            self.decision["operator_command"],
            "OVC APPROVE C1C-G5-CORRECTIVE-PILOT-REVIEW DEFER",
        )

    def test_exact_machine_and_review_evidence_are_accepted_without_replay(self) -> None:
        evidence = self.decision["accepted_evidence"]
        self.assertEqual(evidence["pilot_run_id"], "PD.PILOT.RUN.96c16f11717e787f971851ee")
        self.assertEqual(evidence["active_c2_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")
        self.assertTrue(evidence["machine_rerun_valid"])
        self.assertTrue(evidence["structured_review_v2_complete"])
        self.assertFalse(evidence["second_machine_replay_required"])

    def test_corr2_scope_is_bounded_and_nonactivating(self) -> None:
        packet = self.decision["authorised_next_packet"]
        self.assertEqual(packet["packet_id"], "C1C-G5-CORR2")
        self.assertEqual(packet["authority_delta"], "NONACTIVATING_REVIEW_WORKFLOW_CORRECTION_ONLY")
        self.assertEqual(packet["machine_replay"], "DENIED_NOT_REQUIRED")
        self.assertEqual(packet["return_gate"], "C1C-G5-CORRECTIVE-PILOT-REVIEW")
        self.assertIn(
            self.state["status"],
            {
                "OPERATOR_DEFER_RECORDED_C1C_G5_CORR2_AUTHORISED",
                "C1C_G5_CORR2_IMPLEMENTED_OPERATOR_LOCAL_REREVIEW_REQUIRED",
                "C1C_G5_CORR2_COMPLETED_IN_MAIN_OPERATOR_LOCAL_REREVIEW_REQUIRED",
            },
        )
        self.assertIn(
            self.state["corr2"]["status"],
            {"READY", "RUNNING", "IMPLEMENTED", "QA_REVIEW", "GATE_READY", "COMPLETED_IN_MAIN"},
        )
        self.assertEqual(self.state["corr2"]["authority_delta"], "NONACTIVATING_REVIEW_WORKFLOW_CORRECTION_ONLY")
        self.assertEqual(self.state["corr2"]["second_machine_replay"], "DENIED_NOT_REQUIRED")

    def test_retained_authority_is_fail_closed(self) -> None:
        retained = self.decision["retained_prohibitions"]
        self.assertEqual(retained["canonical_discovery_processing"], "DENIED")
        self.assertEqual(retained["canonical_append"], "DENIED")
        self.assertEqual(retained["validation_consumption"], "LOCKED_UNCONSUMED")
        for key in (
            "semantic_promotion",
            "family_promotion",
            "candidate_promotion",
            "novelty_promotion",
            "threshold_or_model_change",
            "probability",
            "risk",
            "exposure",
            "trading",
            "execution",
            "agent_write",
        ):
            self.assertEqual(retained[key], "NONE")
        self.assertEqual(retained["selector_mutation"], "DENIED")
        self.assertEqual(retained["release_mutation"], "DENIED")
        self.assertEqual(retained["r2_publication"], "DENIED")


if __name__ == "__main__":
    unittest.main()
