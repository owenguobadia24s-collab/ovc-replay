"""Durable, reconstructable DIASI integration transaction state machine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256, normalize_relative_path
from ovc.development.skills.dias import DiasContractError


TERMINAL_STATES = frozenset({"COMPLETED", "DEAD_LETTER", "QUARANTINED"})
TRANSITIONS = {
    ("READY", "ADMIT"): "ADMITTED",
    ("ADMITTED", "START_APPLY"): "APPLYING",
    ("APPLYING", "WRITE_CONFIRMED"): "MATERIALISED",
    ("APPLYING", "WRITE_OUTCOME_UNKNOWN"): "WRITE_UNKNOWN",
    ("WRITE_UNKNOWN", "RECONSTRUCT_WRITE"): "MATERIALISED",
    ("MATERIALISED", "START_RECEIPTS"): "RECEIPTS_PENDING",
    ("RECEIPTS_PENDING", "RECEIPTS_CONFIRMED"): "COMPLETED",
}


@dataclass(frozen=True)
class OwnerFactReference:
    owner: str
    fact_key: str
    fact_id: str
    source_path: str
    source_identity: str

    def __post_init__(self) -> None:
        if not self.owner or not self.fact_key or len(self.fact_id) != 64:
            raise DiasContractError("invalid owner fact reference")
        object.__setattr__(self, "source_path", normalize_relative_path(self.source_path))
        if len(self.source_identity) not in {40, 64}:
            raise DiasContractError("owner source identity must be Git or content-addressed")


@dataclass(frozen=True)
class OwnerFactReferenceManifest:
    transaction_key: str
    facts: tuple[OwnerFactReference, ...]
    unresolved_behavior: str = "BLOCK"

    def __post_init__(self) -> None:
        if len(self.transaction_key) != 64 or not self.facts:
            raise DiasContractError("owner fact manifest is incomplete")
        if self.unresolved_behavior != "BLOCK":
            raise DiasContractError("unresolved owner facts must block")
        keys = [(fact.owner, fact.fact_key) for fact in self.facts]
        if len(keys) != len(set(keys)):
            raise DiasContractError("duplicate owner fact reference")
        object.__setattr__(self, "facts", tuple(sorted(self.facts, key=lambda fact: (fact.owner, fact.fact_key))))

    @property
    def manifest_id(self) -> str:
        return canonical_sha256(asdict(self), role="owner-fact-reference-manifest/v1")


@dataclass(frozen=True)
class TransactionStateCoverage:
    state: str
    terminal: bool
    durable_triggers: tuple[str, ...]
    reconciliation_route: str | None
    maximum_age_seconds: int | None
    dead_letter_disposition: str | None

    def __post_init__(self) -> None:
        if not self.state:
            raise DiasContractError("transaction state is required")
        if self.terminal != (self.state in TERMINAL_STATES):
            raise DiasContractError("terminal state declaration mismatch")
        if not self.terminal:
            if not self.durable_triggers or not self.reconciliation_route:
                raise DiasContractError("nonterminal state lacks durable liveness coverage")
            if not self.maximum_age_seconds or self.maximum_age_seconds <= 0:
                raise DiasContractError("nonterminal state lacks maximum age")
            if not self.dead_letter_disposition:
                raise DiasContractError("nonterminal state lacks dead-letter disposition")


@dataclass(frozen=True)
class IntegrationTriggerCoverageManifest:
    states: tuple[TransactionStateCoverage, ...]

    def __post_init__(self) -> None:
        if not self.states:
            raise DiasContractError("trigger coverage is empty")
        names = [state.state for state in self.states]
        if len(names) != len(set(names)):
            raise DiasContractError("duplicate transaction state coverage")
        required = set(TERMINAL_STATES) | {source for source, _ in TRANSITIONS} | set(TRANSITIONS.values())
        missing = required - set(names)
        if missing:
            raise DiasContractError(f"transaction trigger coverage incomplete: {sorted(missing)}")
        object.__setattr__(self, "states", tuple(sorted(self.states, key=lambda state: state.state)))

    @property
    def manifest_id(self) -> str:
        return canonical_sha256(asdict(self), role="integration-trigger-coverage-manifest/v1")


@dataclass(frozen=True)
class RouteFence:
    writer_id: str
    generation: int
    fence_token: str

    def __post_init__(self) -> None:
        if not self.writer_id or self.generation < 1 or len(self.fence_token) != 64:
            raise DiasContractError("invalid route fence")

    def accepts(self, *, writer_id: str, generation: int, fence_token: str) -> bool:
        return writer_id == self.writer_id and generation == self.generation and fence_token == self.fence_token


@dataclass(frozen=True)
class EventCursor:
    stream_id: str
    sequence: int = 0
    event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.stream_id or self.sequence < 0 or self.sequence != len(self.event_ids):
            raise DiasContractError("invalid event cursor")
        if len(self.event_ids) != len(set(self.event_ids)):
            raise DiasContractError("event cursor contains duplicates")

    def append(self, event_id: str) -> "EventCursor":
        if not event_id:
            raise DiasContractError("event id is required")
        if event_id in self.event_ids:
            return self
        return EventCursor(self.stream_id, self.sequence + 1, (*self.event_ids, event_id))


@dataclass(frozen=True)
class RecoveryEntry:
    attempt: int
    reason: str
    from_state: str
    disposition: str


@dataclass(frozen=True)
class IntegrationTransaction:
    programme_id: str
    packet_id: str
    pip_id: str
    owner_fact_manifest_id: str
    trigger_coverage_manifest_id: str
    route_fence: RouteFence
    state: str
    event_cursor: EventCursor
    idempotence_key: str
    recovery_budget: int
    recovery_history: tuple[RecoveryEntry, ...] = ()
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("pip_id", "owner_fact_manifest_id", "trigger_coverage_manifest_id", "idempotence_key"):
            if len(getattr(self, field)) != 64:
                raise DiasContractError(f"{field} must be SHA-256")
        if self.state not in ({source for source, _ in TRANSITIONS} | set(TRANSITIONS.values()) | TERMINAL_STATES):
            raise DiasContractError("unknown transaction state")
        if self.recovery_budget < 0 or len(self.recovery_history) > self.recovery_budget:
            raise DiasContractError("recovery budget invalid or exceeded")
        if self.authority_effect != "NONE":
            raise DiasContractError("transaction cannot create authority")

    @property
    def transaction_key(self) -> str:
        return canonical_sha256(
            {
                "programme_id": self.programme_id,
                "packet_id": self.packet_id,
                "pip_id": self.pip_id,
                "owner_fact_manifest_id": self.owner_fact_manifest_id,
                "route_fence": asdict(self.route_fence),
                "idempotence_key": self.idempotence_key,
            },
            role="integration-transaction-key/v1",
        )

    @property
    def state_id(self) -> str:
        return canonical_sha256(asdict(self), role="integration-transaction-state/v1")

    def apply_event(
        self,
        *,
        event_id: str,
        event_type: str,
        writer_id: str,
        generation: int,
        fence_token: str,
    ) -> "IntegrationTransaction":
        if event_id in self.event_cursor.event_ids:
            return self
        if not self.route_fence.accepts(writer_id=writer_id, generation=generation, fence_token=fence_token):
            return replace(self, state="QUARANTINED", event_cursor=self.event_cursor.append(event_id))
        target = TRANSITIONS.get((self.state, event_type))
        if target is None:
            return self._record_recovery(event_id=event_id, reason=f"INVALID_TRANSITION:{self.state}:{event_type}")
        return replace(self, state=target, event_cursor=self.event_cursor.append(event_id))

    def _record_recovery(self, *, event_id: str, reason: str) -> "IntegrationTransaction":
        attempt = len(self.recovery_history) + 1
        disposition = "RECONCILE" if attempt <= self.recovery_budget else "DEAD_LETTER"
        history = (*self.recovery_history, RecoveryEntry(attempt, reason, self.state, disposition))
        if attempt > self.recovery_budget:
            # The over-budget attempt is represented by the terminal transition but
            # not stored beyond the bounded history capacity.
            return replace(self, state="DEAD_LETTER", event_cursor=self.event_cursor.append(event_id))
        return replace(self, recovery_history=history, event_cursor=self.event_cursor.append(event_id))


def reconstruct_transaction(payload: Mapping[str, Any]) -> IntegrationTransaction:
    """Rebuild using only durable decoded content; no cache/chat/service state."""
    try:
        fence = RouteFence(**payload["route_fence"])
        cursor = EventCursor(
            stream_id=payload["event_cursor"]["stream_id"],
            sequence=payload["event_cursor"]["sequence"],
            event_ids=tuple(payload["event_cursor"]["event_ids"]),
        )
        history = tuple(RecoveryEntry(**entry) for entry in payload.get("recovery_history", ()))
        return IntegrationTransaction(
            programme_id=payload["programme_id"],
            packet_id=payload["packet_id"],
            pip_id=payload["pip_id"],
            owner_fact_manifest_id=payload["owner_fact_manifest_id"],
            trigger_coverage_manifest_id=payload["trigger_coverage_manifest_id"],
            route_fence=fence,
            state=payload["state"],
            event_cursor=cursor,
            idempotence_key=payload["idempotence_key"],
            recovery_budget=payload["recovery_budget"],
            recovery_history=history,
            authority_effect=payload.get("authority_effect", "NONE"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DiasContractError("invalid durable transaction payload") from exc
