from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp9-implementation"
RECEIPT = BASE / "C2AR_G9A_ASSURANCE_RECEIPT.json"
DECISION = BASE / "C2AR_G9A_DELEGATED_DECISION.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_G9A_APPROVED_STATE_v0_3.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class C2ARG9ADecisionTests(unittest.TestCase):
    def test_assurance_receipt_binds_exact_head_and_complete_pass(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(317, receipt["pull_request"])
        self.assertEqual("5e46d1e3a620c302f0d2592a929295b784b89178", receipt["assured_pre_decision_head"])
        self.assertEqual(269, receipt["assurance"][0]["test_count"])
        self.assertTrue(all(item["result"] in {"PASS", "ZERO"} for item in receipt["assurance"]))
        self.assertTrue(all(value == "PASS" for value in receipt["acceptance"].values()))
        self.assertEqual("PASS", receipt["qa_recommendation"])
        self.assertEqual([], receipt["blocking_warnings"])
        self.assertEqual([], receipt["unresolved_issues"])
        self.assertEqual("NONE", receipt["active_authority_delta"])

    def test_delegated_pass_is_inside_operator_approved_delta(self) -> None:
        decision = load(DECISION)
        self.assertEqual("C2AR-G9A.DELEGATED.PASS.20260805T085100+0100", decision["decision_id"])
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("DELEGATED_BY_APPROVED_PLAN_AND_CEAR_G9_OPERATOR_PASS", decision["decision_authority"])
        self.assertEqual("CEAR-G9.OPERATOR.PASS.20260805T081600+0100", decision["operator_authority"])
        self.assertIn("SHADOW_FROZEN_READ_ONLY_PER_COMPONENT_COMPUTABILITY", decision["approved_delta"])
        self.assertIn("CLAIM_SPECIFIC_RAW_PRESERVING_OVERLAP_REPORTS", decision["approved_delta"])
        self.assertTrue(all(item["result"] in {"PASS", "ZERO"} for item in decision["tests"]))
        self.assertEqual("PASS", decision["qa_recommendation"])
        self.assertEqual([], decision["blockers"])
        denied = set(decision["explicitly_not_granted"])
        self.assertIn("ACTIVE_OR_CANONICAL_CONSUMER_POLICY", denied)
        self.assertIn("NUMERIC_STALENESS_OR_FRESHNESS_THRESHOLD", denied)
        self.assertIn("CANONICAL_OVERLAP_WEIGHTING_DEDUPLICATION_OR_ADJUSTMENT", denied)
        self.assertIn("SEMANTIC_EVENT_EPISODE_OR_RULE_AUTHORITY", denied)
        self.assertIn("VALIDATION_CONSUMPTION", denied)
        self.assertIn("PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION", denied)

    def test_approved_state_routes_only_to_operator_required_cear_g10(self) -> None:
        state = load(STATE)
        self.assertEqual("0.3-REVISED", state["plan_version"])
        self.assertEqual("APPROVED", state["status"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("C2AR-G9A.DELEGATED.PASS.20260805T085100+0100", state["delegated_decision_id"])
        self.assertFalse(state["implementation"]["active"])
        self.assertFalse(state["implementation"]["canonical"])
        authority = state["authority"]
        self.assertEqual("NONE", authority["active_consumer"])
        self.assertEqual("NONE", authority["numeric_staleness_threshold"])
        self.assertEqual("NONE", authority["canonical_overlap_adjustment"])
        self.assertEqual("NONE", authority["global_quality_gating"])
        self.assertEqual("UNCHANGED_READ_ONLY", authority["active_c2"])
        self.assertEqual("NONE", authority["semantic_event_episode_rule"])
        self.assertEqual("NONE", authority["publication_validation"])
        self.assertEqual("NONE", authority["probability_risk_exposure_execution"])
        self.assertEqual("C2AR-WP10", state["next_packet"])
        self.assertEqual("CEAR-G10", state["next_gate"])
        self.assertEqual("OPERATOR_REQUIRED", state["next_gate_class"])
        self.assertEqual([], state["blockers"])
        self.assertIn("APPROVED_PENDING_EXACT_FINAL_HEAD_ASSURANCE_AND_SQUASH_MERGE", state["merge_status"])


if __name__ == "__main__":
    unittest.main()
