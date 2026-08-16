"""Authority-delta gate classification for the OVC operator-reserved gate doctrine.

The classifier is deliberately small and deterministic.  It does not infer authority from
names, gate ordinals, programme history or recommendations.  Callers must provide the
resolved current envelope and proposed PASS effect as exact machine evidence and supply
the resulting net-new authority reason codes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable

from .identity import canonical_sha256


CLASSIFIER_VERSION = "OVC-OPERATOR-RESERVED-GATE-CLASSIFIER-v0.1"


class GateFunction(str, Enum):
    ASSURANCE = "ASSURANCE"
    REVIEW = "REVIEW"
    AUTHORITY_DECISION = "AUTHORITY_DECISION"
    MIXED = "MIXED"


class ExecutionClass(str, Enum):
    AUTO_RATIFIABLE = "AUTO_RATIFIABLE"
    REVIEW_PREREQUISITE = "REVIEW_PREREQUISITE"
    OPERATOR_REQUIRED = "OPERATOR_REQUIRED"
    BLOCKED = "BLOCKED"
    HARD_DENY = "HARD_DENY"


RESERVED_DELTA_CODES = frozenset(
    {
        "OPR.MANDATE_CHANGE",
        "OPR.SCOPE_EXPANSION",
        "OPR.REAL_SOURCE_TRANSITION",
        "OPR.ACTIVATION",
        "OPR.SCIENTIFIC_PROMOTION",
        "OPR.RESEARCH_ROLE",
        "OPR.GOVERNANCE_CHANGE",
        "OPR.OWNER_CHOICE",
        "OPR.FROZEN_CONTRACT_CHANGE",
        "OPR.WRITE_AUTHORITY",
        "OPR.PUBLICATION",
        "OPR.EXPOSURE",
        "OPR.DESTRUCTIVE",
        "OPR.TEMPO_EXPANSION",
        "OPR.OVERRIDE",
        "OPR.AUTHORITATIVE_DISCRETION",
    }
)

AUTO_REASON_CODES = frozenset(
    {
        "AUTO.NO_AUTHORITY_DELTA",
        "AUTO.ALREADY_DELEGATED",
        "AUTO.MECHANICAL_CONFORMANCE",
        "AUTO.ASSURANCE_ONLY",
        "AUTO.REPAIR_WITHIN_SCOPE",
        "AUTO.OPERATIONAL_CHOICE_WITHIN_BUDGET",
        "AUTO.CLOSEOUT_ONLY",
        "AUTO.READ_ONLY_ALREADY_LAWFUL",
    }
)

REVIEW_REASON_CODES = frozenset(
    {
        "REVIEW.INDEPENDENT_ASSURANCE",
        "REVIEW.SOURCE_OWNER",
        "REVIEW.SEMANTIC_CONFORMANCE",
        "REVIEW.USABILITY_NON_ACTIVATING",
    }
)

BLOCK_REASON_CODES = frozenset(
    {
        "BLOCK.MISSING_AUTHORITY",
        "BLOCK.MISSING_ARTIFACT",
        "BLOCK.SOURCE_CONFLICT",
        "BLOCK.AUTHORITY_EFFECT_UNKNOWN",
        "BLOCK.UNRESOLVED_SEMANTICS",
        "BLOCK.NON_REPRODUCIBLE_EVIDENCE",
        "BLOCK.CAPACITY_EXCEEDED",
    }
)

DENY_REASON_CODES = frozenset(
    {
        "DENY.PROTECTED_VALIDATION",
        "DENY.FORCE_PUSH",
        "DENY.HISTORY_REWRITE",
        "DENY.OUT_OF_SCOPE_EXECUTION",
        "DENY.UNAUTHORISED_EXPOSURE",
    }
)


def _stable(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


@dataclass(frozen=True)
class GateAssessmentInput:
    """Fully resolved evidence needed to classify one exact gate instance."""

    gate_id: str
    gate_instance_id: str
    programme_id: str
    plan_id: str
    plan_version: str
    packet_id: str
    baseline_commit: str
    candidate_commit: str
    current_authority_envelope_id: str
    current_authority_hash: str
    proposed_pass_effect_hash: str
    proposed_authority_hash: str
    authority_delta: tuple[str, ...] = ()
    already_delegated_delta: tuple[str, ...] = ()
    net_new_delta: tuple[str, ...] = ()
    required_reviews: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    hard_denies: tuple[str, ...] = ()
    authoritative_discretion_required: bool = False
    acceptance_conditions_passed: bool = False
    qa_status: str = "UNKNOWN"
    blocking_issue_count: int = 0
    rollback_defined: bool = False
    gate_function_hint: GateFunction | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "authority_delta", _stable(self.authority_delta))
        object.__setattr__(self, "already_delegated_delta", _stable(self.already_delegated_delta))
        object.__setattr__(self, "net_new_delta", _stable(self.net_new_delta))
        object.__setattr__(self, "required_reviews", _stable(self.required_reviews))
        object.__setattr__(self, "blockers", _stable(self.blockers))
        object.__setattr__(self, "hard_denies", _stable(self.hard_denies))
        object.__setattr__(self, "evidence_refs", _stable(self.evidence_refs))
        if self.blocking_issue_count < 0:
            raise ValueError("blocking_issue_count must be >= 0")
        delegated = set(self.already_delegated_delta)
        net_new = set(self.net_new_delta)
        if delegated & net_new:
            raise ValueError("a delta cannot be both already delegated and net-new")


@dataclass(frozen=True)
class GateAuthorityAssessment:
    gate_id: str
    gate_instance_id: str
    programme_id: str
    plan_id: str
    plan_version: str
    packet_id: str
    baseline_commit: str
    candidate_commit: str
    current_authority_envelope_id: str
    current_authority_hash: str
    proposed_pass_effect_hash: str
    proposed_authority_hash: str
    authority_delta: tuple[str, ...]
    already_delegated_delta: tuple[str, ...]
    net_new_delta: tuple[str, ...]
    reserved_predicate_hits: tuple[str, ...]
    required_reviews: tuple[str, ...]
    blockers: tuple[str, ...]
    hard_denies: tuple[str, ...]
    gate_function: str
    execution_class: str
    reason_codes: tuple[str, ...]
    classifier_version: str
    evidence_refs: tuple[str, ...]

    @property
    def assessment_id(self) -> str:
        return canonical_sha256(asdict(self), role="GATE_AUTHORITY_ASSESSMENT")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["assessment_id"] = self.assessment_id
        return payload


def _gate_function(inp: GateAssessmentInput, reserved_hits: tuple[str, ...]) -> GateFunction:
    if inp.gate_function_hint is not None:
        return inp.gate_function_hint
    has_review = bool(inp.required_reviews)
    has_authority = bool(reserved_hits) or inp.authoritative_discretion_required
    if has_review and has_authority:
        return GateFunction.MIXED
    if has_authority:
        return GateFunction.AUTHORITY_DECISION
    if has_review:
        return GateFunction.REVIEW
    return GateFunction.ASSURANCE


def classify_gate(inp: GateAssessmentInput) -> GateAuthorityAssessment:
    """Classify one exact gate instance without inferring missing authority.

    Precedence is HARD_DENY -> BLOCKED -> OPERATOR_REQUIRED ->
    REVIEW_PREREQUISITE -> AUTO_RATIFIABLE -> BLOCKED.
    """

    hard_denies = _stable(inp.hard_denies)
    blockers = _stable(inp.blockers)
    reserved_hits = _stable(code for code in inp.net_new_delta if code in RESERVED_DELTA_CODES)
    if inp.authoritative_discretion_required:
        reserved_hits = _stable((*reserved_hits, "OPR.AUTHORITATIVE_DISCRETION"))

    gate_function = _gate_function(inp, reserved_hits)

    if hard_denies:
        execution_class = ExecutionClass.HARD_DENY
        reasons = hard_denies
    elif blockers:
        execution_class = ExecutionClass.BLOCKED
        reasons = blockers
    elif reserved_hits:
        execution_class = ExecutionClass.OPERATOR_REQUIRED
        reasons = reserved_hits
    elif inp.required_reviews:
        execution_class = ExecutionClass.REVIEW_PREREQUISITE
        reasons = _stable(inp.required_reviews)
    elif (
        inp.acceptance_conditions_passed
        and inp.qa_status == "PASS"
        and inp.blocking_issue_count == 0
        and inp.rollback_defined
    ):
        execution_class = ExecutionClass.AUTO_RATIFIABLE
        if inp.authority_delta and set(inp.authority_delta) <= set(inp.already_delegated_delta):
            reasons = ("AUTO.ALREADY_DELEGATED",)
        elif not inp.net_new_delta:
            reasons = ("AUTO.NO_AUTHORITY_DELTA",)
        else:
            reasons = ("AUTO.ASSURANCE_ONLY",)
    else:
        execution_class = ExecutionClass.BLOCKED
        reasons = ("BLOCK.UNRESOLVED_SEMANTICS",)

    return GateAuthorityAssessment(
        gate_id=inp.gate_id,
        gate_instance_id=inp.gate_instance_id,
        programme_id=inp.programme_id,
        plan_id=inp.plan_id,
        plan_version=inp.plan_version,
        packet_id=inp.packet_id,
        baseline_commit=inp.baseline_commit,
        candidate_commit=inp.candidate_commit,
        current_authority_envelope_id=inp.current_authority_envelope_id,
        current_authority_hash=inp.current_authority_hash,
        proposed_pass_effect_hash=inp.proposed_pass_effect_hash,
        proposed_authority_hash=inp.proposed_authority_hash,
        authority_delta=inp.authority_delta,
        already_delegated_delta=inp.already_delegated_delta,
        net_new_delta=inp.net_new_delta,
        reserved_predicate_hits=reserved_hits,
        required_reviews=inp.required_reviews,
        blockers=blockers,
        hard_denies=hard_denies,
        gate_function=gate_function.value,
        execution_class=execution_class.value,
        reason_codes=reasons,
        classifier_version=CLASSIFIER_VERSION,
        evidence_refs=inp.evidence_refs,
    )


@dataclass(frozen=True)
class GateMigrationRecord:
    gate_id: str
    gate_instance_id: str
    programme_id: str
    legacy_classification: str
    legacy_source_ref: str
    new_classification: str
    classifier_version: str
    migration_reason: tuple[str, ...]
    authority_delta: tuple[str, ...]
    assessment_id: str
    effective_from: str

    @property
    def migration_id(self) -> str:
        return canonical_sha256(asdict(self), role="GATE_MIGRATION_RECORD")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["migration_id"] = self.migration_id
        return payload


def migrate_gate(
    *,
    legacy_classification: str,
    legacy_source_ref: str,
    assessment: GateAuthorityAssessment,
    effective_from: str,
) -> GateMigrationRecord:
    """Create a forward-only migration record; historical decisions are untouched."""

    return GateMigrationRecord(
        gate_id=assessment.gate_id,
        gate_instance_id=assessment.gate_instance_id,
        programme_id=assessment.programme_id,
        legacy_classification=legacy_classification,
        legacy_source_ref=legacy_source_ref,
        new_classification=assessment.execution_class,
        classifier_version=assessment.classifier_version,
        migration_reason=assessment.reason_codes,
        authority_delta=assessment.authority_delta,
        assessment_id=assessment.assessment_id,
        effective_from=effective_from,
    )
