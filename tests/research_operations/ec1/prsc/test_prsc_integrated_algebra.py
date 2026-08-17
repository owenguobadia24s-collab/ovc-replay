from __future__ import annotations

import unittest

from ovc.research_operations.prsc import (
    PRSCContractError,
    bind_prsc_refs_to_candidate_review_card,
    bind_prsc_refs_to_question_decision,
    build_candidate_freeze_recommendation,
    build_claim_dependency_manifest,
    build_counterevidence_completeness_record,
    build_scientific_challenge_vector,
    evaluate_scientific_disposition,
)


class PRSCIntegratedAlgebraTests(unittest.TestCase):
    def test_population_templates_keep_boundary_specific_to_p1c(self):
        p1a = build_claim_dependency_manifest(candidate_ref="C1", population_family="P1A")
        p1b = build_claim_dependency_manifest(candidate_ref="C1", population_family="P1B")
        p1c = build_claim_dependency_manifest(candidate_ref="C1", population_family="P1C")
        self.assertIn("boundary", p1a["non_applicable_dimensions"])
        self.assertIn("boundary", p1b["non_applicable_dimensions"])
        self.assertIn("boundary", p1c["required_dimensions"])
        self.assertEqual(p1c["aggregation"], "NON_COMPENSATORY")

    def _support_vector(self, family="P1A"):
        manifest = build_claim_dependency_manifest(candidate_ref="C1", population_family=family)
        states = {d: "NON_FATAL_SUPPORT" for d in manifest["required_dimensions"]}
        for d in manifest["scope_condition_dimensions"]:
            states[d] = "NON_FATAL_SUPPORT"
        for d in manifest["advisory_dimensions"]:
            states[d] = "NOT_APPLICABLE"
        for d in manifest["non_applicable_dimensions"]:
            states[d] = "NOT_APPLICABLE"
        return manifest, build_scientific_challenge_vector(candidate_ref="C1", dimension_states=states)

    def test_fatal_required_dimension_cannot_be_compensated(self):
        manifest, vector = self._support_vector()
        vector["dimensions"]["reference"]["state"] = "FATAL_TO_CURRENT_CLAIM"
        disposition = evaluate_scientific_disposition(challenge_vector=vector, claim_dependency_manifest=manifest)
        self.assertEqual(disposition["precedence_hit"], "REQUIRED_FATAL")
        self.assertEqual(disposition["disposition"], "REJECT_CURRENT_CLAIM")
        self.assertIsNone(disposition["score"])
        self.assertIsNone(disposition["majority_vote"])

    def test_unresolved_precedes_revision_and_restriction(self):
        manifest, vector = self._support_vector()
        vector["dimensions"]["reference"]["state"] = "UNRESOLVED"
        vector["dimensions"]["representation"]["state"] = "REVISION_REQUIRED"
        vector["dimensions"]["context"]["state"] = "SCOPE_RESTRICTION"
        disposition = evaluate_scientific_disposition(challenge_vector=vector, claim_dependency_manifest=manifest)
        self.assertEqual(disposition["precedence_hit"], "REQUIRED_UNRESOLVED")
        self.assertEqual(disposition["disposition"], "NOT_EVALUABLE")

    def test_revision_precedes_scope_restriction(self):
        manifest, vector = self._support_vector()
        vector["dimensions"]["representation"]["state"] = "REVISION_REQUIRED"
        vector["dimensions"]["context"]["state"] = "SCOPE_RESTRICTION"
        disposition = evaluate_scientific_disposition(challenge_vector=vector, claim_dependency_manifest=manifest)
        self.assertEqual(disposition["disposition"], "REFINE_WITHIN_DISCOVERY")

    def test_scope_restriction_preserves_recurrence_and_freeze_is_recommendation_only(self):
        manifest, vector = self._support_vector()
        vector["dimensions"]["context"]["state"] = "SCOPE_RESTRICTION"
        disposition = evaluate_scientific_disposition(challenge_vector=vector, claim_dependency_manifest=manifest)
        self.assertEqual(disposition["disposition"], "FREEZE_WITH_SCOPE_RESTRICTION")
        recommendation = build_candidate_freeze_recommendation(
            candidate_ref="C1", scientific_disposition_ref=disposition["scientific_disposition_id"], rationale_refs=["E1"]
        )
        self.assertEqual(recommendation["owner_gate"], "EC1-GSCI")
        self.assertEqual(recommendation["candidate_freeze_effect"], "NONE")
        self.assertEqual(recommendation["authority_effect"], "NONE")

    def test_clean_required_support_can_only_recommend_freeze_review(self):
        manifest, vector = self._support_vector()
        disposition = evaluate_scientific_disposition(challenge_vector=vector, claim_dependency_manifest=manifest)
        self.assertEqual(disposition["disposition"], "FREEZE_CANDIDATE_RECOMMENDED")
        self.assertEqual(disposition["candidate_freeze_effect"], "NONE")

    def test_counterevidence_completeness_fails_honestly(self):
        record = build_counterevidence_completeness_record(
            candidate_ref="C1",
            required_categories=["counterexamples", "nulls", "near_neighbours"],
            evidence_by_category={"counterexamples": ["E1"], "nulls": [], "near_neighbours": ["E2"]},
        )
        self.assertFalse(record["complete"])
        self.assertEqual(record["missing_categories"], ["nulls"])

    def test_candidate_review_adapter_never_changes_proposal_eligibility(self):
        card = {"review_card_id": "RC1", "proposal_review_status": "PROPOSAL_ELIGIBLE"}
        adapted = bind_prsc_refs_to_candidate_review_card(card, prsc_refs=["PRSC:1"])
        self.assertEqual(adapted["proposal_review_status"], "PROPOSAL_ELIGIBLE")
        self.assertEqual(adapted["prsc_refs"], ["PRSC:1"])
        self.assertNotIn("prsc_refs", card)

    def test_question_adapter_is_q08_q10_only_and_preserves_tree_result(self):
        q08 = {"decision_tree_id": "DT-Q08", "terminal_node": "Q08.PASS", "recommended_disposition": "FREEZE_CANDIDATE", "reserved_action_requested": "PREPARE_EC1_GSCI_CANDIDATE_FREEZE"}
        adapted = bind_prsc_refs_to_question_decision(q08, prsc_refs=["PRSC:1"])
        self.assertEqual(adapted["terminal_node"], q08["terminal_node"])
        self.assertEqual(adapted["recommended_disposition"], q08["recommended_disposition"])
        with self.assertRaises(PRSCContractError):
            bind_prsc_refs_to_question_decision({"decision_tree_id": "DT-Q09"}, prsc_refs=["PRSC:1"])

    def test_integrity_quarantine_has_highest_precedence(self):
        manifest, vector = self._support_vector()
        vector["dimensions"]["reference"]["state"] = "FATAL_TO_CURRENT_CLAIM"
        disposition = evaluate_scientific_disposition(
            challenge_vector=vector, claim_dependency_manifest=manifest, integrity_state="QUARANTINE"
        )
        self.assertEqual(disposition["disposition"], "QUARANTINE_INTEGRITY")
        self.assertEqual(disposition["precedence_hit"], "INTEGRITY_INVALID")


if __name__ == "__main__":
    unittest.main()
