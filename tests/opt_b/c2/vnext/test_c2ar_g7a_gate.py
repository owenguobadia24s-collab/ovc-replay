from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RELEASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp7"
QA = RELEASE / "C2AR_G7A_QA_PACKET.json"
DECISION = RELEASE / "C2AR_G7A_DELEGATED_DECISION.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_WP7_IMPLEMENTED_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class C2ARG7AGateTests(unittest.TestCase):
    def test_qa_is_pass_with_complete_bounded_evidence(self) -> None:
        qa = load(QA)
        self.assertEqual("C2AR-G7A", qa["gate_id"])
        self.assertTrue(all(item["status"] == "PASS" for item in qa["acceptance_conditions"]))
        self.assertEqual("PASS", qa["qa"]["recommendation"])
        self.assertEqual([], qa["qa"]["blocking_warnings"])
        self.assertEqual([], qa["qa"]["unresolved_issues"])
        self.assertEqual(235, qa["tests"][0]["test_count"])
        self.assertFalse(qa["qa"]["raw_market_data"])
        self.assertFalse(qa["qa"]["r2_writes"])

    def test_delegated_pass_is_inside_operator_and_plan_authority(self) -> None:
        decision = load(DECISION)
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("DELEGATED_BY_APPROVED_PLAN_AND_CEAR_G7", decision["decision_authority"])
        self.assertEqual("CEAR-G7.OPERATOR.PASS.20260804T234400+0100", decision["operator_decision_id"])
        self.assertEqual("INACTIVE_NONCANONICAL_SHADOW_FROZEN", decision["authority_delta"]["transition_classifier"])
        self.assertEqual("SIX_INACTIVE_NONCANONICAL_THRESHOLD_FREE", decision["authority_delta"]["raw_detectors"])
        self.assertEqual("NONE", decision["authority_delta"]["semantic_event_episode"])
        self.assertEqual("NONE", decision["authority_delta"]["parent_context_resolver"])
        self.assertEqual("NONE", decision["authority_delta"]["probability_risk_exposure_execution"])

    def test_programme_state_routes_only_to_cear_g8_gate_preparation(self) -> None:
        state = load(STATE)
        self.assertEqual("APPROVED", state["status"])
        self.assertEqual("C2AR-WP7-IMPLEMENTATION", state["completed_packet"])
        self.assertEqual("C2AR-G7A", state["completed_gate"])
        self.assertEqual("C2AR-WP8-GATE-PREPARATION", state["active_packet"])
        self.assertEqual("CEAR-G8", state["active_gate"])
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual("NOT_GRANTED", state["authority"]["parent_context_resolver"])
        self.assertEqual("UNCHANGED_READ_ONLY", state["authority"]["active_c2"])
        self.assertEqual([], state["blockers"])


if __name__ == "__main__":
    unittest.main()
