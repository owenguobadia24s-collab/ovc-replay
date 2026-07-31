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

    def test_supplied_c1_corpus_and_identity_defects_remain_preserved(self) -> None:
        c1 = self.assessment["c1_formula_assurance"]
        self.assertEqual(c1["wick_balance_total_record_count"], 602)
        self.assertEqual(c1["wick_balance_opposite_sign_count"], 589)
        lineage = self.assessment["lineage_assessment"]
        self.assertEqual(lineage["supplied_c2_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1")
        self.assertEqual(lineage["reviewed_pilot_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")

    def test_initial_pretrigger_gap_is_preserved_as_historical_evidence(self) -> None:
        sample = self.assessment["review_sample_relevance"]
        self.assertEqual(sample["reviewed_unit_count"], 26)
        self.assertEqual(sample["history_dependent_unit_count"], 11)
        self.assertEqual(self.assessment["overall_verdict"], "NOT_ESTABLISHED_BLOCKER_REMAINS")

    def test_later_exact_evidence_and_final_defer_are_recorded(self) -> None:
        self.assertEqual(self.gaps["status"], "GATE_READY_CONTROL_AND_AGREEMENT_EVIDENCE_REQUIRED")
        self.assertEqual(self.repro["population_state_reproduction"]["exact_core_match_count"], 1144)
        self.assertEqual(self.repro["review_claim_evidence"]["history_dependent_exact_reproduction_count"], 11)
        self.assertEqual(self.state["status"], "COMPLETED")
        self.assertEqual(self.state["decision"], "DEFER")
        self.assertEqual(self.state["decision_authority"], "OPERATOR")
        self.assertEqual(self.state["review_status"], "COMPLETED")
        self.assertEqual(self.state["merge_status"], "PASS_SQUASH_MERGED_TO_MAIN")
        self.assertIsNone(self.state["next_gate"])
        self.assertIsNone(self.state["next_packet"])
        self.assertEqual(self.state["second_june_replay"], "DENIED_NOT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
