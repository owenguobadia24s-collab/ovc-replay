from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp10"
RECEIPT = BASE / "CEAR_G10_BLOCKED_ASSURANCE_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G10_FINAL_BLOCKED_STATE_v0_3.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CEARG10BlockedAssuranceTests(unittest.TestCase):
    def test_receipt_binds_passing_head_and_preserves_blocker(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(319, receipt["pull_request"])
        self.assertEqual("99f8926e9fa015e8096dfb363ae13563c094387d", receipt["assured_pre_metadata_head"])
        self.assertEqual(280, receipt["assurance"][0]["test_count"])
        self.assertTrue(all(item["result"] in {"PASS", "ZERO"} for item in receipt["assurance"]))
        self.assertEqual("PASS", receipt["verified_results"]["functional_discovery_preparation"])
        self.assertEqual("PASS", receipt["verified_results"]["no_outcome_validation_or_legacy_seed_dependencies"])
        self.assertEqual("BLOCKED", receipt["verified_results"]["required_real_vnext_population_available"])
        self.assertEqual("NOT_EVALUABLE", receipt["verified_results"]["real_functional_and_rule_candidate_dispositions"])
        self.assertEqual("BLOCK", receipt["qa_recommendation"])
        self.assertEqual(["CEAR-G10-BLOCKER-001"], receipt["unresolved_issues"])
        self.assertEqual("PROHIBITED_WHILE_BLOCKED", receipt["merge_authority"])
        self.assertEqual("NONE", receipt["active_authority_effect"])

    def test_final_state_is_blocked_and_wp11_remains_locked(self) -> None:
        state = load(STATE)
        self.assertEqual("0.3-REVISED", state["plan_version"])
        self.assertEqual("BLOCKED", state["status"])
        self.assertEqual("C2AR-WP10", state["current_packet"])
        self.assertEqual("CEAR-G10", state["current_gate"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("NOT_READY_REQUIRED_ARTIFACT_BLOCKER", state["decision_readiness"])
        self.assertEqual("BLOCK", state["recommended_disposition"])
        self.assertEqual("99f8926e9fa015e8096dfb363ae13563c094387d", state["assured_pre_metadata_head"])
        self.assertEqual(280, state["assurance"][0]["test_count"])
        self.assertTrue(all(item["result"] in {"PASS", "ZERO"} for item in state["assurance"]))
        self.assertEqual("BLOCKED", state["completed_preparation"]["real_vnext_population_execution"])
        self.assertEqual("CANDIDATE_NOT_ADMITTED", state["authority"]["discovery_method"])
        self.assertEqual("NONE", state["authority"]["real_functional_candidates"])
        self.assertEqual("NONE", state["authority"]["real_rule_candidates"])
        self.assertEqual("NONE", state["authority"]["research_consumer_permission"])
        self.assertEqual("UNCHANGED_READ_ONLY", state["authority"]["active_c2"])
        self.assertEqual("PROHIBITED_WHILE_BLOCKED", state["merge_status"])
        self.assertEqual("LOCKED", state["wp11_status"])
        self.assertEqual("OVC CONTINUE", state["exact_resume_command"])
        self.assertEqual(["CEAR-G10-BLOCKER-001"], state["blockers"])


if __name__ == "__main__":
    unittest.main()
