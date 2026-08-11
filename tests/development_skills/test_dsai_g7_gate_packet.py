from __future__ import annotations
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/releases/development-skills-architecture-v0-1/dsai-wp7"
class DSAIG7GatePacketTests(unittest.TestCase):
    def test_operator_packet_is_blocked_not_pass_and_grants_no_authority(self):
        packet=json.loads((BASE/"DSAI_G7_OPERATOR_DECISION_PACKET.json").read_text())
        self.assertEqual(packet["recommended_decision"],"BLOCK")
        self.assertEqual(packet["authority_effect"],"NONE")
        self.assertTrue(packet["proposed_delta"]["operator_required"])
        self.assertEqual(packet["current_authority"]["trusted_skills"],[])
        self.assertEqual(packet["acceptance_conditions"]["independent_human_adversarial_review"],"BLOCK")
        self.assertEqual(packet["acceptance_conditions"]["independent_reference_checks"],"BLOCK")
    def test_all_exact_candidate_qualifications_are_blocked_and_not_trusted(self):
        assessment=json.loads((BASE/"DSAI_G7_BLOCKED_QUALIFICATION_ASSESSMENT.json").read_text())
        self.assertEqual(assessment["overall_status"],"BLOCKED")
        self.assertEqual(assessment["evaluation_suite"]["status"],"BLOCK")
        self.assertEqual(set(assessment["evaluation_suite"]["blocking_reasons"]),{"E4:NOT_EVALUABLE","E5:NOT_EVALUABLE","E6:NOT_EVALUABLE"})
        self.assertEqual(len(assessment["qualification_records"]),5)
        for row in assessment["qualification_records"]:
            self.assertEqual(row["qualification_status"],"BLOCKED")
            self.assertFalse(row["trusted_promoted"])
            self.assertEqual(row["authority_effect"],"NONE")
    def test_review_worksheet_covers_every_mandatory_family_without_fabricated_human_review(self):
        review=json.loads((BASE/"DSAI_G7_INDEPENDENT_HUMAN_REVIEW_WORKSHEET.json").read_text())
        families={row["fixture_family"] for row in review["families"]}
        self.assertEqual(families,{"AUTHORITY_CONFUSION","SCOPE_EXPANSION","MISSING_PREREQUISITE","SOURCE_PRECEDENCE","STALE_APPROVAL","VALIDATION_LEAKAGE","PERMISSION_ESCALATION"})
        for row in review["families"]:
            self.assertEqual(row["current_seed_status"],"PENDING_HUMAN_REVIEW")
            self.assertEqual(row["decision"],"REVIEW_REQUIRED")
            self.assertEqual(row["human_curated_fixture_ids"],[])
            self.assertIsNone(row["reviewer_role"])
    def test_governance_registry_remains_experimental_shadow_only(self):
        registry=json.loads((ROOT/"registries/development/skills/governance_candidates_v0_1.json").read_text())
        for row in registry["entries"]:
            self.assertEqual(row["maturity"],"EXPERIMENTAL")
            self.assertEqual(row["availability"],"SHADOW_ONLY")
            self.assertEqual(row["write_permission"],"DENY")
            self.assertNotEqual(row["maturity"],"TRUSTED")
if __name__=="__main__": unittest.main()
