from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr1"
ASSESSMENT = BASE / "PD_JUNE_MDR_CORR1_OPERATOR_UPLOAD_ASSESSMENT.json"
GAPS = BASE / "PD_JUNE_MDR_CORR1_EVIDENCE_GAP_MANIFEST.json"
REPRO = BASE / "PD_JUNE_MDR_CORR1_CLAIM_TRIGGER_REPRODUCTION_SUMMARY.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"


class PDJuneMDRCorr1OperatorUploadAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
        cls.gaps = json.loads(GAPS.read_text(encoding="utf-8"))
        cls.repro = json.loads(REPRO.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_initial_available_manifest_members_remain_exactly_recorded(self) -> None:
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

    def test_historical_release_identity_mismatch_remains_preserved(self) -> None:
        lineage = self.assessment["lineage_assessment"]
        self.assertEqual(lineage["supplied_c2_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1")
        self.assertEqual(lineage["reviewed_pilot_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")
        self.assertEqual(
            lineage["status"],
            "FAIL_SUPPLIED_RPS_WP3_V1_OUTPUT_IS_NOT_THE_CORRECTIVE_C1C_G5_V2_PILOT_EVIDENCE",
        )

    def test_initial_pretrigger_gap_is_preserved_as_historical_evidence(self) -> None:
        sample = self.assessment["review_sample_relevance"]
        self.assertEqual(sample["reviewed_unit_count"], 26)
        self.assertEqual(sample["reviewed_clock"], "15M_ONLY")
        self.assertEqual(sample["history_dependent_unit_count"], 11)
        self.assertEqual(sample["history_dependent_ask_count"], 6)
        self.assertEqual(sample["history_dependent_bid_count"], 5)
        self.assertEqual(sample["supplied_2h_transition_relevance"], "NONE_TO_THE_26_UNIT_CLAIM_REVIEW_SAMPLE")
        self.assertEqual(self.assessment["overall_verdict"], "NOT_ESTABLISHED_BLOCKER_REMAINS")

    def test_later_exact_drive_evidence_progresses_into_operator_review(self) -> None:
        self.assertEqual(self.gaps["status"], "GATE_READY_CONTROL_AND_AGREEMENT_EVIDENCE_REQUIRED")
        self.assertEqual({item["code"] for item in self.gaps["open_blockers"]}, {"PD-JUNE-MDR-006"})
        self.assertEqual(self.repro["population_state_reproduction"]["exact_core_match_count"], 1144)
        self.assertEqual(self.repro["review_claim_evidence"]["history_dependent_exact_reproduction_count"], 11)
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["decision"], "DEFER")
        self.assertEqual(self.state["packet_id"], "PD-JUNE-MDR-CORR2-CONTROL-AND-AGREEMENT-ASSURANCE")
        self.assertEqual(self.state["operator_upload_c1_records"], 602)
        self.assertEqual(
            self.state["operator_upload_wick_balance_assurance"],
            "FAIL_589_OF_602_OPPOSITE_SIGN_13_ZERO_MATCHES_PRESERVED_AS_EVIDENCE",
        )
        self.assertEqual(self.state["review_status"], "OPERATOR_INPUT_REQUIRED")
        self.assertEqual(self.state["next_gate"], "PD-JUNE-MDR-G1")
        self.assertEqual(self.state["next_packet_status"], "WAITING_OPERATOR_REVIEW_ARTIFACT")
        self.assertEqual(self.state["second_june_replay"], "DENIED_NOT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
