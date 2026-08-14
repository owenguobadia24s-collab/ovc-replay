from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from .canonical import sha256_canonical


class TermQualificationError(ValueError):
    """Raised when a StructuralTerm qualification object violates ESL boundaries."""


TERM_CLASSES = frozenset({
    "OBSERVABLE_PROPERTY",
    "STRUCTURAL_RELATION",
    "PERSISTENCE_CONCEPT",
    "DEVELOPMENT_CONCEPT",
    "ORGANISATION_CONCEPT",
    "INVARIANT_CONCEPT",
    "CONSTRAINT_CONCEPT",
    "STRUCTURAL_EVENT_CONCEPT",
    "EPISTEMIC_CONCEPT",
})

QUALIFICATION_STAGES = (
    "PROPOSED",
    "DEFINED",
    "OBSERVABLE",
    "MEASURABLE",
    "MECHANICALLY_REPRODUCIBLE",
    "EMPIRICALLY_OBSERVED",
    "RECURRENCE_CHARACTERISED",
    "ORGANISATION_CHARACTERISED",
    "CONSTRAINT_CHARACTERISED",
    "SEMANTICALLY_QUALIFIED",
)

QUALIFICATION_DISPOSITIONS = frozenset({
    "PROGRESS",
    "DEFER",
    "REJECT",
    "UNRESOLVED",
    "QUARANTINE_PROPOSED",
    "SUPERSEDE_PROPOSED",
})

ADMISSION_PROPOSAL_STATES = frozenset({"ADMISSION_CANDIDATE", "ADMITTED_SHADOW"})
CHALLENGE_TARGETS = frozenset({
    "OBSERVABILITY",
    "MEASUREMENT",
    "REPLAY",
    "RECURRENCE",
    "ORGANISATION",
    "CONSTRAINT",
    "CHRONOLOGY",
    "COMPARABILITY",
    "SEMANTIC_DISTINCTNESS",
    "SCOPE_TRANSPORT",
})
CHALLENGE_RECOMMENDATIONS = frozenset({"RETAIN", "NARROW", "QUARANTINE", "SUPERSEDE", "RETIRE", "REPLICATE", "UNRESOLVED"})
TRANSPORT_STATUSES = frozenset({"NOT_NOMINATED", "TRANSPORT_EVALUATION_CANDIDATE", "EVIDENCE_REQUIRED", "NOT_COMPARABLE", "REJECTED"})

_FORBIDDEN_IDENTITY_KEYS = frozenset({
    "outcome",
    "outcomes",
    "future_return",
    "expected_return",
    "mfe",
    "mae",
    "probability",
    "forecast",
    "risk",
    "exposure",
    "execution",
    "trade",
    "trading",
    "mechanism",
    "cause",
    "causal_claim",
    "intent",
    "admitted_active",
})


