from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


def canonical_id(value: Any) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return sha256(payload).hexdigest()


QUIESCENCE_MODES = {"RUN", "DRAIN", "HOLD", "DISABLE_NEW_DISPATCH"}
SIDE_EFFECT_CLASSES = {"REVERSIBLE_LOCAL", "BRANCH_ONLY", "READ_ONLY", "IRREVERSIBLE_OR_UNKNOWN"}
TRANSACTION_PHASES = {"INTENT_PERSISTED", "DISPATCH_UNKNOWN", "START_ACKNOWLEDGED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"}


@dataclass(frozen=True)
class ReconciliationSnapshot:
    physical_main: str
    physical_tree: str
    programme_states: tuple[Mapping[str, Any], ...]
    assurance_futures: tuple[Mapping[str, Any], ...] = ()
    vit_frontier: Mapping[str, Any] = field(default_factory=dict)
    source_hashes: Mapping[str, str] = field(default_factory=dict)

    @property
    def snapshot_id(self) -> str:
        return canonical_id(self)


@dataclass(frozen=True)
class RunnableWorkItem:
    programme_id: str
    packet_id: str
    action: str
    priority: int
    authority_class: str
    authority_delta: str
    prerequisites_pass: bool
    registered_root: bool
    executor_id: str | None
    side_effect_class: str = "IRREVERSIBLE_OR_UNKNOWN"
    predecessor_materialisation_required: bool = False
    consumed_frontier: str | None = None

    @property
    def work_id(self) -> str:
        return canonical_id(self)


@dataclass(frozen=True)
class RunnableWorkSet:
    snapshot_id: str
    items: tuple[RunnableWorkItem, ...]
    parked: tuple[Mapping[str, str], ...]
    fairness_source: str = "ORCH_CURRENT_POLICY"
    complete: bool = True

    @property
    def workset_id(self) -> str:
        return canonical_id(self)


@dataclass(frozen=True)
class ExecutorCapabilityRecord:
    executor_id: str
    repository_write: bool
    branch_ref_write: bool
    merge: bool
    force_push: bool
    irreversible_external_side_effects: bool
    supported_actions: tuple[str, ...]
    environment_id: str
    active: bool = True

    @property
    def capability_id(self) -> str:
        return canonical_id(self)

    @property
    def non_writing_fixture_only(self) -> bool:
        return not any((self.repository_write, self.branch_ref_write, self.merge, self.force_push, self.irreversible_external_side_effects))


@dataclass(frozen=True)
class SupervisorLease:
    scope: str
    holder_identity: str
    fencing_generation: int
    active: bool = True

    def __post_init__(self) -> None:
        if self.fencing_generation < 1:
            raise ValueError("fencing generation must be monotonic positive")

    @property
    def lease_id(self) -> str:
        return canonical_id(self)


@dataclass(frozen=True)
class DispatchIdentity:
    programme_id: str
    packet_id: str
    action: str
    work_id: str
    executor_id: str
    fencing_generation: int

    @property
    def dispatch_id(self) -> str:
        return canonical_id(self)


@dataclass(frozen=True)
class DispatchTransaction:
    dispatch_id: str
    phase: str
    fencing_generation: int
    worker_run_id: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.phase not in TRANSACTION_PHASES:
            raise ValueError("unknown dispatch transaction phase")


@dataclass(frozen=True)
class WorkerOwnership:
    dispatch_id: str
    worker_run_id: str
    executor_id: str
    fencing_generation: int
    heartbeat_sequence: int = 0
    authoritative: bool = True


@dataclass(frozen=True)
class QuiescenceControl:
    mode: str = "RUN"
    source: str = "OPERATOR_OR_PROGRAMME_OWNER"

    def __post_init__(self) -> None:
        if self.mode not in QUIESCENCE_MODES:
            raise ValueError("unknown quiescence mode")

    @property
    def blocks_new_dispatch(self) -> bool:
        return self.mode in {"HOLD", "DISABLE_NEW_DISPATCH"}


@dataclass(frozen=True)
class SupervisorCheckpoint:
    fencing_generation: int
    open_dispatch_ids: tuple[str, ...] = ()
    last_reconciliation_id: str | None = None
    event_watermarks: Mapping[str, int] = field(default_factory=dict)
    chat_dependency_count: int = 0

    def __post_init__(self) -> None:
        if self.chat_dependency_count != 0:
            raise ValueError("CERS checkpoint may not depend on chat state")
