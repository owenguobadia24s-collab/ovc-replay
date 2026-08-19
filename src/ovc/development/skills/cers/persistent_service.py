from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping

from .model import SupervisorCheckpoint, SupervisorLease
from .persistent import PersistentDispatchProposal


SERVICE_MODES = {"RUN", "DRAIN", "HOLD", "DISABLE_NEW_DISPATCH"}
TERMINAL_PHASES = {"COMPLETED", "FAILED", "CANCELLED"}
KNOWN_PHASES = {"INTENT_PERSISTED", "DISPATCH_UNKNOWN", "START_ACKNOWLEDGED", "RUNNING", *TERMINAL_PHASES}


def _content_id(value: Any) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


@dataclass(frozen=True)
class PersistentTimingPolicy:
    """Activation-time timing values are measured in WP5, never invented here."""

    status: str = "MEASURE_BEFORE_ACTIVATION"
    sweep_cadence_seconds: int | None = None
    heartbeat_cadence_seconds: int | None = None
    liveness_threshold_seconds: int | None = None
    reclaim_after_seconds: int | None = None
    provider_backoff_seconds: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"MEASURE_BEFORE_ACTIVATION", "FROZEN_QUALIFIED"}:
            raise ValueError("UNKNOWN_TIMING_POLICY_STATUS")
        if self.status == "FROZEN_QUALIFIED":
            values = (
                self.sweep_cadence_seconds,
                self.heartbeat_cadence_seconds,
                self.liveness_threshold_seconds,
                self.reclaim_after_seconds,
            )
            if any(value is None or value <= 0 for value in values):
                raise ValueError("FROZEN_TIMING_POLICY_REQUIRES_POSITIVE_MEASURED_VALUES")
            if not self.provider_backoff_seconds or any(value < 0 for value in self.provider_backoff_seconds):
                raise ValueError("FROZEN_TIMING_POLICY_REQUIRES_BOUNDED_BACKOFF")

    @property
    def activation_ready(self) -> bool:
        return self.status == "FROZEN_QUALIFIED"


