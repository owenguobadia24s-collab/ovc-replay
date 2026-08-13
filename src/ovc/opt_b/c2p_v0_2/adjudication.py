from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence

from .canonical import canonical_bytes


REFERENCE_MAX_ELIGIBLE_PER_HARD_SCOPE = 2048
REFERENCE_MAX_PREDICATES_PER_PAIR = 16
REFERENCE_MAX_PAIR_ADJUDICATIONS_PER_GOLDEN_RUN = 4_194_304


class AdjudicationError(ValueError):
    pass


@dataclass(frozen=True)
class MechanicalEvidence:
    subject_id: str
    fixture_structure_key: str
    fixture_step: int
    coordinate_class: str
    identity_defining_geometry: Mapping[str, Any]

    def rebind(self, subject_id: str) -> "MechanicalEvidence":
        return replace(self, subject_id=subject_id)


@dataclass(frozen=True)
class AdjudicationResult:
    decision: Mapping[str, Any]
    evidence_vectors: tuple[Mapping[str, Any], ...]
    proof_envelope: Mapping[str, int]


def _hash(payload: Any) -> str:
    return sha256(canonical_bytes(payload)).hexdigest()


def mechanical_evidence_from_source(subject_id: str, source: Mapping[str, Any]) -> MechanicalEvidence:
    forbidden = sorted(
        key
        for key in source
        if key in {
            "family_label",
            "family_id",
            "context_label",
            "semantic_label",
            "c3_label",
            "rank",
            "score",
            "probability",
            "outcome",
        }
    )
    if forbidden:
        raise AdjudicationError(f"C2P_FORBIDDEN_IDENTITY_EVIDENCE:{forbidden[0]}")
    required = ("fixture_structure_key", "fixture_step", "coordinate_class", "identity_defining_geometry")
    missing = [field for field in required if field not in source]
    if missing:
        raise AdjudicationError(f"C2P_MISSING_MECHANICAL_EVIDENCE:{missing[0]}")
    return MechanicalEvidence(
        subject_id=subject_id,
        fixture_structure_key=str(source["fixture_structure_key"]),
        fixture_step=int(source["fixture_step"]),
        coordinate_class=str(source["coordinate_class"]),
        identity_defining_geometry=dict(source["identity_defining_geometry"]),
    )


