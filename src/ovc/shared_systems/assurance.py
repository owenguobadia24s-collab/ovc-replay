"""Inactive claim-scoped assurance/currentness/change-impact reference kernel.

The module deliberately produces evidence and deterministic projections only. It
does not qualify a scientific result, make an operator decision, revoke authority,
or mutate an owner registry.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable


class SharedAssuranceError(ValueError):
    """A fail-closed Shared Systems WP4 contract violation."""


def _hash(value: Any) -> str:
    try:
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SharedAssuranceError("NON_CANONICAL_ASSURANCE_VALUE") from exc
    return hashlib.sha256(raw).hexdigest()


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise SharedAssuranceError(f"{field.upper()}_REQUIRED")
    return value


def _refs(values: tuple[str, ...], field: str, *, allow_empty: bool = False) -> None:
    if not isinstance(values, tuple) or (not values and not allow_empty):
        raise SharedAssuranceError(f"{field.upper()}_REQUIRED")
    if any(not isinstance(value, str) or not value for value in values):
        raise SharedAssuranceError(f"{field.upper()}_INVALID")
    if len(values) != len(set(values)):
        raise SharedAssuranceError(f"{field.upper()}_DUPLICATE")


ASSURANCE_CLASSES = frozenset(
    {
        "CONTRACT_CONFORMANCE",
        "SEMANTIC_FIDELITY",
        "DETERMINISM_REPLAY",
        "DEPENDENCY_INTEGRITY",
        "EVIDENCE_INTEGRITY",
        "OPERATIONAL_RELIABILITY",
        "SECURITY_INTEGRITY",
        "AUTHORITY_INTEGRITY",
        "SCIENTIFIC_QUALIFICATION",
        "NON_TRANSITIVITY",
    }
)
ASSURANCE_STATUSES = frozenset({"PASS", "FAIL", "NOT_EVALUABLE"})
QUALIFICATION_STATUSES = frozenset(
    {"QUALIFIED", "NOT_QUALIFIED", "NOT_EVALUABLE"}
)
CURRENTNESS_STATUSES = frozenset(
    {"CURRENT", "STALE", "REVOKED", "QUARANTINED", "SUPERSEDED", "UNKNOWN"}
)
CHANGE_CLASSIFICATIONS = frozenset(
    {"SEMANTIC", "IMPLEMENTATION_EQUIVALENT", "AMBIGUOUS"}
)
IMPACT_OBLIGATIONS = frozenset(
    {"REPLAY", "REBUILD", "RETEST", "STALE_QUALIFICATION", "QUARANTINE"}
)


@dataclass(frozen=True)
class AssuranceAssertionSpec:
    assertion_id: str
    version: str
    owner: str
    assurance_class: str
    subject_contract: str
    claim: str
    applicability: str
    prerequisites: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    evaluation_method: str
    blocking_policy: str
    failure_disposition: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.assurance_class not in ASSURANCE_CLASSES:
            raise SharedAssuranceError("ASSURANCE_CLASS_UNKNOWN")
        if self.authority_effect != "NONE":
            raise SharedAssuranceError("ASSURANCE_AUTHORITY_LAUNDERING_FORBIDDEN")
        for field in (
            "assertion_id",
            "version",
            "owner",
            "subject_contract",
            "claim",
            "applicability",
            "evaluation_method",
            "blocking_policy",
            "failure_disposition",
        ):
            _text(getattr(self, field), field)
        _refs(self.prerequisites, "prerequisites", allow_empty=True)
        _refs(self.evidence_requirements, "evidence_requirements")


@dataclass(frozen=True)
class AssuranceAssertionResult:
    assertion_id: str
    subject_ref: str
    status: str
    evidence_refs: tuple[str, ...]
    reason_codes: tuple[str, ...] = ()
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        _text(self.assertion_id, "assertion_id")
        _text(self.subject_ref, "subject_ref")
        if self.status not in ASSURANCE_STATUSES:
            raise SharedAssuranceError("ASSURANCE_STATUS_UNKNOWN")
        if self.authority_effect != "NONE":
            raise SharedAssuranceError("ASSURANCE_AUTHORITY_LAUNDERING_FORBIDDEN")
        _refs(
            self.evidence_refs,
            "evidence_refs",
            allow_empty=self.status == "NOT_EVALUABLE",
        )
        if self.status == "NOT_EVALUABLE" and not self.reason_codes:
            raise SharedAssuranceError("NOT_EVALUABLE_REASON_REQUIRED")
        _refs(self.reason_codes, "reason_codes", allow_empty=self.status == "PASS")


@dataclass(frozen=True)
class AssuranceSuite:
    suite_id: str
    assertion_specs: tuple[AssuranceAssertionSpec, ...]

    def __post_init__(self) -> None:
        _text(self.suite_id, "suite_id")
        ids = [item.assertion_id for item in self.assertion_specs]
        if not ids or len(ids) != len(set(ids)):
            raise SharedAssuranceError("ASSURANCE_SUITE_AMBIGUOUS")


@dataclass(frozen=True)
class AssurancePacket:
    packet_id: str
    suite_id: str
    subject_ref: str
    results: tuple[AssuranceAssertionResult, ...]
    disposition: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("packet_id", "suite_id", "subject_ref"):
            _text(getattr(self, field), field)
        if self.authority_effect != "NONE":
            raise SharedAssuranceError("ASSURANCE_AUTHORITY_LAUNDERING_FORBIDDEN")
        result_ids = [item.assertion_id for item in self.results]
        if not result_ids or len(result_ids) != len(set(result_ids)):
            raise SharedAssuranceError("ASSURANCE_PACKET_AMBIGUOUS")
        expected = (
            "BLOCKED"
            if any(item.status == "FAIL" for item in self.results)
            else "NOT_EVALUABLE"
            if any(item.status == "NOT_EVALUABLE" for item in self.results)
            else "PASS"
        )
        if self.disposition != expected:
            raise SharedAssuranceError("MANDATORY_FAILURE_AVERAGING_FORBIDDEN")

    @property
    def logical_id(self) -> str:
        return _hash(asdict(self))


@dataclass(frozen=True)
class QualificationRecord:
    qualification_id: str
    target_ref: str
    release_ref: str
    generation_ref: str
    capability: str
    role: str
    environment_ref: str | None
    source_ref: str | None
    semantic_scope: str
    evidence_refs: tuple[str, ...]
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "qualification_id",
            "target_ref",
            "release_ref",
            "generation_ref",
            "capability",
            "role",
            "semantic_scope",
        ):
            _text(getattr(self, field), field)
        for field in ("environment_ref", "source_ref"):
            value = getattr(self, field)
            if value is not None:
                _text(value, field)
        _refs(self.evidence_refs, "evidence_refs")
        if self.status not in QUALIFICATION_STATUSES:
            raise SharedAssuranceError("QUALIFICATION_STATUS_UNKNOWN")
        if self.authority_effect != "NONE":
            raise SharedAssuranceError("QUALIFICATION_AUTHORITY_LAUNDERING_FORBIDDEN")


@dataclass(frozen=True)
class QualificationCurrentness:
    qualification_id: str
    status: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.qualification_id, "qualification_id")
        if self.status not in CURRENTNESS_STATUSES:
            raise SharedAssuranceError("CURRENTNESS_STATUS_UNKNOWN")
        _refs(self.reason_codes, "reason_codes", allow_empty=self.status == "CURRENT")


def qualification_currentness(
    record: QualificationRecord,
    *,
    target_ref: str,
    release_ref: str,
    generation_ref: str,
    capability: str,
    role: str,
    environment_ref: str | None,
    source_ref: str | None,
    semantic_scope: str,
    revoked: bool = False,
    quarantined: bool = False,
    superseded: bool = False,
) -> QualificationCurrentness:
    terminal_flags = (revoked, quarantined, superseded)
    if sum(terminal_flags) > 1:
        raise SharedAssuranceError("CURRENTNESS_DISPOSITION_AMBIGUOUS")
    if revoked:
        return QualificationCurrentness(
            record.qualification_id, "REVOKED", ("EXPLICIT_REVOCATION",)
        )
    if quarantined:
        return QualificationCurrentness(
            record.qualification_id, "QUARANTINED", ("MATERIAL_INCIDENT",)
        )
    if superseded:
        return QualificationCurrentness(
            record.qualification_id, "SUPERSEDED", ("EXPLICIT_SUPERSESSION",)
        )
    if record.status != "QUALIFIED":
        return QualificationCurrentness(
            record.qualification_id,
            "UNKNOWN",
            (f"QUALIFICATION_RECORD_{record.status}",),
        )
    drift = []
    for name, current, expected in (
        ("TARGET", target_ref, record.target_ref),
        ("RELEASE", release_ref, record.release_ref),
        ("GENERATION", generation_ref, record.generation_ref),
        ("CAPABILITY", capability, record.capability),
        ("ROLE", role, record.role),
        ("ENVIRONMENT", environment_ref, record.environment_ref),
        ("SOURCE", source_ref, record.source_ref),
        ("SEMANTIC_SCOPE", semantic_scope, record.semantic_scope),
    ):
        if current != expected:
            drift.append(f"{name}_DRIFT")
    return QualificationCurrentness(
        record.qualification_id,
        "STALE" if drift else "CURRENT",
        tuple(drift),
    )


@dataclass(frozen=True)
class ChangeAssessment:
    change_id: str
    changed_refs: tuple[str, ...]
    classification: str
    reason_codes: tuple[str, ...]
    equivalence_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.change_id, "change_id")
        _refs(self.changed_refs, "changed_refs")
        _refs(self.reason_codes, "reason_codes")
        if self.classification not in CHANGE_CLASSIFICATIONS:
            raise SharedAssuranceError("CHANGE_CLASSIFICATION_UNKNOWN")
        if (
            self.classification == "IMPLEMENTATION_EQUIVALENT"
            and not self.equivalence_evidence_refs
        ):
            raise SharedAssuranceError("EQUIVALENCE_PROOF_REQUIRED")
        _refs(
            self.equivalence_evidence_refs,
            "equivalence_evidence_refs",
            allow_empty=self.classification != "IMPLEMENTATION_EQUIVALENT",
        )


@dataclass(frozen=True)
class ImpactDependencyEdge:
    source_ref: str
    dependent_ref: str
    obligation: str

    def __post_init__(self) -> None:
        _text(self.source_ref, "source_ref")
        _text(self.dependent_ref, "dependent_ref")
        if self.source_ref == self.dependent_ref:
            raise SharedAssuranceError("IMPACT_SELF_EDGE_FORBIDDEN")
        if self.obligation not in IMPACT_OBLIGATIONS:
            raise SharedAssuranceError("IMPACT_OBLIGATION_UNKNOWN")


@dataclass(frozen=True)
class ReplayObligation:
    subject_ref: str
    reason: str
    status: str = "REQUIRED"

    def __post_init__(self) -> None:
        _text(self.subject_ref, "subject_ref")
        _text(self.reason, "reason")
        if self.status != "REQUIRED":
            raise SharedAssuranceError("REPLAY_OBLIGATION_STATUS_INVALID")


@dataclass(frozen=True)
class InvalidationPlan:
    change_id: str
    invalidated_refs: tuple[str, ...]
    unaffected_refs: tuple[str, ...]
    replay_obligations: tuple[ReplayObligation, ...]
    conservative_fallback: bool
    unaffected_proof: str
    unresolved_impacts: tuple[str, ...]


def build_invalidation_plan(
    assessment: ChangeAssessment,
    edges: Iterable[ImpactDependencyEdge],
    universe: Iterable[str],
) -> InvalidationPlan:
    universe_refs = tuple(universe)
    _refs(universe_refs, "universe")
    all_refs = set(universe_refs)
    changed = set(assessment.changed_refs)
    if not changed <= all_refs:
        raise SharedAssuranceError("CHANGE_REF_UNKNOWN")

    edge_list = tuple(edges)
    edge_keys = [
        (edge.source_ref, edge.dependent_ref, edge.obligation) for edge in edge_list
    ]
    if len(edge_keys) != len(set(edge_keys)):
        raise SharedAssuranceError("IMPACT_EDGE_DUPLICATE")
    if any(
        edge.source_ref not in all_refs or edge.dependent_ref not in all_refs
        for edge in edge_list
    ):
        raise SharedAssuranceError("IMPACT_EDGE_REF_UNKNOWN")

    conservative = assessment.classification == "AMBIGUOUS"
    invalidated = set(all_refs) if conservative else set(changed)
    if assessment.classification == "SEMANTIC":
        while True:
            before = len(invalidated)
            invalidated.update(
                edge.dependent_ref
                for edge in edge_list
                if edge.source_ref in invalidated
            )
            if len(invalidated) == before:
                break

    reason = (
        "AMBIGUOUS_CONSERVATIVE_FALLBACK"
        if conservative
        else "IMPLEMENTATION_EQUIVALENCE_RETEST"
        if assessment.classification == "IMPLEMENTATION_EQUIVALENT"
        else "EXPLICIT_DEPENDENCY_CLOSURE"
    )
    replay_obligations = tuple(
        ReplayObligation(subject_ref, reason) for subject_ref in sorted(invalidated)
    )
    unaffected = tuple(sorted(all_refs - invalidated))
    proof_payload = {
        "change_id": assessment.change_id,
        "classification": assessment.classification,
        "universe": sorted(all_refs),
        "edges": sorted(edge_keys),
        "invalidated_refs": sorted(invalidated),
        "unaffected_refs": list(unaffected),
    }
    return InvalidationPlan(
        assessment.change_id,
        tuple(sorted(invalidated)),
        unaffected,
        replay_obligations,
        conservative,
        _hash(proof_payload),
        ("DECLARED_UNIVERSE_IMPACT_UNRESOLVED",) if conservative else (),
    )


@dataclass(frozen=True)
class IncidentRecord:
    incident_id: str
    subject_ref: str
    evidence_refs: tuple[str, ...]
    description: str
    impact_assessment_ref: str
    rollback_ref: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "incident_id",
            "subject_ref",
            "description",
            "impact_assessment_ref",
            "rollback_ref",
        ):
            _text(getattr(self, field), field)
        _refs(self.evidence_refs, "evidence_refs")
        if self.authority_effect != "NONE":
            raise SharedAssuranceError("INCIDENT_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class QuarantineRecord:
    quarantine_id: str
    incident_id: str
    subject_ref: str
    evidence_refs: tuple[str, ...]
    rollback_ref: str
    release_condition_ref: str
    deleted: bool = False

    def __post_init__(self) -> None:
        for field in (
            "quarantine_id",
            "incident_id",
            "subject_ref",
            "rollback_ref",
            "release_condition_ref",
        ):
            _text(getattr(self, field), field)
        _refs(self.evidence_refs, "evidence_refs")
        if self.deleted:
            raise SharedAssuranceError("QUARANTINE_EVIDENCE_PRESERVATION_REQUIRED")


def deterministic_read_model(records: Iterable[Any]) -> dict[str, Any]:
    rows = []
    for record in records:
        try:
            rows.append(asdict(record))
        except TypeError as exc:
            raise SharedAssuranceError("READ_MODEL_RECORD_NOT_DATACLASS") from exc
    rows.sort(
        key=lambda row: json.dumps(
            row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    )
    payload = {"rows": rows}
    return {
        **payload,
        "logical_id": _hash(payload),
        "rebuildable": True,
        "authority_effect": "NONE",
    }
