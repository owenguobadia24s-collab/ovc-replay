from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Mapping

from .model import (
    DispatchIdentity,
    DispatchTransaction,
    ExecutorCapabilityRecord,
    QuiescenceControl,
    SupervisorLease,
    WorkerOwnership,
)


class LeaseManager:
    def __init__(self) -> None:
        self._epochs: dict[str, int] = {}
        self._leases: dict[str, SupervisorLease] = {}

    def acquire(self, scope: str, holder_identity: str) -> SupervisorLease:
        epoch = self._epochs.get(scope, 0) + 1
        self._epochs[scope] = epoch
        lease = SupervisorLease(scope=scope, holder_identity=holder_identity, fencing_generation=epoch)
        self._leases[scope] = lease
        return lease

    def validate(self, lease: SupervisorLease) -> bool:
        current = self._leases.get(lease.scope)
        return bool(current and current.active and current.lease_id == lease.lease_id and current.fencing_generation == self._epochs.get(lease.scope))

    def release(self, lease: SupervisorLease) -> None:
        if self.validate(lease):
            self._leases[lease.scope] = replace(lease, active=False)


class EventLedger:
    """At-least-once event ingestion with deterministic source-sequence convergence."""

    def __init__(self) -> None:
        self._events: dict[tuple[str, int], Mapping[str, object]] = {}

    def ingest(self, *, source: str, source_sequence: int, event: Mapping[str, object]) -> bool:
        key = (source, source_sequence)
        previous = self._events.get(key)
        if previous is not None:
            if dict(previous) != dict(event):
                raise ValueError("EVENT_IDENTITY_CONFLICT")
            return False
        self._events[key] = dict(event)
        return True

    def ordered(self) -> tuple[Mapping[str, object], ...]:
        return tuple(self._events[key] for key in sorted(self._events))


class FixtureExecutor:
    """Non-writing executor used only for pre-activation qualification."""

    def __init__(self, executor_id: str = "CERS_FIXTURE_EXECUTOR_V0_1") -> None:
        self.capability = ExecutorCapabilityRecord(
            executor_id=executor_id,
            repository_write=False,
            branch_ref_write=False,
            merge=False,
            force_push=False,
            irreversible_external_side_effects=False,
            supported_actions=("BUILD_FIXTURE_SUCCESSOR", "RECONCILE_FIXTURE", "RUN_FIXTURE_TEST"),
            environment_id="CERS_SYNTHETIC_NON_WRITING_V0_1",
        )
        self.starts: dict[str, WorkerOwnership] = {}
        self.outcomes: dict[str, DispatchTransaction] = {}

    def start(self, identity: DispatchIdentity, lease: SupervisorLease, quiescence: QuiescenceControl) -> WorkerOwnership:
        if quiescence.blocks_new_dispatch:
            raise PermissionError("QUIESCENCE_BLOCKS_NEW_DISPATCH")
        if identity.executor_id != self.capability.executor_id:
            raise PermissionError("EXECUTOR_IDENTITY_MISMATCH")
        if identity.fencing_generation != lease.fencing_generation:
            raise PermissionError("STALE_FENCE")
        existing = self.starts.get(identity.dispatch_id)
        if existing is not None:
            return existing
        worker = WorkerOwnership(
            dispatch_id=identity.dispatch_id,
            worker_run_id=f"fixture-{identity.dispatch_id[:16]}",
            executor_id=self.capability.executor_id,
            fencing_generation=lease.fencing_generation,
            heartbeat_sequence=1,
        )
        self.starts[identity.dispatch_id] = worker
        self.outcomes[identity.dispatch_id] = DispatchTransaction(identity.dispatch_id, "START_ACKNOWLEDGED", lease.fencing_generation, worker.worker_run_id)
        return worker

    def heartbeat(self, dispatch_id: str, fencing_generation: int) -> WorkerOwnership:
        worker = self.starts[dispatch_id]
        if worker.fencing_generation != fencing_generation:
            raise PermissionError("STALE_FENCE")
        worker = replace(worker, heartbeat_sequence=worker.heartbeat_sequence + 1)
        self.starts[dispatch_id] = worker
        return worker

    def complete(self, dispatch_id: str, fencing_generation: int, *, success: bool = True) -> DispatchTransaction:
        worker = self.starts[dispatch_id]
        if worker.fencing_generation != fencing_generation or not worker.authoritative:
            raise PermissionError("STALE_WORKER_COMPLETION")
        result = DispatchTransaction(dispatch_id, "COMPLETED" if success else "FAILED", fencing_generation, worker.worker_run_id)
        self.outcomes[dispatch_id] = result
        return result


class DispatchCoordinator:
    """Idempotent fixture dispatch transaction coordinator.

    The coordinator cannot make a writing executor lawful. Pre-activation it accepts
    only ExecutorCapabilityRecord.non_writing_fixture_only executors.
    """

    def __init__(self, lease_manager: LeaseManager, executor: FixtureExecutor) -> None:
        self.lease_manager = lease_manager
        self.executor = executor
        self.transactions: dict[str, DispatchTransaction] = {}

    def dispatch(self, identity: DispatchIdentity, lease: SupervisorLease, quiescence: QuiescenceControl) -> DispatchTransaction:
        if not self.lease_manager.validate(lease):
            raise PermissionError("STALE_FENCE")
        if not self.executor.capability.non_writing_fixture_only:
            raise PermissionError("LIVE_WRITE_CAPABILITY_NOT_AUTHORISED")
        existing = self.transactions.get(identity.dispatch_id)
        if existing and existing.phase in {"START_ACKNOWLEDGED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"}:
            return existing
        self.transactions[identity.dispatch_id] = DispatchTransaction(identity.dispatch_id, "INTENT_PERSISTED", lease.fencing_generation)
        worker = self.executor.start(identity, lease, quiescence)
        transaction = DispatchTransaction(identity.dispatch_id, "START_ACKNOWLEDGED", lease.fencing_generation, worker.worker_run_id)
        self.transactions[identity.dispatch_id] = transaction
        return transaction

    def mark_unknown_start(self, identity: DispatchIdentity, lease: SupervisorLease) -> DispatchTransaction:
        if not self.lease_manager.validate(lease):
            raise PermissionError("STALE_FENCE")
        transaction = DispatchTransaction(identity.dispatch_id, "DISPATCH_UNKNOWN", lease.fencing_generation, reason="UNKNOWN_START_STATE")
        self.transactions[identity.dispatch_id] = transaction
        return transaction

    def reconcile_unknown(self, dispatch_id: str) -> DispatchTransaction:
        current = self.transactions[dispatch_id]
        if current.phase != "DISPATCH_UNKNOWN":
            return current
        observed = self.executor.outcomes.get(dispatch_id)
        if observed is None:
            return current
        self.transactions[dispatch_id] = observed
        return observed


def selective_invalidation(*, changed_dependency: str, descendants: Iterable[Mapping[str, object]]) -> tuple[str, ...]:
    invalidated: list[str] = []
    for row in descendants:
        dependencies = set(map(str, row.get("dependencies", ())))
        if changed_dependency in dependencies:
            invalidated.append(str(row["packet_id"]))
    return tuple(sorted(invalidated))


def failure_route(programme_id: str, packet_id: str) -> Mapping[str, str]:
    return {"programme_id": programme_id, "packet_id": packet_id, "route": "EXISTING_PROGRAMME_REPAIR_OWNER", "cers_remediation_authority": "NONE"}