@dataclass
class DurableSupervisorState:
    supervisor_scope: str
    fencing_generation: int = 0
    lease_holder: str | None = None
    lease_active: bool = False
    quiescence_mode: str = "DISABLE_NEW_DISPATCH"
    event_watermarks: dict[str, int] = field(default_factory=dict)
    event_identities: dict[str, str] = field(default_factory=dict)
    sweep_identities: list[str] = field(default_factory=list)
    transactions: dict[str, dict[str, Any]] = field(default_factory=dict)
    ownership: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_reconciliation_id: str | None = None
    provider_attempts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.quiescence_mode not in SERVICE_MODES:
            raise ValueError("UNKNOWN_QUIESCENCE_MODE")
        if self.fencing_generation < 0:
            raise ValueError("INVALID_FENCING_GENERATION")

    @property
    def state_id(self) -> str:
        return _content_id(self.to_payload())

    def to_payload(self) -> dict[str, Any]:
        return {
            "supervisor_scope": self.supervisor_scope,
            "fencing_generation": self.fencing_generation,
            "lease_holder": self.lease_holder,
            "lease_active": self.lease_active,
            "quiescence_mode": self.quiescence_mode,
            "event_watermarks": dict(sorted(self.event_watermarks.items())),
            "event_identities": dict(sorted(self.event_identities.items())),
            "sweep_identities": list(self.sweep_identities),
            "transactions": {key: dict(self.transactions[key]) for key in sorted(self.transactions)},
            "ownership": {key: dict(self.ownership[key]) for key in sorted(self.ownership)},
            "last_reconciliation_id": self.last_reconciliation_id,
            "provider_attempts": dict(sorted(self.provider_attempts.items())),
            "chat_dependency_count": 0,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DurableSupervisorState":
        if int(payload.get("chat_dependency_count", 0)) != 0:
            raise ValueError("CHAT_STATE_DEPENDENCY_FORBIDDEN")
        return cls(
            supervisor_scope=str(payload["supervisor_scope"]),
            fencing_generation=int(payload.get("fencing_generation", 0)),
            lease_holder=payload.get("lease_holder"),
            lease_active=bool(payload.get("lease_active", False)),
            quiescence_mode=str(payload.get("quiescence_mode", "DISABLE_NEW_DISPATCH")),
            event_watermarks={str(k): int(v) for k, v in dict(payload.get("event_watermarks", {})).items()},
            event_identities={str(k): str(v) for k, v in dict(payload.get("event_identities", {})).items()},
            sweep_identities=[str(value) for value in payload.get("sweep_identities", ())],
            transactions={str(k): dict(v) for k, v in dict(payload.get("transactions", {})).items()},
            ownership={str(k): dict(v) for k, v in dict(payload.get("ownership", {})).items()},
            last_reconciliation_id=payload.get("last_reconciliation_id"),
            provider_attempts={str(k): int(v) for k, v in dict(payload.get("provider_attempts", {})).items()},
        )


class PersistentSupervisorService:
    """Inactive/shadow durable supervisor mechanics.

    This class owns liveness state only.  It consumes an already-authorised
    dispatch proposal and cannot create programme, executor, merge, main-write,
    scientific or execution authority.
    """

    def __init__(
        self,
        state: DurableSupervisorState,
        *,
        timing_policy: PersistentTimingPolicy | None = None,
    ) -> None:
        self.state = state
        self.timing_policy = timing_policy or PersistentTimingPolicy()

    @classmethod
    def zero_chat_restart(
        cls,
        payload: Mapping[str, Any],
        *,
        timing_policy: PersistentTimingPolicy | None = None,
    ) -> "PersistentSupervisorService":
        return cls(DurableSupervisorState.from_payload(payload), timing_policy=timing_policy)

    def acquire_lease(self, holder_identity: str) -> SupervisorLease:
        if self.state.lease_active:
            raise RuntimeError("SUPERVISOR_LEASE_ALREADY_HELD")
        self.state.fencing_generation += 1
        self.state.lease_holder = holder_identity
        self.state.lease_active = True
        return SupervisorLease(
            scope=self.state.supervisor_scope,
            holder_identity=holder_identity,
            fencing_generation=self.state.fencing_generation,
        )

    def reclaim_lease(self, holder_identity: str, *, liveness_expired: bool) -> SupervisorLease:
        if self.state.lease_active and not liveness_expired:
            raise RuntimeError("RECLAIM_REQUIRES_QUALIFIED_LIVENESS_EXPIRY")
        self.state.lease_active = False
        self.state.lease_holder = None
        return self.acquire_lease(holder_identity)

    def validate_lease(self, lease: SupervisorLease) -> bool:
        return bool(
            self.state.lease_active
            and lease.active
            and lease.scope == self.state.supervisor_scope
            and lease.holder_identity == self.state.lease_holder
            and lease.fencing_generation == self.state.fencing_generation
        )

    def release_lease(self, lease: SupervisorLease) -> None:
        self._require_lease(lease)
        self.state.lease_active = False
        self.state.lease_holder = None

    def set_quiescence(self, mode: str) -> None:
        if mode not in SERVICE_MODES:
            raise ValueError("UNKNOWN_QUIESCENCE_MODE")
        self.state.quiescence_mode = mode

    @property
    def accepts_new_dispatch(self) -> bool:
        return self.state.quiescence_mode == "RUN"

    def ingest_event(self, *, source: str, source_sequence: int, event: Mapping[str, Any]) -> bool:
        if source_sequence < 0:
            raise ValueError("EVENT_SEQUENCE_MUST_BE_NONNEGATIVE")
        key = f"{source}:{source_sequence}"
        identity = _content_id({"source": source, "source_sequence": source_sequence, "event": dict(event)})
        existing = self.state.event_identities.get(key)
        if existing is not None:
            if existing != identity:
                raise ValueError("EVENT_IDENTITY_CONFLICT")
            return False
        watermark = self.state.event_watermarks.get(source, -1)
        if source_sequence < watermark:
            raise ValueError("EVENT_SEQUENCE_BEHIND_DURABLE_WATERMARK")
        self.state.event_identities[key] = identity
        self.state.event_watermarks[source] = max(watermark, source_sequence)
        return True

    def reference_sweep(self, reconciliation_id: str, lease: SupervisorLease) -> bool:
        self._require_lease(lease)
        if reconciliation_id in self.state.sweep_identities:
            return False
        self.state.sweep_identities.append(reconciliation_id)
        self.state.last_reconciliation_id = reconciliation_id
        return True

    def persist_dispatch_intent(self, proposal: PersistentDispatchProposal, lease: SupervisorLease) -> Mapping[str, Any]:
        self._require_lease(lease)
        if not self.accepts_new_dispatch:
            raise PermissionError(f"QUIESCENCE_{self.state.quiescence_mode}_BLOCKS_NEW_DISPATCH")
        if proposal.fencing_generation != lease.fencing_generation:
            raise PermissionError("STALE_FENCE")
        existing = self.state.transactions.get(proposal.dispatch_id)
        if existing is not None:
            if existing["phase"] == "DISPATCH_UNKNOWN":
                raise RuntimeError("UNKNOWN_START_MUST_RECONCILE_BEFORE_REDISPATCH")
            return dict(existing)
        transaction = {
            "dispatch_id": proposal.dispatch_id,
            "phase": "INTENT_PERSISTED",
            "fencing_generation": lease.fencing_generation,
            "worker_run_id": None,
            "reason": None,
        }
        self.state.transactions[proposal.dispatch_id] = transaction
        return dict(transaction)

    def mark_unknown_start(self, dispatch_id: str, lease: SupervisorLease, *, reason: str = "UNKNOWN_START_STATE") -> Mapping[str, Any]:
        self._require_lease(lease)
        current = self._transaction(dispatch_id)
        if current["phase"] in TERMINAL_PHASES:
            return dict(current)
        current.update({"phase": "DISPATCH_UNKNOWN", "reason": reason})
        return dict(current)

    def acknowledge_start(self, dispatch_id: str, worker_run_id: str, lease: SupervisorLease) -> Mapping[str, Any]:
        self._require_lease(lease)
        current = self._transaction(dispatch_id)
        if current["fencing_generation"] != lease.fencing_generation:
            raise PermissionError("STALE_FENCE")
        owner = self.state.ownership.get(dispatch_id)
        if owner is not None and owner.get("authoritative", True):
            if owner["worker_run_id"] != worker_run_id:
                raise RuntimeError("DUPLICATE_AUTHORITATIVE_START")
            return dict(current)
        self.state.ownership[dispatch_id] = {
            "dispatch_id": dispatch_id,
            "worker_run_id": worker_run_id,
            "fencing_generation": lease.fencing_generation,
            "heartbeat_sequence": 0,
            "authoritative": True,
        }
        current.update({"phase": "START_ACKNOWLEDGED", "worker_run_id": worker_run_id, "reason": None})
        return dict(current)

    def mark_running(self, dispatch_id: str, lease: SupervisorLease) -> Mapping[str, Any]:
        self._require_lease(lease)
        current = self._transaction(dispatch_id)
        if current["phase"] == "RUNNING":
            return dict(current)
        if current["phase"] != "START_ACKNOWLEDGED":
            raise RuntimeError("RUNNING_REQUIRES_START_ACKNOWLEDGED")
        current["phase"] = "RUNNING"
        return dict(current)

    def heartbeat(self, dispatch_id: str, worker_run_id: str, lease: SupervisorLease) -> Mapping[str, Any]:
        self._require_lease(lease)
        owner = self._authoritative_owner(dispatch_id)
        if owner["worker_run_id"] != worker_run_id or owner["fencing_generation"] != lease.fencing_generation:
            raise PermissionError("STALE_OR_NONAUTHORITATIVE_HEARTBEAT")
        owner["heartbeat_sequence"] = int(owner.get("heartbeat_sequence", 0)) + 1
        return dict(owner)

    def mark_worker_lost(self, dispatch_id: str, worker_run_id: str, lease: SupervisorLease) -> Mapping[str, Any]:
        self._require_lease(lease)
        owner = self._authoritative_owner(dispatch_id)
        if owner["worker_run_id"] != worker_run_id:
            raise PermissionError("WORKER_OWNERSHIP_MISMATCH")
        owner["authoritative"] = False
        current = self._transaction(dispatch_id)
        current.update({"phase": "DISPATCH_UNKNOWN", "reason": "WORKER_LOST_RECONCILE_REQUIRED"})
        return dict(current)

    def reconcile_unknown(
        self,
        dispatch_id: str,
        lease: SupervisorLease,
        *,
        observed_phase: str,
        observed_worker_run_id: str | None = None,
    ) -> Mapping[str, Any]:
        self._require_lease(lease)
        current = self._transaction(dispatch_id)
        if current["phase"] != "DISPATCH_UNKNOWN":
            return dict(current)
        if observed_phase == "NO_START":
            current.update({"phase": "INTENT_PERSISTED", "worker_run_id": None, "reason": "RECONCILED_NO_AUTHORITATIVE_START"})
            return dict(current)
        if observed_phase not in KNOWN_PHASES - {"INTENT_PERSISTED", "DISPATCH_UNKNOWN"}:
            raise ValueError("UNKNOWN_OBSERVED_PHASE")
        if observed_phase in {"START_ACKNOWLEDGED", "RUNNING"}:
            if not observed_worker_run_id:
                raise ValueError("OBSERVED_ACTIVE_START_REQUIRES_WORKER_ID")
            owner = self.state.ownership.get(dispatch_id)
            if owner is not None and owner.get("authoritative", True) and owner["worker_run_id"] != observed_worker_run_id:
                raise RuntimeError("DUPLICATE_AUTHORITATIVE_START")
            self.state.ownership[dispatch_id] = {
                "dispatch_id": dispatch_id,
                "worker_run_id": observed_worker_run_id,
                "fencing_generation": lease.fencing_generation,
                "heartbeat_sequence": int((owner or {}).get("heartbeat_sequence", 0)),
                "authoritative": True,
            }
        current.update({
            "phase": observed_phase,
            "worker_run_id": observed_worker_run_id or current.get("worker_run_id"),
            "reason": "UNKNOWN_START_RECONCILED",
        })
        return dict(current)

    def complete(self, dispatch_id: str, worker_run_id: str, lease: SupervisorLease, *, success: bool = True) -> Mapping[str, Any]:
        self._require_lease(lease)
        owner = self._authoritative_owner(dispatch_id)
        if owner["worker_run_id"] != worker_run_id or owner["fencing_generation"] != lease.fencing_generation:
            raise PermissionError("STALE_WORKER_COMPLETION")
        current = self._transaction(dispatch_id)
        current.update({"phase": "COMPLETED" if success else "FAILED", "worker_run_id": worker_run_id, "reason": None})
        return dict(current)

    def checkpoint(self) -> SupervisorCheckpoint:
        open_ids = tuple(
            sorted(
                dispatch_id
                for dispatch_id, transaction in self.state.transactions.items()
                if transaction["phase"] not in TERMINAL_PHASES
            )
        )
        return SupervisorCheckpoint(
            fencing_generation=max(1, self.state.fencing_generation),
            open_dispatch_ids=open_ids,
            last_reconciliation_id=self.state.last_reconciliation_id,
            event_watermarks=dict(self.state.event_watermarks),
            chat_dependency_count=0,
        )

    def backoff_for_attempt(self, provider: str, attempt: int) -> int:
        if not self.timing_policy.activation_ready:
            raise RuntimeError("TIMING_POLICY_NOT_FROZEN")
        schedule = self.timing_policy.provider_backoff_seconds
        if attempt < 0:
            raise ValueError("BACKOFF_ATTEMPT_MUST_BE_NONNEGATIVE")
        index = min(attempt, len(schedule) - 1)
        self.state.provider_attempts[provider] = attempt
        return schedule[index]

    def _require_lease(self, lease: SupervisorLease) -> None:
        if not self.validate_lease(lease):
            raise PermissionError("STALE_FENCE")

    def _transaction(self, dispatch_id: str) -> dict[str, Any]:
        if dispatch_id not in self.state.transactions:
            raise KeyError("DISPATCH_INTENT_NOT_PERSISTED")
        return self.state.transactions[dispatch_id]

    def _authoritative_owner(self, dispatch_id: str) -> dict[str, Any]:
        owner = self.state.ownership.get(dispatch_id)
        if owner is None or not owner.get("authoritative", True):
            raise PermissionError("NO_AUTHORITATIVE_WORKER_OWNERSHIP")
        return owner
