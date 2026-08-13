from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.opt_b.c2p_v0_2.adjudication import (
    AdjudicationError,
    REFERENCE_MAX_ELIGIBLE_PER_HARD_SCOPE,
    adjudicate_candidate,
    mechanical_evidence_from_source,
    prove_retrieval_superset,
)
from ovc.opt_b.c2p_v0_2.assertion import AssertionGenesisError, create_object_assertion
from ovc.opt_b.c2p_v0_2.candidate import extract_candidate
from ovc.opt_b.c2p_v0_2.tracklet import append_candidate, open_tracklet

ROOT = Path(__file__).resolve().parents[4]
PACK_A = json.loads((ROOT / "fixtures/opt_b/c2p/v0_2/packs/C2P_SYNTH_OBJECTPACK_MINIMAL_A_v1.json").read_text(encoding="utf-8"))
PACK_B = json.loads((ROOT / "fixtures/opt_b/c2p/v0_2/packs/C2P_SYNTH_OBJECTPACK_MINIMAL_B_v1.json").read_text(encoding="utf-8"))


def source(step: int, *, structure: str = "L1", partition: str = "P1", coordinate_class: str = "C1"):
    return {
        "candidate_present": True,
        "source_available": True,
        "source_lineage_envelope_id": f"SYNTH.LINEAGE.{step}",
        "source_refs": [f"SYNTH:C2:{step}", f"SYNTH:C2E:{step}"],
        "market_effective_start": f"2026-01-01T00:{step:02d}:00Z",
        "market_effective_end": None,
        "first_valid_time": f"2026-01-01T00:{step:02d}:01Z",
        "evaluation_cutoff": f"2026-01-01T00:{step:02d}:02Z",
        "fixture_partition_id": partition,
        "fixture_structure_key": structure,
        "fixture_step": step,
        "coordinate_class": coordinate_class,
        "identity_defining_geometry": {"coordinate": str(100 + step)},
    }


def candidate_and_evidence(step: int, pack=PACK_A, **kwargs):
    src = source(step, **kwargs)
    candidate = extract_candidate(src, pack).candidate
    return candidate, mechanical_evidence_from_source(candidate["candidate_id"], src)


def confirmed_tracklet_and_last(pack=PACK_A):
    pairs = [candidate_and_evidence(step, pack) for step in (1, 2, 3)]
    tracklet = open_tracklet(pairs[0][0], pack)
    tracklet = append_candidate(tracklet, pairs[1][0], pack)
    tracklet = append_candidate(tracklet, pairs[2][0], pack)
    return tracklet, pairs[-1]


def assertion_from_new(pack=PACK_A):
    tracklet, (candidate, evidence) = confirmed_tracklet_and_last(pack)
    result = adjudicate_candidate(candidate, evidence, [], {}, pack)
    assertion = create_object_assertion(tracklet, result.decision, pack)
    return assertion, evidence.rebind(assertion["object_assertion_id"]), tracklet, result.decision


