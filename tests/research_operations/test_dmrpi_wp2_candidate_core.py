from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from ovc.research_operations.dmrp_candidate import (
    CandidateInvariantError,
    CandidateOccurrence,
    CrossModeExposureLedger,
    MembershipEntry,
    MembershipLedger,
    ResearchCandidateGeneration,
    ResearchCandidateSeries,
    ResearchInfluenceEdge,
    assess_candidate_change,
    merge_series,
)


class DMRPIWP2CandidateCoreTests(unittest.TestCase):
    def generation(self, definition=None) -> ResearchCandidateGeneration:
        return ResearchCandidateGeneration(
            series_id="SYNTH.SERIES",
            generation=1,
            definition=definition or {"predicates":["A","B"]},
            population_binding={"population_id":"SYNTH.P1A"},
            dependency_manifest={"required":["C2"]},
            first_valid_rule={"mode":"MAX_REQUIRED_FVT"},
        )

    def test_candidate_definition_change_mutates_generation_hash(self) -> None:
        a = self.generation()
        b = self.generation({"predicates":["A","C"]})
        self.assertNotEqual(a.semantic_sha256, b.semantic_sha256)
        self.assertNotEqual(a.candidate_generation_id, b.candidate_generation_id)

    def test_execution_only_fix_can_preserve_semantics(self) -> None:
        a = self.generation(); b = self.generation()
        self.assertEqual(a.semantic_sha256, b.semantic_sha256)
        assessment = assess_candidate_change({"implementation_bugfix_no_semantic_change", "worker_count"})
        self.assertEqual(assessment.classification, "EXECUTION_CORRECTION")
        self.assertFalse(assessment.successor_generation_required)

    def test_candidate_occurrence_identity_contains_no_outcome(self) -> None:
        generation = self.generation()
        occurrence = CandidateOccurrence(generation.candidate_generation_id, "SYNTH.UNIT.1")
        self.assertTrue(occurrence.occurrence_id.startswith("rco:"))
        self.assertNotIn("outcome", occurrence.__dict__)
        with self.assertRaises(TypeError):
            CandidateOccurrence(generation.candidate_generation_id, "u1", outcome=1)  # type: ignore[call-arg]

    def test_complete_membership_ledger_preserves_all_states(self) -> None:
        generation = self.generation()
        ledger = MembershipLedger(generation.candidate_generation_id)
        units = {"u1","u2","u3","u4","u5","u6","u7","u8","u9"}
        states = ["MATCH","NON_MATCH","AMBIGUOUS","NOT_EVALUABLE","NOT_COMPARABLE","CENSORED","QUARANTINED","OUT_OF_SCOPE","PROCESS_INVALID"]
        for unit, state in zip(sorted(units), states):
            ledger.add(MembershipEntry(unit, state))
        ledger.assert_complete(units)
        self.assertEqual(len(ledger.entries), 9)
        with self.assertRaises(CandidateInvariantError):
            ledger.assert_complete(units | {"u10"})

    def test_unresolved_change_fails_toward_new_generation(self) -> None:
        unresolved = assess_candidate_change({"mystery"}, unresolved=True)
        self.assertEqual(unresolved.classification, "BLOCK_UNRESOLVED")
        self.assertTrue(unresolved.successor_generation_required)
        semantic = assess_candidate_change({"dependency_manifest"})
        self.assertEqual(semantic.classification, "SEMANTIC_CHANGE")
        self.assertTrue(semantic.successor_generation_required)

    def test_path1_and_path2_series_cannot_merge(self) -> None:
        p1 = ResearchCandidateSeries("SERIES", "PATH_1_EMPIRICAL", "x")
        p2 = ResearchCandidateSeries("SERIES", "PATH_2_THEORY_FORMALISATION", "x")
        with self.assertRaises(CandidateInvariantError):
            merge_series(p1, p2)

    def test_exposure_and_influence_records_never_grant_authority(self) -> None:
        edge = ResearchInfluenceEdge("PATH_2_THEORY_FORMALISATION", "PATH_1_EMPIRICAL", "VOCABULARY", "theory:1", "candidate:1", "2026-01-01T00:00:00Z")
        ledger = CrossModeExposureLedger(); ledger.add(edge)
        self.assertFalse(ledger.independence_claim_allowed("theory:1", "candidate:1"))
        self.assertEqual(edge.authority_effect, "NONE")
        with self.assertRaises(CandidateInvariantError):
            ResearchInfluenceEdge("P2", "P1", "ORIGIN", "a", "b", "t", authority_effect="FREEZE")

    def test_frozen_generation_rejects_attribute_and_nested_payload_mutation(self) -> None:
        generation = self.generation()
        with self.assertRaises(FrozenInstanceError):
            generation.generation = 2  # type: ignore[misc]
        with self.assertRaises(TypeError):
            generation.definition["predicates"] = ("X",)  # type: ignore[index]
        with self.assertRaises(AttributeError):
            generation.definition["predicates"].append("X")  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
