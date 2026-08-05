from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp10"
RECEIPT = BASE / "C2AR_WP10_DISPOSITION_EVIDENCE_INTEGRATION_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_WP10_DISPOSITION_EVIDENCE_INTEGRATED_STATE_v0_3.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class C2ARWP10DispositionEvidenceIntegrationTests(unittest.TestCase):
    def test_receipt_binds_exact_retained_branch_integration(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(322, receipt["source_pull_request"])
        self.assertEqual(319, receipt["retained_parent_pull_request"])
        self.assertEqual(
            "a02d049d444869a6309e7fc6b69cc95a7ca80929",
            receipt["source_final_head"],
        )
        self.assertEqual(
            "525b754377cbea65edb15ec39c5e17e4a15a70b8",
            receipt["squash_merge_commit"],
        )
        self.assertEqual("COMPLETED_RETAINED_BRANCH_ONLY", receipt["integration_result"])
        self.assertTrue(all(item["result"] == "PASS" for item in receipt["assurance"]))
        self.assertFalse(receipt["main_changed"])
        self.assertFalse(receipt["active_c2_changed"])
        self.assertFalse(receipt["cear_g10_operator_decision_granted"])
        self.assertFalse(receipt["wp11_unlocked"])

    def test_state_routes_only_to_operator_local_compact_analysis(self) -> None:
        state = load(STATE)
        self.assertEqual("BLOCKED", state["status"])
        self.assertEqual("C2AR-WP10", state["current_packet"])
        self.assertEqual("C2AR-WP10-DISPOSITION-EVIDENCE", state["completed_subpacket"])
        self.assertEqual("CEAR-G10", state["current_gate"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual(
            "NOT_READY_OPERATOR_LOCAL_COMPACT_ANALYSIS_REQUIRED",
            state["decision_readiness"],
        )
        self.assertEqual(
            "CEAR-G10-COMPACT-DISPOSITION-EVIDENCE-001",
            state["blocker_id"],
        )
        self.assertEqual("COMPLETED", state["completed_preparation"]["full_replay_orchestration"])
        self.assertEqual("PENDING", state["completed_preparation"]["operator_local_compact_record"])
        self.assertEqual("CANDIDATE_NOT_ADMITTED", state["authority"]["discovery_method"])
        self.assertEqual("NONE", state["authority"]["rule_candidates"])
        self.assertEqual("UNCHANGED_READ_ONLY", state["authority"]["active_c2"])
        self.assertEqual("PROHIBITED", state["main_merge_status"])
        self.assertEqual("LOCKED", state["wp11_status"])
        self.assertEqual("OVC CONTINUE", state["exact_resume_command"])


if __name__ == "__main__":
    unittest.main()