class C2P2WP3AdjudicationAssertionTests(unittest.TestCase):
    def test_new_decision_and_object_assertion_genesis_are_deterministic(self):
        assertion_a, evidence_a, tracklet_a, decision_a = assertion_from_new(PACK_A)
        assertion_b, evidence_b, tracklet_b, decision_b = assertion_from_new(PACK_A)
        self.assertEqual(decision_a, decision_b)
        self.assertEqual(assertion_a, assertion_b)
        self.assertEqual(evidence_a, evidence_b)
        self.assertEqual(tracklet_a["state"], "CONFIRMED")
        self.assertEqual(decision_a["terminal_decision"], "NEW")
        self.assertGreaterEqual(assertion_a["first_valid_identity_time"], tracklet_a["first_valid_time"])
        self.assertEqual(assertion_a["immutable_genesis_evidence_ids"], tracklet_a["member_candidate_ids"])
        self.assertEqual(len(assertion_a["object_assertion_id"]), 64)
        self.assertEqual(len(assertion_a["genesis_event_id"]), 64)

    def test_exact_single_match_updates_and_rank_cannot_decide_identity(self):
        assertion, assertion_evidence, _, _ = assertion_from_new()
        candidate, evidence = candidate_and_evidence(4)
        result = adjudicate_candidate(candidate, evidence, [assertion], {assertion["object_assertion_id"]: assertion_evidence}, PACK_A)
        self.assertEqual(result.decision["terminal_decision"], "UPDATE")
        self.assertEqual(result.decision["eligible_assertions"], [assertion["object_assertion_id"]])
        self.assertEqual(result.proof_envelope["pair_adjudications"], 4)
        self.assertNotIn("score", result.decision)
        self.assertNotIn("rank", result.decision)
        self.assertTrue(all("score" not in vector and "rank" not in vector for vector in result.evidence_vectors))

    def test_multiple_equally_lawful_assertions_preserve_ambiguity(self):
        assertion, assertion_evidence, _, _ = assertion_from_new()
        second = dict(assertion)
        second["object_assertion_id"] = "b" * 64
        candidate, evidence = candidate_and_evidence(4)
        result = adjudicate_candidate(
            candidate,
            evidence,
            [second, assertion],
            {
                assertion["object_assertion_id"]: assertion_evidence,
                second["object_assertion_id"]: assertion_evidence.rebind(second["object_assertion_id"]),
            },
            PACK_A,
        )
        self.assertEqual(result.decision["terminal_decision"], "AMBIGUOUS")
        self.assertEqual(result.decision["eligible_assertions"], sorted([assertion["object_assertion_id"], second["object_assertion_id"]]))

    def test_missing_match_evidence_fails_closed_not_new(self):
        assertion, _, _, _ = assertion_from_new()
        candidate, evidence = candidate_and_evidence(4)
        result = adjudicate_candidate(candidate, evidence, [assertion], {}, PACK_A)
        self.assertEqual(result.decision["terminal_decision"], "NOT_EVALUABLE")
        self.assertEqual(result.decision["predicate_results"]["all_potential_matches_evaluable"], "FAIL")

    def test_family_context_semantic_and_score_inputs_are_forbidden_identity_evidence(self):
        candidate, _ = candidate_and_evidence(4)
        for field in ("family_label", "context_label", "semantic_label", "rank", "score", "probability", "outcome"):
            bad = source(4)
            bad[field] = "FORBIDDEN"
            with self.assertRaisesRegex(AdjudicationError, "C2P_FORBIDDEN_IDENTITY_EVIDENCE"):
                mechanical_evidence_from_source(candidate["candidate_id"], bad)

    def test_reference_envelope_and_retrieval_superset_fail_closed(self):
        assertion, _, _, _ = assertion_from_new()
        candidate, _ = candidate_and_evidence(4)
        too_many = []
        for index in range(REFERENCE_MAX_ELIGIBLE_PER_HARD_SCOPE + 1):
            item = dict(assertion)
            item["object_assertion_id"] = f"{index:064x}"
            too_many.append(item)
        with self.assertRaisesRegex(AdjudicationError, "C2P_REFERENCE_PROOF_ENVELOPE_CANDIDATE_LIMIT"):
            adjudicate_candidate(candidate, mechanical_evidence_from_source(candidate["candidate_id"], source(4)), too_many, {}, PACK_A)
        with self.assertRaisesRegex(AdjudicationError, "C2P_RETRIEVAL_FALSE_NEGATIVE"):
            prove_retrieval_superset(["a" * 64, "b" * 64], ["a" * 64])
        self.assertTrue(prove_retrieval_superset(["a" * 64], ["a" * 64, "b" * 64]))

    def test_assertion_identity_is_pack_scoped_and_genesis_is_causal(self):
        assertion_a, _, _, _ = assertion_from_new(PACK_A)
        assertion_b, _, _, _ = assertion_from_new(PACK_B)
        self.assertNotEqual(assertion_a["object_assertion_id"], assertion_b["object_assertion_id"])
        self.assertNotEqual(assertion_a["object_pack_id"], assertion_b["object_pack_id"])

        candidate, evidence = candidate_and_evidence(1)
        unconfirmed = open_tracklet(candidate, PACK_A)
        new_decision = adjudicate_candidate(candidate, evidence, [], {}, PACK_A).decision
        with self.assertRaisesRegex(AssertionGenesisError, "C2P_TRACKLET_NOT_CONFIRMED"):
            create_object_assertion(unconfirmed, new_decision, PACK_A)

    def test_genesis_requires_new_decision_and_duplicate_control(self):
        assertion, assertion_evidence, tracklet, new_decision = assertion_from_new()
        candidate, evidence = candidate_and_evidence(4)
        update = adjudicate_candidate(candidate, evidence, [assertion], {assertion["object_assertion_id"]: assertion_evidence}, PACK_A).decision
        with self.assertRaisesRegex(AssertionGenesisError, "C2P_GENESIS_REQUIRES_NEW_MATCH_DECISION"):
            create_object_assertion(tracklet, update, PACK_A)
        with self.assertRaisesRegex(AssertionGenesisError, "C2P_DUPLICATE_ASSERTION_GENESIS"):
            create_object_assertion(tracklet, new_decision, PACK_A, existing_assertion_ids=[assertion["object_assertion_id"]])

    def test_records_match_frozen_schema_field_surfaces(self):
        assertion, assertion_evidence, _, _ = assertion_from_new()
        candidate, evidence = candidate_and_evidence(4)
        result = adjudicate_candidate(candidate, evidence, [assertion], {assertion["object_assertion_id"]: assertion_evidence}, PACK_A)
        decision_required = {
            "schema", "decision_id", "object_pack_id", "retrieval_query_id", "candidate_id",
            "retrieved_candidate_assertions", "eligible_assertions", "evidence_vector_ids", "predicate_results",
            "excluded_assertions", "terminal_decision", "first_valid_time", "evaluation_cutoff",
        }
        vector_required = {
            "schema", "evidence_vector_id", "object_pack_id", "candidate_id", "assertion_id",
            "geometry_residuals", "temporal_continuity", "topology_compatibility", "relation_compatibility",
            "scale_compatibility", "availability_evaluability", "predicate_results",
        }
        assertion_required = {
            "schema", "object_assertion_id", "hash_version", "object_pack_id", "structural_role_id",
            "geometry_kind_id", "hard_scope", "immutable_genesis_evidence_ids", "genesis_match_decision_id",
            "genesis_event_id", "first_valid_identity_time", "lifecycle_state",
        }
        self.assertEqual(set(result.decision), decision_required)
        self.assertTrue(all(set(vector) == vector_required for vector in result.evidence_vectors))
        self.assertEqual(set(assertion), assertion_required)


if __name__ == "__main__":
    unittest.main()
