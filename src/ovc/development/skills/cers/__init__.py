"""CERS inactive/shadow liveness substrate.

CERS coordinates durable liveness only. It does not own programme authority,
repository-main writes, or scientific semantics.
"""

from .model import (
    DispatchIdentity,
    DispatchTransaction,
    ExecutorCapabilityRecord,
    QuiescenceControl,
    ReconciliationSnapshot,
    RunnableWorkItem,
    RunnableWorkSet,
    SupervisorCheckpoint,
    SupervisorLease,
    WorkerOwnership,
)
from .persistent import (
    DENY_PRECEDENCE,
    PersistentAuthorityView,
    PersistentDispatchProposal,
    PersistentReconciliationResult,
    PersistentWorkRequest,
    derive_authority_view,
    reconcile_persistent_requests,
    route_failure_to_owner,
)
from .reconcile import ReferenceReconciler, ReconciliationResult
from .runtime import DispatchCoordinator, EventLedger, FixtureExecutor, LeaseManager

__all__ = [
    "DENY_PRECEDENCE",
    "DispatchCoordinator",
    "DispatchIdentity",
    "DispatchTransaction",
    "EventLedger",
    "ExecutorCapabilityRecord",
    "FixtureExecutor",
    "LeaseManager",
    "PersistentAuthorityView",
    "PersistentDispatchProposal",
    "PersistentReconciliationResult",
    "PersistentWorkRequest",
    "QuiescenceControl",
    "ReconciliationResult",
    "ReconciliationSnapshot",
    "ReferenceReconciler",
    "RunnableWorkItem",
    "RunnableWorkSet",
    "SupervisorCheckpoint",
    "SupervisorLease",
    "WorkerOwnership",
    "derive_authority_view",
    "reconcile_persistent_requests",
    "route_failure_to_owner",
]