def _candidate_scope_assertions(candidate: Mapping[str, Any], assertions: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [
        assertion
        for assertion in assertions
        if assertion.get("object_pack_id") == candidate.get("object_pack_id")
        and assertion.get("structural_role_id") == candidate.get("structural_role_id")
        and assertion.get("geometry_kind_id") == candidate.get("geometry_kind_id")
        and assertion.get("hard_scope") == candidate.get("hard_scope")
    ]


def reference_retrieve(candidate: Mapping[str, Any], assertions: Sequence[Mapping[str, Any]], object_pack: Mapping[str, Any]) -> tuple[str, list[Mapping[str, Any]]]:
    if candidate.get("object_pack_id") != object_pack.get("object_pack_id"):
        raise AdjudicationError("C2P_OBJECT_PACK_MISMATCH")
    if object_pack.get("status") != "SYNTHETIC_ONLY_NONEMPIRICAL" or object_pack.get("real_source_forbidden") is not True:
        raise AdjudicationError("C2P_WP3_SYNTHETIC_PACK_REQUIRED")
    in_scope = _candidate_scope_assertions(candidate, assertions)
    if len(in_scope) > REFERENCE_MAX_ELIGIBLE_PER_HARD_SCOPE:
        raise AdjudicationError("C2P_REFERENCE_PROOF_ENVELOPE_CANDIDATE_LIMIT")
    query_payload = {
        "schema": "c2p-reference-retrieval-query/v0.2",
        "object_pack_id": object_pack["object_pack_id"],
        "structural_role_id": candidate["structural_role_id"],
        "geometry_kind_id": candidate["geometry_kind_id"],
        "hard_scope": candidate["hard_scope"],
        "mode": "EXHAUSTIVE_REFERENCE",
    }
    return _hash(query_payload), sorted(in_scope, key=lambda item: item["object_assertion_id"])


def prove_retrieval_superset(reference_assertion_ids: Iterable[str], optimized_assertion_ids: Iterable[str]) -> bool:
    reference = set(reference_assertion_ids)
    optimized = set(optimized_assertion_ids)
    if not reference.issubset(optimized):
        missing = sorted(reference - optimized)
        raise AdjudicationError(f"C2P_RETRIEVAL_FALSE_NEGATIVE:{missing[0]}")
    return True


def _predicate_results(candidate: Mapping[str, Any], candidate_evidence: MechanicalEvidence, assertion: Mapping[str, Any], assertion_evidence: MechanicalEvidence | None, object_pack: Mapping[str, Any]) -> dict[str, str]:
    predicates = tuple(object_pack.get("matching_contract", {}).get("identity_predicates", ()))
    if len(predicates) > REFERENCE_MAX_PREDICATES_PER_PAIR:
        raise AdjudicationError("C2P_REFERENCE_PROOF_ENVELOPE_PREDICATE_LIMIT")
    supported = {
        "same_hard_scope",
        "same_fixture_structure_key",
        "same_coordinate_class",
        "monotonic_fixture_step",
    }
    unknown = [predicate for predicate in predicates if predicate not in supported]
    if unknown:
        raise AdjudicationError(f"C2P_UNIMPLEMENTED_IDENTITY_PREDICATE:{unknown[0]}")

    results: dict[str, str] = {}
    for predicate in predicates:
        if predicate == "same_hard_scope":
            results[predicate] = "PASS" if candidate["hard_scope"] == assertion["hard_scope"] else "FAIL"
        elif assertion_evidence is None:
            results[predicate] = "NOT_EVALUABLE"
        elif predicate == "same_fixture_structure_key":
            results[predicate] = "PASS" if candidate_evidence.fixture_structure_key == assertion_evidence.fixture_structure_key else "FAIL"
        elif predicate == "same_coordinate_class":
            results[predicate] = "PASS" if candidate_evidence.coordinate_class == assertion_evidence.coordinate_class else "FAIL"
        elif predicate == "monotonic_fixture_step":
            results[predicate] = "PASS" if candidate_evidence.fixture_step > assertion_evidence.fixture_step else "FAIL"
    return results


def adjudicate_candidate(
    candidate: Mapping[str, Any],
    candidate_evidence: MechanicalEvidence,
    assertions: Sequence[Mapping[str, Any]],
    assertion_evidence_by_id: Mapping[str, MechanicalEvidence],
    object_pack: Mapping[str, Any],
    *,
    pair_adjudications_already_used: int = 0,
) -> AdjudicationResult:
    if candidate_evidence.subject_id != candidate.get("candidate_id"):
        raise AdjudicationError("C2P_CANDIDATE_EVIDENCE_BINDING_MISMATCH")
    retrieval_query_id, retrieved = reference_retrieve(candidate, assertions, object_pack)
    predicate_count = len(tuple(object_pack.get("matching_contract", {}).get("identity_predicates", ())))
    pair_cost = len(retrieved) * predicate_count
    if pair_adjudications_already_used + pair_cost > REFERENCE_MAX_PAIR_ADJUDICATIONS_PER_GOLDEN_RUN:
        raise AdjudicationError("C2P_REFERENCE_PROOF_ENVELOPE_PAIR_LIMIT")

    evidence_vectors: list[dict[str, Any]] = []
    eligible: list[str] = []
    excluded: list[dict[str, Any]] = []
    unresolved_potential_match = False

    for assertion in retrieved:
        assertion_id = assertion["object_assertion_id"]
        assertion_evidence = assertion_evidence_by_id.get(assertion_id)
        if assertion_evidence is not None and assertion_evidence.subject_id != assertion_id:
            raise AdjudicationError("C2P_ASSERTION_EVIDENCE_BINDING_MISMATCH")
        predicates = _predicate_results(candidate, candidate_evidence, assertion, assertion_evidence, object_pack)
        vector_payload = {
            "schema": "c2p-evidence-vector/v0.2",
            "object_pack_id": object_pack["object_pack_id"],
            "candidate_id": candidate["candidate_id"],
            "assertion_id": assertion_id,
            "geometry_residuals": {
                "candidate_geometry": candidate_evidence.identity_defining_geometry,
                "assertion_geometry": assertion_evidence.identity_defining_geometry if assertion_evidence else None,
            },
            "temporal_continuity": {
                "candidate_fixture_step": candidate_evidence.fixture_step,
                "assertion_fixture_step": assertion_evidence.fixture_step if assertion_evidence else None,
            },
            "topology_compatibility": {},
            "relation_compatibility": {},
            "scale_compatibility": {"same_scale": candidate["hard_scope"]["scale"] == assertion["hard_scope"]["scale"]},
            "availability_evaluability": {"mechanical_evidence": "AVAILABLE" if assertion_evidence else "NOT_EVALUABLE"},
            "predicate_results": predicates,
        }
        vector = dict(vector_payload)
        vector["evidence_vector_id"] = _hash(vector_payload)
        evidence_vectors.append(vector)

        values = set(predicates.values())
        if values == {"PASS"} or not predicates:
            eligible.append(assertion_id)
        elif "NOT_EVALUABLE" in values and "FAIL" not in values:
            unresolved_potential_match = True
            excluded.append({"assertion_id": assertion_id, "reason_codes": ["C2P_MATCH_NOT_EVALUABLE"]})
        else:
            failed = sorted(key for key, value in predicates.items() if value == "FAIL")
            excluded.append({"assertion_id": assertion_id, "reason_codes": [f"C2P_PREDICATE_FAIL:{key}" for key in failed]})

    if len(eligible) > 1:
        terminal = "AMBIGUOUS"
    elif unresolved_potential_match:
        terminal = "NOT_EVALUABLE"
    elif len(eligible) == 1:
        terminal = "UPDATE"
    else:
        terminal = "NEW"

    decision_payload = {
        "schema": "c2p-match-decision/v0.2",
        "object_pack_id": object_pack["object_pack_id"],
        "retrieval_query_id": retrieval_query_id,
        "candidate_id": candidate["candidate_id"],
        "retrieved_candidate_assertions": [item["object_assertion_id"] for item in retrieved],
        "eligible_assertions": sorted(eligible),
        "evidence_vector_ids": sorted(vector["evidence_vector_id"] for vector in evidence_vectors),
        "predicate_results": {
            "reference_envelope": "PASS",
            "all_potential_matches_evaluable": "FAIL" if unresolved_potential_match else "PASS",
        },
        "excluded_assertions": excluded,
        "terminal_decision": terminal,
        "first_valid_time": candidate["first_valid_time"],
        "evaluation_cutoff": candidate["evaluation_cutoff"],
    }
    decision = dict(decision_payload)
    decision["decision_id"] = _hash(decision_payload)
    proof_envelope = {
        "retrieved_count": len(retrieved),
        "predicates_per_pair": predicate_count,
        "pair_adjudications": pair_cost,
        "max_eligible_per_hard_scope": REFERENCE_MAX_ELIGIBLE_PER_HARD_SCOPE,
        "max_predicates_per_pair": REFERENCE_MAX_PREDICATES_PER_PAIR,
        "max_pair_adjudications_per_golden_run": REFERENCE_MAX_PAIR_ADJUDICATIONS_PER_GOLDEN_RUN,
    }
    return AdjudicationResult(decision=decision, evidence_vectors=tuple(evidence_vectors), proof_envelope=proof_envelope)
