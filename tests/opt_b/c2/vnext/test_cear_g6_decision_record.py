from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DECISION = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp6/CEAR_G6_OPERATOR_DECISION.json"
RECEIPT = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp6/CEAR_G6_AUTHORITY_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G6_APPROVED_STATE_v0_2.jsonc"


class CEARG6DecisionRecordTests(unittest.TestCase):
    def test_operator_pass_is_bound_to_lawful_post_wp5_5_main(self) -> None:
        decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("OVC APPROVE CEAR-G6 PASS", decision["operator_command"])
        self.assertEqual("86000a293aa255e19a2c5a4ab5656da94659beb2", decision["lawful_baseline_commit"])
        self.assertEqual("PASS_MERGED", decision["prerequisites"]["C2AR-G5.5"]["status"])
        self.assertFalse(decision["supersession"]["authority_delta_changed"])
        self.assertFalse(decision["supersession"]["force_push_used"])
        self.assertEqual([], decision["blocking_warnings"])
        self.assertEqual([], decision["unresolved_issues"])

    def test_approval_is_bounded_and_not_active(self) -> None:
        decision = json.loads(DECISION.read_text(encoding="utf-8"))
        denied = set(decision["explicitly_not_granted"])
        self.assertIn("ACTIVE_SELECTOR_OR_REPLACEMENT", denied)
        self.assertIn("NUMERIC_THRESHOLD_PARAMETER_OR_SCALE_SELECTION", denied)
        self.assertIn("CANONICAL_OR_R2_PUBLICATION", denied)
        self.assertIn("VALIDATION_CONSUMPTION", denied)
        self.assertIn("PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION", denied)
        self.assertEqual("NONE", decision["current_active_c2"]["mutation"])

    def test_authority_receipt_releases_only_after_merge(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual("APPROVED_PENDING_DECISION_PR_MERGE", receipt["authority_state"])
        self.assertEqual("DECISION_RECORD_MERGED_TO_MAIN_AND_EXACT_HEAD_CHECKS_PASS", receipt["implementation_release_condition"])
        self.assertTrue(all(value == "NONE" for value in receipt["active_authority_changes"].values()))

    def test_state_exposes_implementation_and_next_reserved_gate(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual("APPROVED_PENDING_MERGE", state["status"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("C2AR-WP6-IMPLEMENTATION", state["implementation"]["packet_id"])
        self.assertEqual("CEAR-G7", state["implementation"]["next_reserved_gate"])
        self.assertEqual("CLOSED_UNMERGED", state["superseded_gate"]["state"])
        self.assertEqual("NONE", state["superseded_gate"]["authority_effect"])
        active = (ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("SELECTOR.OPT-B.C2.GBPUSD.v2", active)
        self.assertIn("LOCKED_UNCONSUMED", active)


if __name__ == "__main__":
    unittest.main()
