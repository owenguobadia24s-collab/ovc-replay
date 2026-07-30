from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ASSESSMENT = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-ra1" / "PD_JUNE_2026_OPERATOR_REVIEW_AND_MARKET_DESCRIPTION_ASSESSMENT.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"
QA = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-ra1" / "PD_JUNE_RA1_QA_PACKET.json"
PLAN = ROOT / "docs" / "plans" / "research_operations" / "OVC_PD_JUNE_2026_OPERATOR_REVIEW_AND_MARKET_DESCRIPTION_ASSURANCE_PLAN_v0_1.md"
CONTRACT = ROOT / "contracts" / "research_operations" / "pattern_discovery" / "PD_MARKET_DESCRIPTION_RELIABILITY_REVIEW_CONTRACT_v0_1.md"
DECISION = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-ra1" / "PD_JUNE_RA1_DELEGATED_DECISION.md"
CORR1_DECISION = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr1" / "PD_JUNE_MDR_G1_CORR1_OPERATOR_DECISION.json"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_2026_review_assessment_v0_1.schema.json"


class PDJune2026ReviewAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
        self.state = json.loads(STATE.read_text(encoding="utf-8"))
        self.qa = json.loads(QA.read_text(encoding="utf-8"))
        self.corr1_decision = json.loads(CORR1_DECISION.read_text(encoding="utf-8"))

    def test_required_packet_files_exist(self) -> None:
        for path in (ASSESSMENT, STATE, QA, PLAN, CONTRACT, DECISION, CORR1_DECISION, SCHEMA):
            self.assertTrue(path.is_file(), path)

    def test_exact_june_machine_counts_and_reproducibility(self) -> None:
        machine = self.assessment["machine_operation"]
        self.assertEqual(machine["c2_states"], 1144)
        self.assertEqual(machine["transitions"], 7032)
        self.assertEqual(machine["trigger_events"], 208)
        self.assertEqual(machine["candidates"], 208)
        self.assertEqual(machine["queue_promoted"], 6)
        self.assertEqual(machine["queue_suppressed"], 202)
        self.assertEqual(machine["verdict"], "PASS_REPRODUCIBLE_FOR_EXACT_GOVERNED_INPUT")
        self.assertTrue(self.assessment["source_evidence"]["deterministic_rerun_match"])
        self.assertTrue(self.assessment["source_evidence"]["signed_hash_chain_verified"])

    def test_initial_operator_review_distribution_is_exact(self) -> None:
        review = self.assessment["initial_v2_operator_review"]
        self.assertEqual(review["decision_count"], 6)
        self.assertEqual(
            review["distribution"],
            {
                "WORKFLOW_ACCEPTED": 1,
                "FLAG_WORKFLOW_DEFECT": 1,
                "FLAG_UI_FRICTION": 1,
                "DEFER_PILOT_OBJECT": 2,
                "REJECT_PILOT_OBJECT": 1,
            },
        )
        self.assertEqual(review["clean_acceptance_rate"], "1/6")
        self.assertEqual(review["qualified_or_nonaccepted_rate"], "5/6")

    def test_corrective_chain_preserves_chronology_rejection_and_nonpromotion(self) -> None:
        results = self.assessment["corrective_review_chain"]["corr2_results"]
        chronology = next(item for item in results if item["candidate_window_id"].endswith("4f41e21b6cd075e0fdbc40e4"))
        structural = next(item for item in results if item["candidate_window_id"].endswith("bab63b935155e4d9033aed81"))
        self.assertEqual(chronology["final_disposition"], "REJECT_PILOT_OBJECT")
        self.assertEqual(chronology["finding_code"], "PD-REJECT-CORR2-CHRONOLOGY-INCONSISTENT-001")
        self.assertEqual(structural["corr3_final_disposition"], "WORKFLOW_ACCEPTED")
        self.assertIn("NOT_CANDIDATE_OR_MARKET_SEMANTIC_APPROVAL", structural["meaning"])
        self.assertEqual(self.assessment["corrective_review_chain"]["remaining_deferred_object_count"], 0)

    def test_historical_market_description_reliability_fails_closed(self) -> None:
        dimensions = self.assessment["reliability_dimensions"]
        self.assertEqual(dimensions["computational_reproducibility"]["verdict"], "PASS")
        self.assertEqual(dimensions["lineage_and_evidence_integrity"]["verdict"], "PASS")
        self.assertEqual(dimensions["review_workflow_reliability"]["verdict"], "CONDITIONAL_PASS_AFTER_CORRECTIONS")
        self.assertEqual(dimensions["external_market_description_validity"]["verdict"], "NOT_ESTABLISHED")
        self.assertEqual(dimensions["population_level_consistency"]["verdict"], "NOT_ESTABLISHED")
        self.assertEqual(self.assessment["overall_answer"]["verdict"], "NOT_ESTABLISHED")

    def test_no_canonical_discovery_or_replay_authority(self) -> None:
        authority = self.assessment["authority"]
        self.assertEqual(self.assessment["operator_boundary"]["canonical_2021_2023_discovery"], "DEFERRED_NOT_REQUESTED")
        self.assertEqual(self.assessment["operator_boundary"]["second_june_replay"], "DENIED_NOT_REQUIRED")
        for key in (
            "canonical_discovery_processing", "canonical_append", "provider_intake",
            "machine_replay", "selector_or_release_mutation", "r2_publication",
        ):
            self.assertIn(authority[key], {"DENIED", "DEFERRED_NOT_AUTHORISED"})
        for key in (
            "trigger_or_model_change", "semantic_or_candidate_promotion", "probability",
            "risk", "exposure", "trading", "execution", "agent_write",
        ):
            self.assertEqual(authority[key], "NONE")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")

    def test_prior_blocker_progresses_through_corr1_into_corr2_review(self) -> None:
        next_packet = self.assessment["next_packet"]
        self.assertEqual(next_packet["packet_id"], "PD-JUNE-MDR-WP1")
        self.assertEqual(next_packet["status"], "BLOCKED_EXTERNAL_OPERATOR_LOCAL_ARTIFACT_BINDING_REQUIRED")
        self.assertGreaterEqual(len(self.assessment["missing_evidence_for_claim_level_assurance"]), 7)
        self.assertEqual(self.corr1_decision["decision"], "DEFER")
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["packet_id"], "PD-JUNE-MDR-CORR2-CONTROL-AND-AGREEMENT-ASSURANCE")
        self.assertEqual(self.state["overall_verdict"], "NOT_ESTABLISHED")
        self.assertEqual(self.state["source_to_c2_v2_binding"], "PASS_EXPLICIT_CARRY_FORWARD_AND_CORRECTIVE_RUN_BINDING")
        self.assertEqual(self.state["timeline_chronology"], "PASS_208_OF_208_CORRECTED_READ_ONLY_PROJECTION")
        self.assertEqual(self.state["population_state_reproduction"], "PASS_1144_OF_1144")
        self.assertEqual(self.state["pre_trigger_history"], "PASS_11_OF_11_HISTORY_DEPENDENT_UNITS")
        self.assertEqual(self.state["review_status"], "OPERATOR_INPUT_REQUIRED")
        self.assertEqual(self.state["next_gate"], "PD-JUNE-MDR-G1")
        self.assertEqual(self.state["next_packet_status"], "WAITING_OPERATOR_REVIEW_ARTIFACT")

    def test_qa_recommends_assessment_pass_not_market_validity_pass(self) -> None:
        self.assertEqual(self.qa["qa_status"], "PASS_ASSESSMENT_BLOCKED_NEXT_PACKET")
        self.assertEqual(self.qa["recommendation"], "PASS_READ_ONLY_ASSESSMENT_AND_PRESERVE_NOT_ESTABLISHED_VERDICT")
        self.assertEqual(self.qa["unresolved_issues"][0]["code"], "PD-JUNE-MDR-BLOCK-001")
        self.assertTrue(all(check["result"] == "PASS" for check in self.qa["checks"]))


if __name__ == "__main__":
    unittest.main()
