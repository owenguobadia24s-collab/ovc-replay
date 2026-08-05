from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp9-implementation/C2AR_G9A_MERGE_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_WP9_MERGED_STATE_v0_3.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class C2ARG9AMergeReceiptTests(unittest.TestCase):
    def test_receipt_binds_final_head_merge_and_assurance(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(317, receipt["pull_request"])
        self.assertEqual("a00a050f2beef8acbc19edcb211c16d8ac7c6187", receipt["final_head"])
        self.assertEqual("95e5bac94c49464b10c066a261b36c8a7429d11d", receipt["squash_merge_commit"])
        self.assertTrue(all(item["result"] in {"PASS", "ZERO"} for item in receipt["final_assurance"]))
        self.assertEqual("SHADOW_FROZEN_READ_ONLY", receipt["merged_boundary"]["computability"])
        self.assertEqual("INACTIVE_NONCANONICAL_ONLY", receipt["merged_boundary"]["consumer_policy_evaluation"])
        self.assertEqual("UNCHANGED", receipt["merged_boundary"]["active_c2"])
        self.assertEqual([], receipt["external_artifacts"])
        self.assertEqual("CEAR-G10", receipt["next_gate"])
        self.assertEqual("OPERATOR_REQUIRED", receipt["next_gate_class"])

    def test_state_completes_wp9_and_exposes_only_bounded_wp10_research(self) -> None:
        state = load(STATE)
        self.assertEqual("0.3-REVISED", state["plan_version"])
        self.assertEqual("COMPLETED", state["status"])
        self.assertEqual("C2AR-WP9-IMPLEMENTATION", state["completed_packet"])
        self.assertEqual("95e5bac94c49464b10c066a261b36c8a7429d11d", state["merge_commit"])
        self.assertEqual("C2AR-WP10", state["current_packet"])
        self.assertEqual("CEAR-G10", state["current_gate"])
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual("OPERATOR_REQUIRED", state["authority_required"])
        authority = state["wp10_execution_authority"]
        self.assertEqual("AUTO_EXECUTABLE_RESEARCH_EVIDENCE", authority["neutral_fingerprints"])
        self.assertEqual("AUTO_EXECUTABLE_CANDIDATE_ONLY", authority["restricted_declarative_rule_compilation"])
        self.assertEqual("OPERATOR_REQUIRED_AT_CEAR_G10", authority["discovery_method_and_candidate_dispositions"])
        boundaries = state["part_10_boundaries"]
        self.assertTrue(boundaries["complete_neutral_population_required"])
        self.assertEqual("PROHIBITED", boundaries["legacy_seed_filter_score_stop_promote"])
        self.assertEqual("PROHIBITED", boundaries["outcome_validation_profitability_dependencies"])
        self.assertEqual("NONE", boundaries["selector_event_episode_semantic_authority"])
        self.assertEqual([], state["blockers"])


if __name__ == "__main__":
    unittest.main()
