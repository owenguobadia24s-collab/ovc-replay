from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr1"
ASSESSMENT = BASE / "PD_JUNE_MDR_CORR1_OPERATOR_UPLOAD_ASSESSMENT.json"
GAPS = BASE / "PD_JUNE_MDR_CORR1_EVIDENCE_GAP_MANIFEST.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"


class PDJuneMDRCorr1OperatorUploadAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
        cls.gaps = json.loads(GAPS.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_available_manifest_members_are_exactly_hash_verified(self) -> None:
        upload = self.assessment["operator_upload"]
        self.assertEqual(upload["manifest_file_count"], 21)
        self.assertEqual(upload["manifest_members_available_and_hash_verified"], 14)
        self.assertEqual(upload["manifest_members_missing"], 7)
        self.assertEqual(
            self.assessment["exact_hash_verification"]["status"],
            "PASS_14_OF_14_AVAILABLE_MEMBERS_MATCH_DECLARED_MANIFEST_HASH_AND_SIZE",
        )

    def test_supplied_c1_corpus_is_pre_corrective(self) -> None:
        c1 = self.assessment["c1_formula_assurance"]
        self.assertEqual(c1["same_bar_non_wick_invariants"], "PASS_602_OF_602_RECORDS")
        self.assertEqual(c1["wick_balance_total_record_count"], 602)
        self.assertEqual(c1["wick_balance_exact_match_count"], 13)
        self.assertEqual(c1["wick_balance_opposite_sign_count"], 589)
        self.assertEqual(
            c1["verdict"],
            "FAIL_SUPPLIED_C1_CORPUS_IS_PRE_CORRECTIVE_DEFECTIVE_HELPER_OUTPUT",
        )

    def test_release_identity_does_not_match_corrective_pilot(self) -> None:
        lineage = self.assessment["lineage_assessment"]
        self.assertEqual(lineage["supplied_c2_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1")
        self.assertEqual(lineage["reviewed_pilot_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")
        self.assertEqual(
            lineage["status"],
            "FAIL_SUPPLIED_RPS_WP3_V1_OUTPUT_IS_NOT_THE_CORRECTIVE_C1C_G5_V2_PILOT_EVIDENCE",
        )

    def test_pretrigger_blocker_remains_for_entirely_15m_sample(self) -> None:
        sample = self.assessment["review_sample_relevance"]
        self.assertEqual(sample["reviewed_unit_count"], 26)
        self.assertEqual(sample["reviewed_clock"], "15M_ONLY")
        self.assertEqual(sample["history_dependent_unit_count"], 11)
        self.assertEqual(sample["history_dependent_ask_count"], 6)
        self.assertEqual(sample["history_dependent_bid_count"], 5)
        self.assertEqual(sample["supplied_2h_transition_relevance"], "NONE_TO_THE_26_UNIT_CLAIM_REVIEW_SAMPLE")

    def test_gap_and_programme_state_fail_closed(self) -> None:
        self.assertEqual(self.assessment["overall_verdict"], "NOT_ESTABLISHED_BLOCKER_REMAINS")
        self.assertEqual(self.gaps["status"], "BLOCKED_CORRECTIVE_V2_EVIDENCE_REQUIRED")
        self.assertEqual(
            {item["code"] for item in self.gaps["open_blockers"]},
            {"PD-JUNE-MDR-003", "PD-JUNE-MDR-004", "PD-JUNE-MDR-006"},
        )
        self.assertEqual(self.state["status"], "BLOCKED")
        self.assertEqual(self.state["operator_upload_c1_records"], 602)
        self.assertEqual(
            self.state["operator_upload_wick_balance_assurance"],
            "FAIL_589_OF_602_OPPOSITE_SIGN_13_ZERO_MATCHES",
        )
        self.assertEqual(self.state["next_gate"], "PD-JUNE-MDR-G1_RETURN_NOT_READY")
        self.assertEqual(self.state["second_june_replay"], "DENIED_NOT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