def _copy(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _copy(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_copy(v) for v in value]
    return copy.deepcopy(value)


def _scan_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text.lower() in _FORBIDDEN_IDENTITY_KEYS:
                raise TermQualificationError(f"TERM_FORBIDDEN_IDENTITY_FIELD:{path}.{key_text}")
            _scan_forbidden(child, f"{path}.{key_text}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _scan_forbidden(child, f"{path}[{index}]")


def _nonempty(value: Any, code: str) -> str:
    text = str(value or "")
    if not text:
        raise TermQualificationError(code)
    return text


def _strings(values: Sequence[Any], code: str, *, allow_empty: bool = True) -> list[str]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TermQualificationError(code)
    result = sorted({str(v) for v in values})
    if any(not item for item in result):
        raise TermQualificationError(code)
    if not allow_empty and not result:
        raise TermQualificationError(code)
    return result


def _authority() -> dict[str, str]:
    return {
        "authority_state": "INACTIVE_CONFORMANCE_ONLY",
        "authority_effect": "NONE",
        "semantic_activation": "NONE",
        "admitted_active_path": "FORBIDDEN",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
    }


def build_language_candidate_binding(*, research_candidate_generation_id: str, structural_term_candidate_id: str, source_mode: str, vocabulary_exposure: str = "UNKNOWN") -> dict[str, Any]:
    research_id = _nonempty(research_candidate_generation_id, "TERM_RESEARCH_CANDIDATE_ID_REQUIRED")
    term_id = _nonempty(structural_term_candidate_id, "TERM_CANDIDATE_ID_REQUIRED")
    if research_id == term_id:
        raise TermQualificationError("TERM_RESEARCH_AND_TERM_IDENTITY_MUST_DIFFER")
    mode = str(source_mode)
    if mode not in {"PATH_1", "PATH_2", "THEORY_AGNOSTIC", "OTHER_GOVERNED"}:
        raise TermQualificationError("TERM_SOURCE_MODE_INVALID")
    exposure = str(vocabulary_exposure)
    if exposure not in {"BLINDED", "EXPOSED", "PARTIAL", "UNKNOWN", "NOT_APPLICABLE"}:
        raise TermQualificationError("TERM_VOCABULARY_EXPOSURE_INVALID")
    payload = {
        "schema": "ovc-esl-language-candidate-binding/v1",
        "research_candidate_generation_id": research_id,
        "structural_term_candidate_id": term_id,
        "source_mode": mode,
        "vocabulary_exposure": exposure,
        "identity_merge": "FORBIDDEN",
        "authority": _authority(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "language_candidate_binding_id": "lcb1:" + logical_hash, "logical_hash": logical_hash}


def build_structural_term_candidate(
    *,
    machine_symbol: str,
    term_class: str,
    formal_definition: Mapping[str, Any],
    observation_unit: str,
    temporal_semantics: Mapping[str, Any],
    inclusion_predicates: Sequence[Any],
    exclusion_predicates: Sequence[Any],
    boundary_cases: Sequence[Any],
    ambiguity_policy: str,
    missingness_policy: str,
    observable_implications: Sequence[Any],
    falsifiers: Sequence[Any],
    prohibited_interpretations: Sequence[Any],
    scope: Mapping[str, Any],
    provenance_refs: Sequence[Any],
    research_candidate_generation_ids: Sequence[Any] = (),
    semantic_delta: str = "",
    composition_refs: Sequence[Any] = (),
    predecessor_term_generation_id: str | None = None,
) -> dict[str, Any]:
    symbol = _nonempty(machine_symbol, "TERM_MACHINE_SYMBOL_REQUIRED")
    klass = str(term_class)
    if klass not in TERM_CLASSES:
        raise TermQualificationError("TERM_CLASS_INVALID:" + klass)
    definition = _copy(formal_definition)
    temporal = _copy(temporal_semantics)
    scope_payload = _copy(scope)
    if not all(isinstance(value, Mapping) for value in (definition, temporal, scope_payload)):
        raise TermQualificationError("TERM_MAPPING_SURFACES_REQUIRED")
    identity_surface = {
        "machine_symbol": symbol,
        "term_class": klass,
        "formal_definition": definition,
        "observation_unit": _nonempty(observation_unit, "TERM_OBSERVATION_UNIT_REQUIRED"),
        "temporal_semantics": temporal,
        "inclusion_predicates": _strings(inclusion_predicates, "TERM_INCLUSION_INVALID", allow_empty=False),
        "exclusion_predicates": _strings(exclusion_predicates, "TERM_EXCLUSION_INVALID", allow_empty=False),
        "boundary_cases": _strings(boundary_cases, "TERM_BOUNDARY_CASES_INVALID", allow_empty=False),
        "ambiguity_policy": _nonempty(ambiguity_policy, "TERM_AMBIGUITY_POLICY_REQUIRED"),
        "missingness_policy": _nonempty(missingness_policy, "TERM_MISSINGNESS_POLICY_REQUIRED"),
        "observable_implications": _strings(observable_implications, "TERM_OBSERVABLE_IMPLICATIONS_INVALID"),
        "falsifiers": _strings(falsifiers, "TERM_FALSIFIERS_INVALID", allow_empty=False),
        "prohibited_interpretations": _strings(prohibited_interpretations, "TERM_PROHIBITED_INTERPRETATIONS_INVALID", allow_empty=False),
        "scope": scope_payload,
        "semantic_delta": str(semantic_delta),
        "composition_refs": _strings(composition_refs, "TERM_COMPOSITION_REFS_INVALID"),
    }
    _scan_forbidden(identity_surface)
    payload = {
        "schema": "ovc-esl-structural-term-candidate/v1",
        **identity_surface,
        "provenance_refs": _strings(provenance_refs, "TERM_PROVENANCE_REFS_INVALID", allow_empty=False),
        "research_candidate_generation_ids": _strings(research_candidate_generation_ids, "TERM_RESEARCH_CANDIDATE_IDS_INVALID"),
        "predecessor_term_generation_id": predecessor_term_generation_id,
        "qualification_stage": "PROPOSED",
        "semantic_admission_state": "NOT_ADMITTED",
        "authority": _authority(),
    }
    logical_hash = sha256_canonical({k: v for k, v in payload.items() if k not in {"provenance_refs", "research_candidate_generation_ids", "predecessor_term_generation_id", "qualification_stage", "semantic_admission_state", "authority"}})
    return {**payload, "structural_term_candidate_id": "stc1:" + logical_hash, "term_generation_id": "stg1:" + logical_hash, "logical_hash": logical_hash}


def build_term_qualification_rule_pack(*, rule_pack_id: str, term_class: str, required_stages: Sequence[Any], required_evidence_dimensions: Sequence[Any], rule_refs: Sequence[Any], frozen_before_evidence: bool) -> dict[str, Any]:
    if not frozen_before_evidence:
        raise TermQualificationError("TERM_RULE_PACK_MUST_BE_FROZEN_BEFORE_EVIDENCE")
    klass = str(term_class)
    if klass not in TERM_CLASSES:
        raise TermQualificationError("TERM_CLASS_INVALID:" + klass)
    stages = _strings(required_stages, "TERM_RULE_PACK_STAGES_INVALID", allow_empty=False)
    unknown = sorted(set(stages) - set(QUALIFICATION_STAGES))
    if unknown:
        raise TermQualificationError("TERM_RULE_PACK_STAGE_UNKNOWN:" + ",".join(unknown))
    payload = {
        "schema": "ovc-esl-term-qualification-rule-pack/v1",
        "rule_pack_id": _nonempty(rule_pack_id, "TERM_RULE_PACK_ID_REQUIRED"),
        "term_class": klass,
        "required_stages": stages,
        "required_evidence_dimensions": _strings(required_evidence_dimensions, "TERM_RULE_PACK_EVIDENCE_DIMENSIONS_INVALID", allow_empty=False),
        "rule_refs": _strings(rule_refs, "TERM_RULE_PACK_RULE_REFS_INVALID", allow_empty=False),
        "frozen_before_evidence": True,
        "authority": _authority(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "logical_hash": logical_hash}


def build_term_qualification_record(
    *,
    candidate: Mapping[str, Any],
    rule_pack: Mapping[str, Any],
    stage_statuses: Mapping[str, Any],
    evidence_refs_by_dimension: Mapping[str, Any],
    disposition: str,
    failure_layer: str | None = None,
    adjudication_decision_ref: str | None = None,
) -> dict[str, Any]:
    if candidate.get("schema") != "ovc-esl-structural-term-candidate/v1":
        raise TermQualificationError("TERM_CANDIDATE_SCHEMA_INVALID")
    if rule_pack.get("schema") != "ovc-esl-term-qualification-rule-pack/v1" or not rule_pack.get("frozen_before_evidence"):
        raise TermQualificationError("TERM_RULE_PACK_INVALID")
    if candidate.get("term_class") != rule_pack.get("term_class"):
        raise TermQualificationError("TERM_RULE_PACK_CLASS_MISMATCH")
    disposition_id = str(disposition)
    if disposition_id not in QUALIFICATION_DISPOSITIONS:
        raise TermQualificationError("TERM_QUALIFICATION_DISPOSITION_INVALID")
    statuses = {str(k): str(v) for k, v in stage_statuses.items()}
    if set(statuses) - set(QUALIFICATION_STAGES):
        raise TermQualificationError("TERM_QUALIFICATION_STAGE_UNKNOWN")
    for stage in rule_pack["required_stages"]:
        if stage not in statuses:
            raise TermQualificationError("TERM_QUALIFICATION_REQUIRED_STAGE_MISSING:" + stage)
    if statuses.get("EMPIRICALLY_OBSERVED") == "PASS" and not any("real" in str(x).lower() or "population" in str(x).lower() for x in evidence_refs_by_dimension.values()):
        raise TermQualificationError("TERM_EMPIRICALLY_OBSERVED_REQUIRES_FROZEN_REAL_POPULATION_EVIDENCE")
    if statuses.get("SEMANTICALLY_QUALIFIED") == "PASS" and not adjudication_decision_ref:
        raise TermQualificationError("TERM_SEMANTICALLY_QUALIFIED_REQUIRES_EXTERNAL_ADJUDICATION_DECISION")
    payload = {
        "schema": "ovc-esl-term-qualification-record/v1",
        "term_generation_id": candidate["term_generation_id"],
        "structural_term_candidate_id": candidate["structural_term_candidate_id"],
        "term_class": candidate["term_class"],
        "rule_pack_id": rule_pack["rule_pack_id"],
        "rule_pack_hash": rule_pack["logical_hash"],
        "stage_statuses": dict(sorted(statuses.items())),
        "evidence_refs_by_dimension": _copy(evidence_refs_by_dimension),
        "disposition": disposition_id,
        "failure_layer": failure_layer,
        "adjudication_decision_ref": adjudication_decision_ref,
        "semantic_admission_state": "NOT_ADMITTED",
        "authority": _authority(),
    }
    _scan_forbidden(payload["evidence_refs_by_dimension"])
    logical_hash = sha256_canonical(payload)
    return {**payload, "term_qualification_record_id": "tqr1:" + logical_hash, "logical_hash": logical_hash}


def build_semantic_admission_proposal(*, term_generation_id: str, qualification_record_id: str, requested_state: str, empirical_scope: Mapping[str, Any], evidence_packet_refs: Sequence[Any], expiry: str | None = None) -> dict[str, Any]:
    requested = str(requested_state)
    if requested == "ADMITTED_ACTIVE":
        raise TermQualificationError("TERM_ADMITTED_ACTIVE_OPERATOR_RESERVED")
    if requested not in ADMISSION_PROPOSAL_STATES:
        raise TermQualificationError("TERM_ADMISSION_PROPOSAL_STATE_INVALID")
    payload = {
        "schema": "ovc-esl-semantic-admission-proposal/v1",
        "term_generation_id": _nonempty(term_generation_id, "TERM_GENERATION_ID_REQUIRED"),
        "qualification_record_id": _nonempty(qualification_record_id, "TERM_QUALIFICATION_RECORD_ID_REQUIRED"),
        "requested_state": requested,
        "empirical_scope": _copy(empirical_scope),
        "evidence_packet_refs": _strings(evidence_packet_refs, "TERM_ADMISSION_EVIDENCE_REQUIRED", allow_empty=False),
        "expiry": expiry,
        "proposal_only": True,
        "registry_mutation": "FORBIDDEN",
        "authority": _authority(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "semantic_admission_proposal_id": "sap1:" + logical_hash, "logical_hash": logical_hash}


def build_term_challenge(*, term_generation_id: str, target: str, evidence_refs: Sequence[Any], recommendation: str, opened_at: str) -> dict[str, Any]:
    target_id = str(target)
    recommendation_id = str(recommendation)
    if target_id not in CHALLENGE_TARGETS:
        raise TermQualificationError("TERM_CHALLENGE_TARGET_INVALID")
    if recommendation_id not in CHALLENGE_RECOMMENDATIONS:
        raise TermQualificationError("TERM_CHALLENGE_RECOMMENDATION_INVALID")
    payload = {
        "schema": "ovc-esl-term-challenge-record/v1",
        "term_generation_id": _nonempty(term_generation_id, "TERM_GENERATION_ID_REQUIRED"),
        "target": target_id,
        "evidence_refs": _strings(evidence_refs, "TERM_CHALLENGE_EVIDENCE_REQUIRED", allow_empty=False),
        "recommendation": recommendation_id,
        "opened_at": _nonempty(opened_at, "TERM_CHALLENGE_OPENED_AT_REQUIRED"),
        "authority_action": "PROPOSAL_ONLY",
        "historical_rewrite": "FORBIDDEN",
        "authority": _authority(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "term_challenge_record_id": "tch1:" + logical_hash, "logical_hash": logical_hash}


def build_transport_candidate(*, term_generation_id: str, source_scope: Mapping[str, Any], target_scope: Mapping[str, Any], evidence_refs: Sequence[Any] = ()) -> dict[str, Any]:
    source = _copy(source_scope)
    target = _copy(target_scope)
    if source == target:
        raise TermQualificationError("TERM_TRANSPORT_TARGET_MUST_DIFFER")
    payload = {
        "schema": "ovc-esl-term-transport-candidate/v1",
        "term_generation_id": _nonempty(term_generation_id, "TERM_GENERATION_ID_REQUIRED"),
        "source_scope": source,
        "target_scope": target,
        "status": "TRANSPORT_EVALUATION_CANDIDATE",
        "target_scope_semantic_authority": "NONE",
        "new_evidence_required": True,
        "evidence_refs": _strings(evidence_refs, "TERM_TRANSPORT_EVIDENCE_INVALID"),
        "authority": _authority(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "term_transport_candidate_id": "ttc1:" + logical_hash, "logical_hash": logical_hash}
