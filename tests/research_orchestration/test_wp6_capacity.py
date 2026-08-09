from __future__ import annotations

import pytest

from ovc.research_orchestration.capacity import (
    CapacityError,
    CapacityEstimate,
    ExperimentIdentity,
    RecoveryProposal,
    assert_same_experiment,
    evaluate_capacity,
    ready_stage_ids,
    validate_recovery_proposal,
)
from ovc.research_orchestration.models import CapacityBudget, PipelineProfile, StageDependency, StageSpec
from ovc.research_orchestration.planner import build_plan
from ovc.research_orchestration.registry import build_registry_snapshot


def identity(*, pack="PACK.A") -> ExperimentIdentity:
    return ExperimentIdentity(
        semantic_run_id="IROF.RUN.SAME",
        population_hash="POP.HASH",
        profile_hash="PROFILE.HASH",
        stage_spec_hashes=(("A", "SPEC.A"),),
        pack_bindings=(("representation", pack),),
    )


def test_within_budget_is_ready() -> None:
    decision = evaluate_capacity(
        identity=identity(),
        stage_id="A",
        budget=CapacityBudget("T", max_wall_seconds=10, max_peak_rss_bytes=1000, max_external_bytes=1000, max_workers=2),
        estimate=CapacityEstimate(wall_seconds=5, peak_rss_bytes=500, external_bytes=100, workers=2, work_units=10),
    )
    assert decision.status == "READY"
    assert decision.receipt.scientific_effect == "NONE"
    assert decision.experiment_identity == identity()


def test_forced_capacity_failure_preserves_exact_experiment_identity() -> None:
    before = identity()
    decision = evaluate_capacity(
        identity=before,
        stage_id="A",
        budget=CapacityBudget("T", max_wall_seconds=1, max_peak_rss_bytes=100),
        estimate=CapacityEstimate(wall_seconds=5, peak_rss_bytes=500),
    )
    assert decision.status == "CAPACITY_EXCEEDED"
    assert set(decision.reason_codes) == {"IROF_CAPACITY_RSS_EXCEEDED", "IROF_CAPACITY_WALL_EXCEEDED"}
    assert decision.experiment_identity == before
    assert decision.receipt.run_id == before.semantic_run_id
    assert decision.receipt.scientific_effect == "NONE"


@pytest.mark.parametrize("action", [
    "SAMPLE_POPULATION", "DROP_METHOD", "DROP_CONFIGURATION", "REDUCE_GRID",
    "CHANGE_THRESHOLD", "CHANGE_DENOMINATOR", "SUBSTITUTE_PROFILE", "CHANGE_PACK",
])
def test_capacity_recovery_cannot_mutate_experiment(action: str) -> None:
    with pytest.raises(CapacityError, match="IROF_CAPACITY_EXPERIMENT_MUTATION_FORBIDDEN"):
        RecoveryProposal(identity(), action)


def test_worker_reduction_is_operational_only() -> None:
    before = identity()
    proposal = RecoveryProposal(before, "REDUCE_WORKERS", requested_workers=1)
    after = validate_recovery_proposal(before, proposal)
    assert_same_experiment(before, after)
    assert after == before


def test_pack_change_is_detected_as_experiment_change() -> None:
    with pytest.raises(CapacityError, match="IROF_CAPACITY_EXPERIMENT_IDENTITY_CHANGED"):
        assert_same_experiment(identity(pack="PACK.A"), identity(pack="PACK.B"))


def _stage(stage_id: str, deps=()) -> StageSpec:
    return StageSpec(
        stage_id=stage_id,
        stage_version="0.1",
        stage_kind="FIXTURE",
        implementation_identity=f"impl:{stage_id}",
        contract_identity=f"contract:{stage_id}",
        schema_identity=f"schema:{stage_id}",
        input_types=(),
        output_types=(f"{stage_id}_OUT",),
        dependencies=tuple(deps),
    )


def test_scheduler_returns_only_dag_ready_stages_in_canonical_order() -> None:
    a = _stage("A")
    b = _stage("B", (StageDependency("A", "REQUIRED", ("A_OUT",)),))
    c = _stage("C", (StageDependency("A", "REQUIRED", ("A_OUT",)),))
    d = _stage("D", (StageDependency("B", "REQUIRED", ("B_OUT",)), StageDependency("C", "REQUIRED", ("C_OUT",))))
    profile = PipelineProfile("P", "0.1", ("A", "B", "C", "D"))
    plan = build_plan(snapshot=build_registry_snapshot(stage_specs=(d, c, b, a), profiles=(profile,)), profile_id="P")
    assert ready_stage_ids(plan, max_new_workers=2) == ("A",)
    assert ready_stage_ids(plan, completed_stage_ids=("A",), max_new_workers=2) == ("B", "C")
    assert ready_stage_ids(plan, completed_stage_ids=("A", "B", "C"), max_new_workers=1) == ("D",)
