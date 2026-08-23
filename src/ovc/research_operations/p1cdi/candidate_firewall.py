from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

READINESS_RESULTS = (
    "MECHANICAL_REVIEW_READY",
    "NOT_READY",
    "UNRESOLVED",
    "BLOCKED",
)
DERIVATION_RELATIONS = (
    "DIRECT_FORMALISATION_OF",
    "REFINES_DISTINCTION",
    "RESTRICTS_DISTINCTION",
    "COMBINES_DISTINCTIONS",
    "DERIVES_SEQUENCE_FROM",
    "DERIVES_CROSS_SCALE_FROM",
    "USES_AS_NEGATIVE_SPACE",
    "USES_AS_DISCRIMINATOR",
    "PROVENANCE_ONLY",
)
FORBIDDEN_CANDIDATE_OBJECTS = (
    "Path1CandidateProposal",
    "CandidateFreezePacket",
    "ResearchCandidateGeneration",
    "CandidateEvaluationAdmission",
)
FORBIDDEN_REPAIR_SOURCES = ("OPT-C", "OPT-D", "VALIDATION")


def _exact_string(value: Any, name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _refs(value: Sequence[str], name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a sequence")
    rows = [_exact_string(item, name) for item in value]
    if not allow_empty and not rows:
        raise ValueError(f"{name} must be non-empty")
    if len(rows) != len(set(rows)):
        raise ValueError(f"{name} must not contain duplicates")
    return sorted(rows)


def _record_id(prefix: str, body: Mapping[str, Any]) -> str:
    return f"p1:{prefix}:{canonical_sha256(body)}"


def build_proposal_readiness_assessment(
    *,
    generation_id: str,
    source_completeness_refs: Sequence[str],
    result: str | None = None,
    reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    generation = _exact_string(generation_id, "generation_id")
    completeness = _refs(source_completeness_refs, "source_completeness_refs")
    reasons = _refs(reason_codes, "reason_codes")
    resolved_result = result
    if resolved_result is None:
        resolved_result = "MECHANICAL_REVIEW_READY" if completeness else "NOT_READY"
    resolved_result = _exact_string(resolved_result, "result")
    if resolved_result not in READINESS_RESULTS:
        raise ValueError("result is outside the frozen P1CDI readiness vocabulary")
    if resolved_result == "MECHANICAL_REVIEW_READY" and not completeness:
        raise ValueError("MECHANICAL_REVIEW_READY requires source completeness evidence")
    body = {
        "generation_id": generation,
        "result": resolved_result,
        "source_completeness_refs": completeness,
        "reason_codes": reasons,
    }
    return {
        "record_type": "P1ProposalReadinessAssessment",
        "schema_version": "0.1",
        "record_id": _record_id("proposal-readiness", body),
        **body,
        "authority_effect": "NONE",
        "candidate_write": "DENIED",
    }


def build_candidate_derivation_manifest(
    *,
    distinction_generation_refs: Sequence[str],
    candidate_ref: str,
    relation: str,
) -> dict[str, Any]:
    generations = _refs(distinction_generation_refs, "distinction_generation_refs", allow_empty=False)
    candidate = _exact_string(candidate_ref, "candidate_ref")
    relation_name = _exact_string(relation, "relation")
    if relation_name not in DERIVATION_RELATIONS:
        raise ValueError("relation is outside the frozen candidate ancestry registry")
    body = {
        "distinction_generation_refs": generations,
        "candidate_ref": candidate,
        "relation": relation_name,
    }
    return {
        "record_type": "P1CandidateDerivationManifest",
        "schema_version": "0.1",
        "record_id": _record_id("candidate-derivation", body),
        **body,
        "authority_effect": "NONE",
        "candidate_write": "DENIED",
    }


def bind_source_disposition(
    *, candidate_ref: str, source_disposition_ref: str, projected_value: str
) -> dict[str, Any]:
    body = {
        "candidate_ref": _exact_string(candidate_ref, "candidate_ref"),
        "source_disposition_ref": _exact_string(source_disposition_ref, "source_disposition_ref"),
        "projected_value": _exact_string(projected_value, "projected_value"),
    }
    return {
        "record_type": "CandidateDispositionBinding",
        "schema_version": "0.1",
        "record_id": _record_id("candidate-disposition-binding", body),
        **body,
        "authority_effect": "NONE",
        "candidate_write": "DENIED",
    }


def project_freeze_disposition(binding: Mapping[str, Any]) -> dict[str, Any]:
    if binding.get("record_type") != "CandidateDispositionBinding":
        raise ValueError("a lawful CandidateDispositionBinding is required")
    if binding.get("candidate_write") != "DENIED" or binding.get("authority_effect") != "NONE":
        raise PermissionError("P1CDI candidate disposition projection may not write candidate state")
    return {
        "record_type": "P1CandidateDispositionProjection",
        "schema_version": "0.1",
        "candidate_ref": _exact_string(binding.get("candidate_ref"), "candidate_ref"),
        "projected_value": _exact_string(binding.get("projected_value"), "projected_value"),
        "source_disposition_ref": _exact_string(binding.get("source_disposition_ref"), "source_disposition_ref"),
        "candidate_generation_creation": "DENIED",
        "freeze_actuation": "DENIED",
        "authority_effect": "NONE",
    }


def assert_candidate_firewall(record: Mapping[str, Any]) -> None:
    if record.get("authority_effect") != "NONE":
        raise PermissionError("P1CDI candidate-link records must have authority_effect NONE")
    if record.get("candidate_write") not in {None, "DENIED"}:
        raise PermissionError("P1CDI candidate write authority is denied")
    if record.get("record_type") in FORBIDDEN_CANDIDATE_OBJECTS:
        raise PermissionError("P1CDI may not create DMRP candidate/freeze/admission objects")
    forbidden_fields = {
        "candidate_payload",
        "candidate_semantic_bytes",
        "freeze_decision",
        "candidate_generation_id",
        "candidate_evaluation_admission",
        "opt_c_outcome",
        "opt_d_result",
        "validation_result",
    }
    present = sorted(forbidden_fields.intersection(record))
    if present:
        raise PermissionError(f"P1CDI candidate firewall forbids fields: {present}")


def preserve_frozen_candidate(
    *, frozen_candidate_ref: str, frozen_semantic_sha256: str, later_evidence_refs: Sequence[str]
) -> dict[str, Any]:
    candidate = _exact_string(frozen_candidate_ref, "frozen_candidate_ref")
    frozen_hash = _exact_string(frozen_semantic_sha256, "frozen_semantic_sha256")
    evidence = _refs(later_evidence_refs, "later_evidence_refs", allow_empty=False)
    body = {
        "frozen_candidate_ref": candidate,
        "frozen_semantic_sha256": frozen_hash,
        "later_evidence_refs": evidence,
    }
    return {
        "record_type": "P1PostFreezeEvidenceBinding",
        "schema_version": "0.1",
        "record_id": _record_id("post-freeze-evidence", body),
        **body,
        "semantic_mutation": "DENIED",
        "required_route": "SUCCESSOR_LINEAGE_ONLY",
        "authority_effect": "NONE",
    }


def assert_no_outcome_repair(*, source_class: str, target_generation_ref: str) -> dict[str, Any]:
    source = _exact_string(source_class, "source_class").upper()
    target = _exact_string(target_generation_ref, "target_generation_ref")
    if source in FORBIDDEN_REPAIR_SOURCES:
        return {
            "record_type": "P1OutcomeRepairDenial",
            "schema_version": "0.1",
            "source_class": source,
            "target_generation_ref": target,
            "result": "DENIED",
            "authority_effect": "NONE",
        }
    raise ValueError("source_class is not a downstream outcome source covered by this firewall")
