from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp9/CEAR_G9_OPERATOR_DECISION.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G9_APPROVED_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CEARG9DecisionTests(unittest.TestCase):
    def test_operator_pass_is_exact_immutable_and_bounded(self) -> None:
        decision = load(DECISION)
        self.assertEqual("CEAR-G9.OPERATOR.PASS.20260805T081600+0100", decision["decision_id"])
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual(315, decision["gate_pr"])
        self.assertEqual("f5cc9deb4ed1f1e4c547b5fa6c1944aedbcc6da1", decision["assured_predecision_head"])
        self.assertEqual(
            "VERSIONED_INACTIVE_NONCANONICAL_SHADOW_COMPUTABILITY_DEPENDENCY_CONSUMER_DENOMINATOR_OVERLAP_AND_COMPARABILITY_IMPLEMENTATION_ONLY",
            decision["approved_delta"]["implementation_authority"],
        )
        self.assertEqual("COMPARABLE_TRANSITION_PAIRS", decision["approved_delta"]["transition_rate_unit"])
        self.assertIn("NO_NUMERIC_STALENESS_OR_FRESHNESS_THRESHOLD", decision["conditions"])
        self.assertIn("NO_CANONICAL_OVERLAP_WEIGHTING_DEDUPLICATION_OR_NUMERIC_ADJUSTMENT", decision["conditions"])
        denied = set(decision["explicitly_not_granted"])
        self.assertIn("ACTIVE_OR_CANONICAL_CONSUMER_ELIGIBILITY_POLICY", denied)
        self.assertIn("RULE_OR_THEORY_PROMOTION", denied)
        self.assertIn("VALIDATION_CONSUMPTION", denied)
        self.assertIn("PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION", denied)

    def test_approved_state_requires_merge_and_v03_binding_before_implementation(self) -> None:
        state = load(STATE)
        self.assertEqual("APPROVED", state["status"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("CEAR-G9.OPERATOR.PASS.20260805T081600+0100", state["operator_decision_id"])
        self.assertEqual("READY_AFTER_DECISION_MERGE_AND_PLAN_V0_3_BINDING", state["implementation_status"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["numeric_staleness_threshold"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["canonical_overlap_adjustment"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["global_quality_gating"])
        self.assertEqual("NONE", state["current_authority"]["rule_theory"])
        self.assertEqual("NONE", state["current_authority"]["release_publication_validation"])
        self.assertEqual("PENDING_AFTER_CEAR_G9_DECISION_MERGE", state["plan_revision_continuation"]["source_binding_status"])
        self.assertEqual(
            ["C2AR-WP9-IMPLEMENTATION", "C2AR-WP10", "C2AR-WP11"],
            state["plan_revision_continuation"]["remaining_work_governed_by_v0_3_after_ratification"],
        )
        self.assertEqual([], state["blockers"])
        self.assertIn("APPROVED_PENDING_EXACT_FINAL_HEAD_ASSURANCE_AND_SQUASH_MERGE", state["merge_status"])


if __name__ == "__main__":
    unittest.main()
