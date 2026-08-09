from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .models import CapacityBudget, CapacityReceipt
from .planner import CanonicalPlan


class CapacityError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


ALLOWED_RECOVERY_ACTIONS = frozenset({
    "REDUCE_WORKERS",
    "SERIALIZE",
    "RESUME_LATER",
    "MOVE_PHYSICAL_STORAGE",
    "RETRY_SAME_EXPERIMENT",
})
FORBIDDEN_EXPERIMENT_MUTATIONS = frozenset({
    "SAMPLE_POPULATION",
    "DROP_METHOD",
    "DROP_CONFIGURATION",
    "REDUCE_GRID",
    "CHANGE_THRESHOLD",
    "CHANGE_DENOMINATOR",
    "SUBSTITUTE_PROFILE",
    "CHANGE_PACK",
    "CHANGE_POPULATION",
})


@dataclass(frozen=True)
class ExperimentIdentity:
    semantic_run_id: str
    population_hash: str
    profile_hash: str
    stage_spec_hashes: tuple[tuple[str, str], ...]
    pack_bindings: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.semantic_run_id or not self.population_hash or not self.profile_hash:
            raise CapacityError("IROF_CAPACITY_EXPERIMENT_ID_REQUIRED", self.semantic_run_id)


@dataclass(frozen=True)
class CapacityEstimate:
    wall_seconds: float | None = None
    peak_rss_bytes: int | None = None
    external_bytes: int | None = None
    workers: int | None = None
    work_units: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "wall_seconds": self.wall_seconds,
            "peak_rss_bytes": self.peak_rss_bytes,
            "external_bytes": self.external_bytes,
            "workers": self.workers,
            "work_units": self.work_units,
        }


@dataclass(frozen=True)
class CapacityDecision:
    experiment_identity: ExperimentIdentity
    stage_id: str
    status: str
    reason_codes: tuple[str, ...]
    receipt: CapacityReceipt
    scientific_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.scientific_effect != "NONE":
            raise CapacityError("IROF_CAPACITY_SCIENTIFIC_EFFECT_FORBIDDEN", self.stage_id)


@dataclass(frozen=True)
class RecoveryProposal:
    experiment_identity: ExperimentIdentity
    action: str
    requested_workers: int | None = None

    def __post_init__(self) -> None:
        action = self.action.upper()
        if action in FORBIDDEN_EXPERIMENT_MUTATIONS:
            raise CapacityError("IROF_CAPACITY_EXPERIMENT_MUTATION_FORBIDDEN", action)
        if action not in ALLOWED_RECOVERY_ACTIONS:
            raise CapacityError("IROF_CAPACITY_RECOVERY_ACTION_UNKNOWN", action)
        if self.requested_workers is not None and self.requested_workers <= 0:
            raise CapacityError("IROF_CAPACITY_WORKERS_INVALID", str(self.requested_workers))


def evaluate_capacity(
    *,
    identity: ExperimentIdentity,
    stage_id: str,
    budget: CapacityBudget,
    estimate: CapacityEstimate,
) -> CapacityDecision:
    reasons: list[str] = []
    if budget.max_wall_seconds is not None and estimate.wall_seconds is not None and estimate.wall_seconds > budget.max_wall_seconds:
        reasons.append("IROF_CAPACITY_WALL_EXCEEDED")
    if budget.max_peak_rss_bytes is not None and estimate.peak_rss_bytes is not None and estimate.peak_rss_bytes > budget.max_peak_rss_bytes:
        reasons.append("IROF_CAPACITY_RSS_EXCEEDED")
    if budget.max_external_bytes is not None and estimate.external_bytes is not None and estimate.external_bytes > budget.max_external_bytes:
        reasons.append("IROF_CAPACITY_EXTERNAL_BYTES_EXCEEDED")
    if budget.max_workers is not None and estimate.workers is not None and estimate.workers > budget.max_workers:
        reasons.append("IROF_CAPACITY_WORKERS_EXCEEDED")
    status = "CAPACITY_EXCEEDED" if reasons else "READY"
    receipt = CapacityReceipt(
        run_id=identity.semantic_run_id,
        stage_id=stage_id,
        status=status,
        estimated=estimate.to_dict(),
        observed={},
        reason_codes=tuple(sorted(reasons)),
        scientific_effect="NONE",
    )
    return CapacityDecision(identity, stage_id, status, tuple(sorted(reasons)), receipt)


def assert_same_experiment(before: ExperimentIdentity, after: ExperimentIdentity) -> None:
    if before != after:
        raise CapacityError("IROF_CAPACITY_EXPERIMENT_IDENTITY_CHANGED", before.semantic_run_id)


def ready_stage_ids(
    plan: CanonicalPlan,
    *,
    completed_stage_ids: Iterable[str] = (),
    running_stage_ids: Iterable[str] = (),
    max_new_workers: int = 1,
) -> tuple[str, ...]:
    if max_new_workers <= 0:
        raise CapacityError("IROF_CAPACITY_WORKERS_INVALID", str(max_new_workers))
    completed = set(completed_stage_ids)
    running = set(running_stage_ids)
    known = set(plan.ordered_stage_ids)
    unknown = (completed | running) - known
    if unknown:
        raise CapacityError("IROF_CAPACITY_UNKNOWN_STAGE", ",".join(sorted(unknown)))
    candidates: list[str] = []
    for stage_id in plan.ordered_stage_ids:
        if stage_id in completed or stage_id in running:
            continue
        parents = set(plan.dag.parents_of(stage_id))
        if parents.issubset(completed):
            candidates.append(stage_id)
    return tuple(candidates[:max_new_workers])


def validate_recovery_proposal(before: ExperimentIdentity, proposal: RecoveryProposal) -> ExperimentIdentity:
    assert_same_experiment(before, proposal.experiment_identity)
    return proposal.experiment_identity


def observed_capacity_receipt(
    *,
    identity: ExperimentIdentity,
    stage_id: str,
    status: str,
    estimate: CapacityEstimate,
    observed: Mapping[str, Any],
    reason_codes: Iterable[str] = (),
) -> CapacityReceipt:
    if status not in {"READY", "RUNNING", "COMPLETE", "CAPACITY_EXCEEDED", "FAILED", "QUARANTINED"}:
        raise CapacityError("IROF_CAPACITY_STATUS_INVALID", status)
    return CapacityReceipt(
        run_id=identity.semantic_run_id,
        stage_id=stage_id,
        status=status,
        estimated=estimate.to_dict(),
        observed=dict(observed),
        reason_codes=tuple(sorted(set(reason_codes))),
        scientific_effect="NONE",
    )
