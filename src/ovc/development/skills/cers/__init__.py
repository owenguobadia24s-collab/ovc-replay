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
from .persistent_service import (
    DurableSupervisorState,
    PersistentSupervisorService,
    PersistentTimingPolicy,
)
from .admission import canonical_record_sha256, validate_inactive_admission_registry
from .reconcile import ReferenceReconciler, ReconciliationResult
from .runtime import DispatchCoordinator, EventLedger, FixtureExecutor, LeaseManager

__all__ = [
    "DENY_PRECEDENCE",
    "DispatchCoordinator",
    "DispatchIdentity",
    "DispatchTransaction",
    "DurableSupervisorState",
    "EventLedger",
    "ExecutorCapabilityRecord",
    "FixtureExecutor",
    "LeaseManager",
    "PersistentAuthorityView",
    "PersistentDispatchProposal",
    "PersistentReconciliationResult",
    "PersistentSupervisorService",
    "canonical_record_sha256",
    "validate_inactive_admission_registry",
    "PersistentTimingPolicy",
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
