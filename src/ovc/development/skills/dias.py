"""Deterministic common substrate for the DIASI programme.

This module is deliberately owner-local and side-effect free.  It classifies
consequences, binds authority and dependency identities, and derives a shadow
current-execution projection without creating a scheduler, writer, or new
authority source.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256, normalize_relative_path


class DiasContractError(ValueError):
    """Raised when a DIASI record is incomplete, ambiguous, or unsafe."""


class OwnerFactConflict(DiasContractError):
    """Raised when equally authoritative owner facts disagree."""


class OwnerFactUnresolved(DiasContractError):
    """Raised when an owner fact has no authoritative candidate."""


FLOW_EFFECTS = frozenset(
    {
        "SCHEDULE",
        "ROUTE",
        "RETRY",
        "PLACEMENT",
        "LEASE",
        "RECONCILE",
        "EVENT_CURSOR",
        "RELEASE_SUCCESSOR",
    }
)
EVIDENCE_EFFECTS = frozenset(
    {
        "PRODUCE_EVIDENCE",
        "CONSUME_EVIDENCE",
        "VALIDATE",
        "QUALIFY",
        "PUBLISH_EVIDENCE",
        "CHANGE_SOURCE_CONSUMER_ROLE",
        "CHANGE_PROTECTED_POPULATION",
        "CHANGE_RESEARCH_ROLE",
    }
)
AUTHORITY_EFFECTS = frozenset(
    {
        "GRANT",
        "REVOKE",
        "CUTOVER",
        "FREEZE_INTAKE",
        "TRANSFER_WRITER",
        "RETIRE",
        "REMOVE",
        "PROOF_SUBSTITUTE",
        "ASSURANCE_COMPRESS",
        "LIVE_WRITE",
        "EXPOSURE",
        "MARKET_EXECUTION",
        "CHANGE_RULESET",
        "CHANGE_OWNER",
    }
)
KNOWN_EFFECTS = FLOW_EFFECTS | EVIDENCE_EFFECTS | AUTHORITY_EFFECTS
PLANE_ORDER = {"FLOW": 0, "EVIDENCE": 1, "AUTHORITY": 2}


def _required(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DiasContractError(f"{field} is required")
    return value


def _unique(values: Iterable[str], field: str) -> tuple[str, ...]:
    materialised = tuple(values)
    if any(not isinstance(value, str) or not value for value in materialised):
        raise DiasContractError(f"{field} contains an empty or non-string value")
    if len(set(materialised)) != len(materialised):
        raise DiasContractError(f"{field} contains duplicates")
    return tuple(sorted(materialised))


@dataclass(frozen=True)
class ProgrammeAuthorityEnvelope:
    programme_id: str
    plan_id: str
    packet_id: str
    gate_id: str
    authority_class: str
    authority_sources: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    denied_actions: tuple[str, ...]
    write_families: tuple[str, ...]
    reserved_boundaries: tuple[str, ...] = ()
    rollback: str = "FORWARD_DISABLE_AND_PRESERVE_EVIDENCE"
    expires_on: str | None = None

    def __post_init__(self) -> None:
        for field in ("programme_id", "plan_id", "packet_id", "gate_id", "authority_class", "rollback"):
            _required(getattr(self, field), field)
        if self.authority_class not in {"AUTO_EXECUTABLE", "OPERATOR_REQUIRED", "HARD_DENY"}:
            raise DiasContractError("unknown authority_class")
        if not self.authority_sources:
            raise DiasContractError("authority_sources must be source-bound")
        sources = tuple(normalize_relative_path(path) for path in self.authority_sources)
        writes = tuple(normalize_relative_path(path) for path in self.write_families)
        allowed = _unique(self.allowed_actions, "allowed_actions")
        denied = _unique(self.denied_actions, "denied_actions")
        if set(allowed) & set(denied):
            raise DiasContractError("an action cannot be both allowed and denied")
        object.__setattr__(self, "authority_sources", tuple(sorted(sources)))
        object.__setattr__(self, "write_families", tuple(sorted(writes)))
        object.__setattr__(self, "allowed_actions", allowed)
        object.__setattr__(self, "denied_actions", denied)
        object.__setattr__(self, "reserved_boundaries", _unique(self.reserved_boundaries, "reserved_boundaries"))

    @property
    def envelope_id(self) -> str:
        return canonical_sha256(asdict(self), role="programme-authority-envelope/v1")

    def permits(self, action: str) -> bool:
        _required(action, "action")
        return action in self.allowed_actions and action not in self.denied_actions


@dataclass(frozen=True)
class ConsequenceClassification:
    action_id: str
    effects: tuple[str, ...]
    planes: tuple[str, ...]
    controlling_plane: str
    requires_split: bool
    disposition: str

    @property
    def classification_id(self) -> str:
        return canonical_sha256(asdict(self), role="consequence-classification/v1")


def classify_consequence(action: Mapping[str, Any]) -> ConsequenceClassification:
    """Classify declared effects; unknown or implicit effects fail closed."""

    action_id = _required(str(action.get("action_id", "")), "action_id")
    raw_effects = action.get("effects")
    if not isinstance(raw_effects, Sequence) or isinstance(raw_effects, (str, bytes)) or not raw_effects:
        raise DiasContractError("effects must be a non-empty sequence")
    effects = _unique((str(value) for value in raw_effects), "effects")
    unknown = sorted(set(effects) - KNOWN_EFFECTS)
    if unknown:
        raise DiasContractError(f"unknown consequence effects: {unknown}")

    planes: set[str] = set()
    if set(effects) & FLOW_EFFECTS:
        planes.add("FLOW")
    if set(effects) & EVIDENCE_EFFECTS:
        planes.add("EVIDENCE")
    if set(effects) & AUTHORITY_EFFECTS:
        planes.add("AUTHORITY")
    if action.get("source_consumer_role_change") is True:
        planes.add("EVIDENCE")
    if action.get("authority_delta") not in (None, "", "NONE"):
        planes.add("AUTHORITY")
    if not planes:
        raise DiasContractError("no consequence plane resolved")

    ordered = tuple(sorted(planes, key=PLANE_ORDER.__getitem__))
    controlling = ordered[-1]
    split = len(ordered) > 1 and "AUTHORITY" in planes
    disposition = "SPLIT_AND_HOLD_AUTHORITY_CONSEQUENCE" if split else f"CLASSIFIED_{controlling}"
    return ConsequenceClassification(
        action_id=action_id,
        effects=effects,
        planes=ordered,
        controlling_plane=controlling,
        requires_split=split,
        disposition=disposition,
    )


TOKEN_TYPES = frozenset(
    {
        "MAIN",
        "TREE",
        "RULESET",
        "GRT_STATE",
        "OWNER_STATE",
        "OWNER_FACT",
        "RECEIPT",
        "LEDGER_HEAD",
        "QUALIFICATION",
        "SECURITY_PROFILE",
        "TRIGGER",
        "CREDENTIAL_REF",
    }
)
TOKEN_RE = re.compile(r"^(?P<kind>[A-Z][A-Z0-9_]*)\:(?P<value>[^\s:][^\s]*)$")


@dataclass(frozen=True, order=True)
class DependencyToken:
    kind: str
    value: str

    def __post_init__(self) -> None:
        if self.kind not in TOKEN_TYPES:
            raise DiasContractError("unknown dependency token kind")
        _required(self.value, "dependency token value")
        if any(character.isspace() for character in self.value):
            raise DiasContractError("dependency token values cannot contain whitespace")
        if self.kind == "CREDENTIAL_REF" and any(marker in self.value.upper() for marker in ("TOKEN=", "PASSWORD=", "SECRET=")):
            raise DiasContractError("credential tokens must be logical references, never values")

    @classmethod
    def parse(cls, raw: str) -> "DependencyToken":
        match = TOKEN_RE.fullmatch(raw)
        if match is None:
            raise DiasContractError("invalid dependency token")
        return cls(kind=match.group("kind"), value=match.group("value"))

    def render(self) -> str:
        return f"{self.kind}:{self.value}"


ASSURANCE_CLASSES = frozenset({"A0", "AA1", "AA2", "AA3", "CROSS_BOUNDARY_UNKNOWN"})


@dataclass(frozen=True)
class TestDependency:
    test_id: str
    assurance_class: str
    dependency_tokens: tuple[str, ...]
    reference_route_required: bool = False

    def __post_init__(self) -> None:
        _required(self.test_id, "test_id")
        if self.assurance_class not in ASSURANCE_CLASSES:
            raise DiasContractError("unknown assurance class")
        parsed = tuple(sorted({DependencyToken.parse(token).render() for token in self.dependency_tokens}))
        if not parsed:
            raise DiasContractError("test dependency cannot be empty")
        object.__setattr__(self, "dependency_tokens", parsed)


@dataclass(frozen=True)
class TestDependencyManifest:
    programme_id: str
    packet_id: str
    tests: tuple[TestDependency, ...]
    unresolved_behavior: str = "BLOCK"

    def __post_init__(self) -> None:
        _required(self.programme_id, "programme_id")
        _required(self.packet_id, "packet_id")
        if self.unresolved_behavior != "BLOCK":
            raise DiasContractError("unresolved test dependencies must block")
        if not self.tests:
            raise DiasContractError("test manifest cannot be empty")
        test_ids = [test.test_id for test in self.tests]
        if len(test_ids) != len(set(test_ids)):
            raise DiasContractError("test ids must be unique")
        object.__setattr__(self, "tests", tuple(sorted(self.tests, key=lambda test: test.test_id)))

    @property
    def manifest_id(self) -> str:
        return canonical_sha256(asdict(self), role="test-dependency-manifest/v1")


SOURCE_PRECEDENCE = {
    "OWNER_CURRENT_POINTER": 0,
    "OWNER_REFERENCED_STATE": 1,
    "OWNER_SIGNED_RECEIPT": 2,
    "DERIVED_OBSERVATION": 3,
}
SOURCE_ID_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


@dataclass(frozen=True)
class OwnerFactCandidate:
    owner: str
    fact_key: str
    value: Any
    source_class: str
    source_path: str
    source_blob: str
    observed_at: str | None = None

    def __post_init__(self) -> None:
        _required(self.owner, "owner")
        _required(self.fact_key, "fact_key")
        if self.source_class not in SOURCE_PRECEDENCE:
            raise DiasContractError("unknown owner source class")
        object.__setattr__(self, "source_path", normalize_relative_path(self.source_path))
        if not SOURCE_ID_RE.fullmatch(self.source_blob):
            raise DiasContractError("owner fact source_blob must be an exact Git blob or content SHA")

    @property
    def fact_id(self) -> str:
        return canonical_sha256(asdict(self), role="owner-fact-candidate/v1")


@dataclass(frozen=True)
class ResolvedOwnerFact:
    owner: str
    fact_key: str
    value: Any
    controlling_source_class: str
    controlling_source_paths: tuple[str, ...]
    controlling_source_blobs: tuple[str, ...]
    ignored_lower_precedence_fact_ids: tuple[str, ...]

    @property
    def resolved_fact_id(self) -> str:
        return canonical_sha256(asdict(self), role="resolved-owner-fact/v1")


def resolve_owner_fact(candidates: Sequence[OwnerFactCandidate]) -> ResolvedOwnerFact:
    if not candidates:
        raise OwnerFactUnresolved("owner fact has no candidates")
    owners = {candidate.owner for candidate in candidates}
    keys = {candidate.fact_key for candidate in candidates}
    if len(owners) != 1 or len(keys) != 1:
        raise DiasContractError("owner fact candidates must share owner and fact_key")
    controlling_rank = min(SOURCE_PRECEDENCE[candidate.source_class] for candidate in candidates)
    controlling = [candidate for candidate in candidates if SOURCE_PRECEDENCE[candidate.source_class] == controlling_rank]
    identities = {canonical_sha256(candidate.value) for candidate in controlling}
    if len(identities) != 1:
        raise OwnerFactConflict("equally authoritative owner facts conflict")
    controlling_sorted = sorted(controlling, key=lambda candidate: (candidate.source_path, candidate.source_blob))
    ignored = sorted(candidate.fact_id for candidate in candidates if candidate not in controlling)
    first = controlling_sorted[0]
    return ResolvedOwnerFact(
        owner=first.owner,
        fact_key=first.fact_key,
        value=first.value,
        controlling_source_class=first.source_class,
        controlling_source_paths=tuple(candidate.source_path for candidate in controlling_sorted),
        controlling_source_blobs=tuple(candidate.source_blob for candidate in controlling_sorted),
        ignored_lower_precedence_fact_ids=tuple(ignored),
    )


@dataclass(frozen=True)
class CurrentExecutionProjection:
    programme_id: str
    resolved_facts: tuple[ResolvedOwnerFact, ...]
    shadow_only: bool = True
    derivative: bool = True
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        _required(self.programme_id, "programme_id")
        if not self.shadow_only or not self.derivative or self.authority_effect != "NONE":
            raise DiasContractError("current execution projection must remain derivative shadow evidence")
        keys = [(fact.owner, fact.fact_key) for fact in self.resolved_facts]
        if len(keys) != len(set(keys)):
            raise DiasContractError("projection contains duplicate owner fact keys")
        object.__setattr__(self, "resolved_facts", tuple(sorted(self.resolved_facts, key=lambda fact: (fact.owner, fact.fact_key))))

    @property
    def projection_id(self) -> str:
        return canonical_sha256(asdict(self), role="current-execution-projection/v1")


def build_current_execution_projection(
    programme_id: str,
    candidates_by_fact: Mapping[str, Sequence[OwnerFactCandidate]],
) -> CurrentExecutionProjection:
    if not candidates_by_fact:
        raise OwnerFactUnresolved("projection requires owner facts")
    resolved = tuple(resolve_owner_fact(candidates) for _, candidates in sorted(candidates_by_fact.items()))
    return CurrentExecutionProjection(programme_id=programme_id, resolved_facts=resolved)


@dataclass(frozen=True)
class CanonicalIdentityGateRegistry:
    programme_id: str
    plan_id: str
    packet_ids: tuple[str, ...]
    gate_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _required(self.programme_id, "programme_id")
        _required(self.plan_id, "plan_id")
        packets = _unique(self.packet_ids, "packet_ids")
        gates = _unique(self.gate_ids, "gate_ids")
        if any(not packet.startswith("DIASI-WP") for packet in packets):
            raise DiasContractError("non-canonical DIASI packet identity")
        if any(not gate.startswith("DIASI-G") for gate in gates):
            raise DiasContractError("non-canonical DIASI gate identity")
        object.__setattr__(self, "packet_ids", packets)
        object.__setattr__(self, "gate_ids", gates)

    @property
    def registry_id(self) -> str:
        return canonical_sha256(asdict(self), role="canonical-identity-gate-registry/v1")

    def require_packet(self, packet_id: str) -> str:
        if packet_id not in self.packet_ids:
            raise DiasContractError("unknown packet identity")
        return packet_id

    def require_gate(self, gate_id: str) -> str:
        if gate_id not in self.gate_ids:
            raise DiasContractError("unknown gate identity")
        return gate_id
