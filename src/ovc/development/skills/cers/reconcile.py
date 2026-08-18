from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .model import (
    DispatchIdentity,
    ExecutorCapabilityRecord,
    QuiescenceControl,
    ReconciliationSnapshot,
    RunnableWorkItem,
    RunnableWorkSet,
)


@dataclass(frozen=True)
class ReconciliationResult:
    snapshot: ReconciliationSnapshot
    workset: RunnableWorkSet
    proposed_dispatches: tuple[DispatchIdentity, ...]


class ReferenceReconciler:
    """Side-effect-free CERS reference oracle.

    It never dispatches.  It only turns exact durable observations into a
    deterministic ordered runnable/parked set and proposed dispatch identities.
    """

    def reconcile(
        self,
        *,
        snapshot: ReconciliationSnapshot,
        work_items: Iterable[RunnableWorkItem],
        executors: Mapping[str, ExecutorCapabilityRecord],
        quiescence: QuiescenceControl,
        fencing_generation: int,
    ) -> ReconciliationResult:
        parked: list[Mapping[str, str]] = []
        runnable: list[RunnableWorkItem] = []
        proposed: list[DispatchIdentity] = []

        for item in sorted(
            tuple(work_items),
            key=lambda row: (row.priority, row.programme_id, row.packet_id, row.action, row.work_id),
        ):
            reason = self._park_reason(item, executors, quiescence)
            if reason is not None:
                parked.append({"work_id": item.work_id, "programme_id": item.programme_id, "packet_id": item.packet_id, "reason": reason})
                continue
            runnable.append(item)
            executor = executors[item.executor_id or ""]
            proposed.append(
                DispatchIdentity(
                    programme_id=item.programme_id,
                    packet_id=item.packet_id,
                    action=item.action,
                    work_id=item.work_id,
                    executor_id=executor.executor_id,
                    fencing_generation=fencing_generation,
                )
            )

        workset = RunnableWorkSet(
            snapshot_id=snapshot.snapshot_id,
            items=tuple(runnable),
            parked=tuple(parked),
            fairness_source="ORCH_CURRENT_POLICY",
            complete=True,
        )
        return ReconciliationResult(snapshot=snapshot, workset=workset, proposed_dispatches=tuple(proposed))

    @staticmethod
    def _park_reason(
        item: RunnableWorkItem,
        executors: Mapping[str, ExecutorCapabilityRecord],
        quiescence: QuiescenceControl,
    ) -> str | None:
        if quiescence.blocks_new_dispatch:
            return f"QUIESCENCE_{quiescence.mode}"
        if not item.registered_root:
            return "UNREGISTERED_PROGRAMME_ROOT"
        if item.authority_class not in {"AUTO_EXECUTABLE", "AUTO_RATIFIABLE"}:
            return "AUTHORITY_NOT_AUTO_EXECUTABLE"
        if item.authority_delta not in {"NONE", "INACTIVE_CONTRACTS_SCHEMAS_REGISTRIES", "READ_ONLY_DETERMINISTIC_RECONCILER", "INACTIVE_FENCING_RECOVERY_WAKE_RECONCILIATION", "FIXTURE_ONLY_NON_WRITING_EXECUTOR_SHADOW", "SHADOW_QUALIFICATION_DEVOBS_GATE_PREPARATION"}:
            return "AUTHORITY_DELTA_NOT_PREACTIVATION_ALLOWED"
        if not item.prerequisites_pass:
            return "PREREQUISITE_UNSATISFIED"
        if item.predecessor_materialisation_required:
            return "PREDECESSOR_MATERIALISATION_REQUIRED"
        if item.side_effect_class == "IRREVERSIBLE_OR_UNKNOWN":
            return "IRREVERSIBLE_OR_UNKNOWN_SIDE_EFFECT"
        if item.executor_id is None:
            return "EXECUTOR_UNKNOWN"
        executor = executors.get(item.executor_id)
        if executor is None or not executor.active:
            return "EXECUTOR_UNKNOWN_OR_INACTIVE"
        if item.action not in executor.supported_actions:
            return "EXECUTOR_ACTION_UNSUPPORTED"
        if not executor.non_writing_fixture_only:
            return "LIVE_WRITE_CAPABILITY_NOT_AUTHORISED"
        return None
