from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ASSESSMENT = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-ra1" / "PD_JUNE_2026_OPERATOR_REVIEW_AND_MARKET_DESCRIPTION_ASSESSMENT.json"
QA = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-ra1" / "PD_JUNE_RA1_QA_PACKET.json"
CORR2_DECISION = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr2" / "PD_JUNE_MDR_G1_CORR2_OPERATOR_DECISION.json"
MERGE_RECEIPT = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr2" / "PD_JUNE_MDR_G1_CORR2_MERGE_RECEIPT.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"


class PDJune2026ReviewAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
        cls.qa = json.loads(QA.read_text(encoding="utf-8"))
        cls.corr2_decision = json.loads(CORR2_DECISION.read_text(encoding="utf-8"))
        cls.merge_receipt = json.loads(MERGE_RECEIPT.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_exact_june_machine_counts_and_reproducibility(self) -> None:
        machine = self.assessment["machine_operation"]
        self.assertEqual(machine["c2_states"], 1144)
        self.assertEqual(machine["transitions"], 7032)
        self.assertEqual(machine["trigger_events"], 208)
        self.assertEqual(machine["candidates"], 208)
        self.assertEqual(machine["queue_promoted"], 6)
        self.assertEqual(machine["queue_suppressed"], 202)
        self.assertEqual(machine["verdict"], "PASS_REPRODUCIBLE_FOR_EXACT_GOVERNED_INPUT")

    def test_historical_reliability_assessment_remains_not_established(self) -> None:
        dimensions = self.assessment["reliability_dimensions"]
        self.assertEqual(dimensions["computational_reproducibility"]["verdict"], "PASS")
        self.assertEqual(dimensions["lineage_and_evidence_integrity"]["verdict"], "PASS")
        self.assertEqual(dimensions["external_market_description_validity"]["verdict"], "NOT_ESTABLISHED")
        self.assertEqual(dimensions["population_level_consistency"]["verdict"], "NOT_ESTABLISHED")
        self.assertEqual(self.assessment["overall_answer"]["verdict"], "NOT_ESTABLISHED")

    def test_final_operator_defer_and_merge_close_without_new_authority(self) -> None:
        self.assertEqual(self.corr2_decision["decision"], "DEFER")
        self.assertEqual(self.corr2_decision["decision_authority"], "OPERATOR")
        self.assertIsNone(self.corr2_decision["next_packet"])
        self.assertEqual(self.merge_receipt["merge_result"], "PASS_SQUASH_MERGED_TO_MAIN")
        self.assertEqual(self.state["status"], "COMPLETED")
        self.assertEqual(self.state["decision"], "DEFER")
        self.assertEqual(self.state["review_status"], "COMPLETED")
        self.assertEqual(self.state["merge_commit"], "306e449acdaddbb0131fd01aca6098dd8ab0b7ef")
        self.assertIsNone(self.state["next_gate"])
        self.assertIsNone(self.state["next_packet"])
        self.assertEqual(self.state["canonical_2021_2023_discovery"], "DEFERRED_NOT_AUTHORISED")
        self.assertEqual(self.state["second_june_replay"], "DENIED_NOT_REQUIRED")

    def test_historical_qa_remains_preserved(self) -> None:
        self.assertEqual(self.qa["qa_status"], "PASS_ASSESSMENT_BLOCKED_NEXT_PACKET")
        self.assertEqual(self.qa["recommendation"], "PASS_READ_ONLY_ASSESSMENT_AND_PRESERVE_NOT_ESTABLISHED_VERDICT")


if __name__ == "__main__":
    unittest.main()
