from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp10"
ASSURANCE = BASE / "C2AR_WP10_DISPOSITION_EVIDENCE_ASSURANCE_RECEIPT.json"
QA = BASE / "C2AR_WP10_DISPOSITION_EVIDENCE_FINAL_QA_PACKET.json"
DECISION = BASE / "C2AR_WP10_DISPOSITION_EVIDENCE_DELEGATED_DECISION.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_WP10_DISPOSITION_EVIDENCE_ASSURED_STATE_v0_3.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class C2ARWP10DispositionEvidenceAssuranceTests(unittest.TestCase):
    def test_assurance_and_qa_bind_exact_passing_head(self) -> None:
        assurance = load(ASSURANCE)
        qa = load(QA)
        self.assertEqual(322, assurance["pull_request"])
        self.assertEqual(
            "b856a32b380ea44f344587484d33888396a809f6",
            assurance["assured_pre_metadata_head"],
        )
        self.assertEqual(286, assurance["assurance"][0]["test_count"])
        self.assertTrue(
            all(item["result"] in {"PASS", "ZERO"} for item in assurance["assurance"])
        )
        self.assertEqual("PASS", qa["status"])
        self.assertEqual(286, qa["tests"]["canonical_repository_suite"]["test_count"])
        self.assertEqual(0, qa["tests"]["unresolved_review_threads"])
        self.assertEqual(
            "PASS_TOOLING_PACKET_PRESERVE_CEAR_G10_OPERATOR_GATE",
            qa["qa_recommendation"],
        )
        self.assertEqual("NONE", qa["reserved_authority_effect"])
        self.assertEqual("PROHIBITED", qa["main_merge_recommendation"])

    def test_delegated_decision_and_state_preserve_cear_g10_boundary(self) -> None:
        decision = load(DECISION)
        state = load(STATE)
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual(
            "DELEGATED_APPROVED_PLAN_AUTO_EXECUTABLE_SCOPE",
            decision["decision_authority"],
        )
        self.assertEqual("RETAINED_PR_319_BRANCH_ONLY", decision["integration_scope"])
        self.assertEqual("PROHIBITED", decision["main_merge_authority"])
        self.assertIn("DISCOVERY_METHOD_ADMISSION", decision["explicitly_not_granted"])
        self.assertIn("RULE_CANDIDATE_PASS", decision["explicitly_not_granted"])
        self.assertEqual("APPROVED", state["status"])
        self.assertEqual("C2AR-WP10", state["current_packet"])
        self.assertEqual("CEAR-G10", state["current_gate"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual(
            "NOT_READY_OPERATOR_LOCAL_COMPACT_ANALYSIS_REQUIRED",
            state["decision_readiness"],
        )
        self.assertEqual("CANDIDATE_NOT_ADMITTED", state["authority"]["discovery_method"])
        self.assertEqual("NONE", state["authority"]["rule_candidates"])
        self.assertEqual("UNCHANGED_READ_ONLY", state["authority"]["active_c2"])
        self.assertEqual("PROHIBITED", state["main_merge_status"])
        self.assertEqual("LOCKED", state["wp11_status"])
        self.assertEqual("OVC CONTINUE", state["exact_resume_command"])


if __name__ == "__main__":
    unittest.main()
