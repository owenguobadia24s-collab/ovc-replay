from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp9/CEAR_G9_ASSURANCE_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G9_FINAL_GATE_READY_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CEARG9AssuranceTests(unittest.TestCase):
    def test_receipt_binds_exact_pre_metadata_head_and_successful_assurance(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(315, receipt["pull_request"])
        self.assertEqual("8ef7efb131a87ee9304c8e41494d64980dbc875d", receipt["baseline_commit"])
        self.assertEqual("21a73ecbf45cb8d753f0cf5dc71c70b5d22d661f", receipt["assured_pre_metadata_head"])
        self.assertEqual(256, receipt["assurance"][0]["test_count"])
        self.assertTrue(all(item["result"] in {"PASS", "ZERO"} for item in receipt["assurance"]))
        self.assertTrue(all(value == "PASS" for value in receipt["gate_policy_results"].values()))
        self.assertEqual("PASS", receipt["qa_recommendation"])
        self.assertEqual([], receipt["blocking_warnings"])
        self.assertEqual([], receipt["unresolved_issues"])
        self.assertEqual("NONE", receipt["active_authority_effect"])
        self.assertEqual("PR_315_REMAINS_UNMERGED_PENDING_OPERATOR_DECISION", receipt["stop_boundary"])

    def test_final_state_requires_operator_and_prohibits_merge(self) -> None:
        state = load(STATE)
        self.assertEqual("GATE_READY", state["status"])
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual("OVC APPROVE CEAR-G9 PASS", state["exact_approval_command"])
        self.assertEqual("BOUND_BY_PR_315_FINAL_HEAD", state["candidate_commit"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["consumer_eligibility_policy"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["denominator_policy"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["overlap_adjustment_policy"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["numeric_staleness_threshold"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["global_quality_gating"])
        self.assertEqual("NONE", state["current_authority"]["rule_theory"])
        self.assertEqual("NONE", state["current_authority"]["release_publication_validation"])
        self.assertEqual("PROHIBITED_PENDING_OPERATOR_DECISION", state["merge_status"])
        self.assertEqual("C2AR-WP9-IMPLEMENTATION", state["next_packet_on_pass"])
        self.assertEqual("CEAR-G10", state["next_reserved_gate"])
        self.assertEqual([], state["blocking_warnings"])
        self.assertEqual([], state["unresolved_issues"])


if __name__ == "__main__":
    unittest.main()
