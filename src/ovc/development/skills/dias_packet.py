"""Immutable PACKET_READY/PIP primitives and semantic-reopen policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256, normalize_relative_path
from ovc.development.skills.dias import DiasContractError, DependencyToken


ASSURANCE_CLASSES = frozenset({"A0", "AA1", "AA2", "AA3", "CROSS_BOUNDARY_UNKNOWN"})
PLACEMENT_EVENTS = frozenset({"MAIN_MOVED", "PROVIDER_RERUN", "LEASE_LOST", "RULESET_DRIFT", "PROCESS_RESTART"})
SEMANTIC_REOPEN_EVENTS = frozenset({"PACKET_DEFECT", "MEANING_BEARING_OWNER_CONFLICT"})
KNOWN_EVENTS = PLACEMENT_EVENTS | SEMANTIC_REOPEN_EVENTS | {"FAILED_APPLY_PRECONDITION"}
PRECONDITION_KINDS = frozenset({"PATH_ABSENT", "BLOB_EQUALS", "VALUE_EQUALS", "RULESET_EQUALS", "OWNER_FACT_EQUALS"})


def _required(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise DiasContractError(f"{field} is required")
    return value


@dataclass(frozen=True, order=True)
class ApplyPrecondition:
    key: str
    kind: str
    expected: Any

    def __post_init__(self) -> None:
        _required(self.key, "precondition key")
        if self.kind not in PRECONDITION_KINDS:
            raise DiasContractError("unknown apply precondition kind")

    @property
    def precondition_id(self) -> str:
        return canonical_sha256(asdict(self), role="diasi-apply-precondition/v1")


@dataclass(frozen=True, order=True)
class LogicalChange:
    op: str
    path: str
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.op not in {"ADD", "MODIFY", "DELETE"}:
            raise DiasContractError("unknown logical change operation")
        object.__setattr__(self, "path", normalize_relative_path(self.path))
        if self.op != "DELETE" and (not self.content_sha256 or len(self.content_sha256) != 64):
            raise DiasContractError("non-delete logical change requires SHA-256 content identity")
        if self.op == "DELETE" and self.content_sha256 is not None:
            raise DiasContractError("delete logical change cannot declare replacement content")


@dataclass(frozen=True)
class DependencyFrontier:
    tokens: tuple[str, ...]
    owner_fact_ids: tuple[str, ...]
    unresolved_behavior: str = "BLOCK"

    def __post_init__(self) -> None:
        parsed = tuple(sorted({DependencyToken.parse(token).render() for token in self.tokens}))
        if not parsed:
            raise DiasContractError("dependency frontier cannot be empty")
        if any(len(value) != 64 for value in self.owner_fact_ids):
            raise DiasContractError("owner fact ids must be SHA-256 identities")
        if self.unresolved_behavior != "BLOCK":
            raise DiasContractError("unresolved dependency frontiers must block")
        object.__setattr__(self, "tokens", parsed)
        object.__setattr__(self, "owner_fact_ids", tuple(sorted(set(self.owner_fact_ids))))

    @property
    def frontier_id(self) -> str:
        return canonical_sha256(asdict(self), role="diasi-dependency-frontier/v1")


@dataclass(frozen=True)
class PacketReadyRecord:
    programme_id: str
    packet_id: str
    authority_envelope_id: str
    source_tree: str
    logical_changes: tuple[LogicalChange, ...]
    preconditions: tuple[ApplyPrecondition, ...]
    dependency_frontier_id: str
    test_dependency_manifest_id: str
    status: str = "PACKET_READY"

    def __post_init__(self) -> None:
        _required(self.programme_id, "programme_id")
        _required(self.packet_id, "packet_id")
        if self.status != "PACKET_READY":
            raise DiasContractError("PacketReadyRecord status must be PACKET_READY")
        for field in ("authority_envelope_id", "dependency_frontier_id", "test_dependency_manifest_id"):
            if len(getattr(self, field)) != 64:
                raise DiasContractError(f"{field} must be SHA-256")
        if len(self.source_tree) != 40:
            raise DiasContractError("source_tree must be a Git tree identity")
        if not self.logical_changes or not self.preconditions:
            raise DiasContractError("ready record requires changes and apply preconditions")
        paths = [change.path for change in self.logical_changes]
        if len(paths) != len(set(paths)):
            raise DiasContractError("logical change paths must be unique")
        keys = [condition.key for condition in self.preconditions]
        if len(keys) != len(set(keys)):
            raise DiasContractError("precondition keys must be unique")
        object.__setattr__(self, "logical_changes", tuple(sorted(self.logical_changes, key=lambda change: change.path)))
        object.__setattr__(self, "preconditions", tuple(sorted(self.preconditions, key=lambda condition: condition.key)))

    @property
    def ready_id(self) -> str:
        return canonical_sha256(asdict(self), role="packet-ready-record/v1")


@dataclass(frozen=True)
class ImmutablePacketIntegrationPayload:
    programme_id: str
    packet_id: str
    packet_ready_id: str
    authority_envelope_id: str
    dependency_frontier_id: str
    logical_changes: tuple[LogicalChange, ...]
    preconditions: tuple[ApplyPrecondition, ...]
    assurance_class: str
    completion_transition: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.assurance_class not in ASSURANCE_CLASSES:
            raise DiasContractError("unknown assurance class")
        for field in ("packet_ready_id", "authority_envelope_id", "dependency_frontier_id"):
            if len(getattr(self, field)) != 64:
                raise DiasContractError(f"{field} must be SHA-256")
        if not self.logical_changes or not self.preconditions or not self.completion_transition:
            raise DiasContractError("immutable PIP is incomplete")
        object.__setattr__(self, "logical_changes", tuple(sorted(self.logical_changes, key=lambda change: change.path)))
        object.__setattr__(self, "preconditions", tuple(sorted(self.preconditions, key=lambda condition: condition.key)))
        object.__setattr__(self, "completion_transition", tuple(sorted(self.completion_transition)))

    @classmethod
    def from_ready(
        cls,
        ready: PacketReadyRecord,
        *,
        assurance_class: str,
        completion_transition: Mapping[str, str],
    ) -> "ImmutablePacketIntegrationPayload":
        return cls(
            programme_id=ready.programme_id,
            packet_id=ready.packet_id,
            packet_ready_id=ready.ready_id,
            authority_envelope_id=ready.authority_envelope_id,
            dependency_frontier_id=ready.dependency_frontier_id,
            logical_changes=ready.logical_changes,
            preconditions=ready.preconditions,
            assurance_class=assurance_class,
            completion_transition=tuple(completion_transition.items()),
        )

    @property
    def pip_id(self) -> str:
        return canonical_sha256(asdict(self), role="immutable-packet-integration-payload/v1")


@dataclass(frozen=True)
class ApplicabilityAssessment:
    pip_id: str
    status: str
    semantic_reopen: bool
    reasons: tuple[str, ...]
    placement_recompute_required: bool

    @property
    def assessment_id(self) -> str:
        return canonical_sha256(asdict(self), role="pip-applicability-assessment/v1")


def _precondition_holds(condition: ApplyPrecondition, observed: Mapping[str, Any]) -> bool:
    present = condition.key in observed
    if condition.kind == "PATH_ABSENT":
        return not present
    return present and observed[condition.key] == condition.expected


def assess_applicability(
    pip: ImmutablePacketIntegrationPayload,
    *,
    events: Sequence[str],
    observed_preconditions: Mapping[str, Any],
) -> ApplicabilityAssessment:
    event_set = set(events)
    unknown = sorted(event_set - KNOWN_EVENTS)
    if unknown:
        return ApplicabilityAssessment(pip.pip_id, "BLOCKED_CROSS_BOUNDARY_UNKNOWN", False, tuple(unknown), False)
    failed = sorted(condition.key for condition in pip.preconditions if not _precondition_holds(condition, observed_preconditions))
    semantic = sorted(event_set & SEMANTIC_REOPEN_EVENTS)
    if failed or "FAILED_APPLY_PRECONDITION" in event_set:
        reasons = tuple(["FAILED_APPLY_PRECONDITION", *failed])
        return ApplicabilityAssessment(pip.pip_id, "SEMANTIC_REOPEN_REQUIRED", True, reasons, False)
    if semantic:
        return ApplicabilityAssessment(pip.pip_id, "SEMANTIC_REOPEN_REQUIRED", True, tuple(semantic), False)
    placement = bool(event_set & PLACEMENT_EVENTS)
    status = "PLACEMENT_RECOMPUTE_ONLY" if placement else "APPLICABLE"
    return ApplicabilityAssessment(pip.pip_id, status, False, tuple(sorted(event_set)), placement)


def classify_assurance(tokens: Sequence[str]) -> str:
    kinds = {DependencyToken.parse(token).kind for token in tokens}
    if "CREDENTIAL_REF" in kinds or "SECURITY_PROFILE" in kinds:
        return "CROSS_BOUNDARY_UNKNOWN"
    if {"MAIN", "TREE", "RULESET", "GRT_STATE"} & kinds:
        if "TREE" in kinds and "MAIN" in kinds:
            return "AA3"
        return "AA1"
    if {"OWNER_STATE", "OWNER_FACT", "RECEIPT", "LEDGER_HEAD", "QUALIFICATION", "TRIGGER"} & kinds:
        return "AA2"
    return "A0"


def reconstruct_pip(payload: Mapping[str, Any]) -> ImmutablePacketIntegrationPayload:
    """Fresh-process reconstruction from canonical decoded JSON."""
    try:
        changes = tuple(LogicalChange(**change) for change in payload["logical_changes"])
        conditions = tuple(ApplyPrecondition(**condition) for condition in payload["preconditions"])
        transition = tuple((str(key), str(value)) for key, value in payload["completion_transition"])
        return ImmutablePacketIntegrationPayload(
            programme_id=str(payload["programme_id"]),
            packet_id=str(payload["packet_id"]),
            packet_ready_id=str(payload["packet_ready_id"]),
            authority_envelope_id=str(payload["authority_envelope_id"]),
            dependency_frontier_id=str(payload["dependency_frontier_id"]),
            logical_changes=changes,
            preconditions=conditions,
            assurance_class=str(payload["assurance_class"]),
            completion_transition=transition,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DiasContractError("invalid immutable PIP payload") from exc
