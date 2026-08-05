from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RELEASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp8"
QA = RELEASE / "C2AR_G8A_QA.json"
GATE = RELEASE / "C2AR_G8A_GATE_PACKET.json"
DECISION = RELEASE / "C2AR_G8A_DELEGATED_DECISION.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_WP8_IMPLEMENTED_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class C2ARG8ADecisionTests(unittest.TestCase):
    def test_qa_passes_all_conditions_and_preserves_corrective_history(self) -> None:
        qa = load(QA)
        self.assertEqual("PASS", qa["recommendation"])
        self.assertTrue(all(item["result"] == "PASS" for item in qa["findings"]))
        self.assertEqual("RESOLVED", qa["corrective_history"][0]["result"])
        self.assertEqual(245, qa["tests"][0]["test_count"])
        self.assertEqual([], qa["blocking_warnings"])
        self.assertEqual([], qa["unresolved_issues"])
        self.assertEqual("NONE", qa["active_authority_effect"])

    def test_gate_is_auto_ratifable_inside_exact_operator_authority(self) -> None:
        gate = load(GATE)
        self.assertEqual("DELEGATED_AUTO_RATIFIABLE", gate["decision_authority"])
        self.assertEqual("CEAR-G8.OPERATOR.PASS.20260805T062900+0100", gate["operator_authority"])
        self.assertEqual("PASS", gate["recommended_decision"])
        self.assertTrue(all(item["result"] == "PASS" for item in gate["acceptance_conditions"]))
        self.assertEqual("NONE_BEYOND_OPERATOR_APPROVED_INACTIVE_NONCANONICAL_SHADOW_IMPLEMENTATION", gate["authority_delta"])
        self.assertEqual([], gate["blocking_warnings"])
        self.assertEqual([], gate["unresolved_issues"])

    def test_delegated_pass_does_not_grant_reserved_authority(self) -> None:
        decision = load(DECISION)
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("DELEGATED_BY_CEAR_G8_OPERATOR_PASS", decision["decision_authority"])
        self.assertEqual("SQUASH", decision["merge_method"])
        self.assertEqual([], decision["blocking_warnings"])
        self.assertEqual([], decision["unresolved_issues"])
        state = load(STATE)
        self.assertEqual("APPROVED", state["status"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("SHADOW_FROZEN_READ_ONLY_INACTIVE_NONCANONICAL", state["authority"]["parent_context_resolver"])
        for key in (
            "active_parent_selection",
            "hidden_selection",
            "universal_staleness_threshold",
            "semantic_event_episode",
            "c2e_c2_5",
            "consumer_denominator_overlap",
            "rule_theory",
            "release_publication_validation",
            "probability_risk_exposure_execution",
        ):
            self.assertEqual("NONE", state["authority"][key])
        self.assertEqual("UNCHANGED_READ_ONLY", state["authority"]["active_c2"])
        self.assertEqual("APPROVED_PENDING_EXACT_FINAL_HEAD_ASSURANCE_AND_SQUASH_MERGE", state["merge_status"])
        self.assertEqual("CEAR-G9", state["next_reserved_gate"])


if __name__ == "__main__":
    unittest.main()
