from __future__ import annotations

from dataclasses import replace

import pytest

from ovc.shared_systems.execution import (
    CapacityReceipt, ExecutionEnvironmentManifest, RunExecutionManifest,
    RunSpecification, SemanticGenerationRef, SharedExecutionError,
    deterministic_partitions, reconcile_exact, run_reference,
)


def generation() -> SemanticGenerationRef:
    return SemanticGenerationRef("FIXTURE_OWNER", "FIXTURE.GEN.v1", ("FIXTURE.CONTRACT.v1",))


def spec() -> RunSpecification:
    return RunSpecification(generation().logical_id, ("R1", "R2", "R3", "R4"), "FIXTURE.SCOPE.v1", "2026-08-01T12:00:00Z", {"precision": "EXACT"}, "FIXTURE.OUTPUT.v1", ("SOURCE:FVT<=2026-08-01T12:00:00Z",))


def manifest(run: RunSpecification, *, workers: int = 1, chunk: int = 1, environment: str = "ENV.A", host: str = "/a") -> RunExecutionManifest:
    return RunExecutionManifest(run.logical_id, environment, f"ATTEMPT.{workers}.{chunk}.{environment}", workers, chunk, "LOCAL_REFERENCE", host)


RECORDS = {"R1": 1, "R2": 2, "R3": 3, "R4": 4}
TRANSFORM = lambda value: {"exact": value * 7}


def test_semantic_and_run_identity_are_exact_and_stable() -> None:
    assert generation().logical_id == generation().logical_id
    assert spec().logical_id == spec().logical_id
    with pytest.raises(SharedExecutionError, match="EXACT_REF_REQUIRED"):
        SemanticGenerationRef("OWNER", "latest", ("C.v1",))


def test_physical_manifest_fields_do_not_enter_logical_result_identity() -> None:
    run = spec()
    a = run_reference(run, manifest(run), RECORDS, TRANSFORM)
    b = run_reference(run, manifest(run, workers=4, chunk=3, environment="ENV.B", host="D:\\scratch"), RECORDS, TRANSFORM, physical_order=("R4", "R2", "R1", "R3"))
    assert reconcile_exact(a, b) == a.logical_result_identity
    assert a.ordered_results == b.ordered_results


def test_deterministic_partition_api_changes_only_physical_groups() -> None:
    run = spec()
    assert deterministic_partitions(run, 1) == (("R1",), ("R2",), ("R3",), ("R4",))
    assert deterministic_partitions(run, 3) == (("R1", "R2", "R3"), ("R4",))


def test_crash_before_commit_resumes_exactly() -> None:
    run = spec()
    fresh = run_reference(run, manifest(run), RECORDS, TRANSFORM)
    interrupted = run_reference(run, manifest(run), RECORDS, TRANSFORM, stop_before=2)
    assert interrupted.status == "CHECKPOINTED_BEFORE_COMMIT"
    resumed = run_reference(run, manifest(run, workers=3, chunk=2), RECORDS, TRANSFORM, checkpoint=interrupted.checkpoint)
    assert reconcile_exact(fresh, resumed) == fresh.logical_result_identity


def test_crash_after_commit_does_not_duplicate_committed_item() -> None:
    run = spec()
    fresh = run_reference(run, manifest(run), RECORDS, TRANSFORM)
    interrupted = run_reference(run, manifest(run), RECORDS, TRANSFORM, stop_after=1)
    assert interrupted.status == "CHECKPOINTED_AFTER_COMMIT"
    assert tuple(key for key, _ in interrupted.ordered_results) == ("R1", "R2")
    resumed = run_reference(run, manifest(run), RECORDS, TRANSFORM, checkpoint=interrupted.checkpoint)
    assert tuple(key for key, _ in resumed.ordered_results) == run.population_ids
    assert reconcile_exact(fresh, resumed) == fresh.logical_result_identity


def test_corrupt_or_wrong_checkpoint_fails_closed() -> None:
    run = spec()
    checkpoint = run_reference(run, manifest(run), RECORDS, TRANSFORM, stop_after=0).checkpoint
    assert checkpoint
    with pytest.raises(SharedExecutionError, match="HASH_MISMATCH"):
        run_reference(run, manifest(run), RECORDS, TRANSFORM, checkpoint=replace(checkpoint, prefix_hash="0" * 64))


def test_capacity_exceeded_preserves_population_precision_and_emits_no_result() -> None:
    run = spec()
    result = run_reference(run, manifest(run), RECORDS, TRANSFORM, available_units=3)
    assert result.status == "CAPACITY_EXCEEDED"
    assert result.logical_result_identity is None and result.ordered_results == ()
    assert result.capacity_receipt.population_preserved is True
    assert result.capacity_receipt.precision_preserved is True
    assert result.capacity_receipt.sampling_applied is False
    with pytest.raises(SharedExecutionError, match="DEGRADATION"):
        CapacityReceipt(run.logical_id, "CAPACITY_EXCEEDED", 4, 3, sampling_applied=True)


def test_population_change_cannot_be_hidden_as_physical_partitioning() -> None:
    run = spec()
    with pytest.raises(SharedExecutionError, match="POPULATION_MISMATCH"):
        run_reference(run, manifest(run), {"R1": 1}, TRANSFORM)
    with pytest.raises(SharedExecutionError, match="PHYSICAL_ORDER_POPULATION_MISMATCH"):
        run_reference(run, manifest(run), RECORDS, TRANSFORM, physical_order=("R1", "R2"))


def test_barriers_are_source_bound_not_wall_clock_authority() -> None:
    with pytest.raises(SharedExecutionError, match="WALL_CLOCK"):
        replace(spec(), logical_barriers=("WALL_CLOCK:12:00",))


def test_environment_is_manifested_but_nonsemantic() -> None:
    env = ExecutionEnvironmentManifest("ENV.A", "linux", "x86_64", "python-3.11", "LOCK.v1", "CROSS_ENV_EXACT")
    assert env.reproducibility_class == "CROSS_ENV_EXACT"
    with pytest.raises(SharedExecutionError, match="EXACT_REF_REQUIRED"):
        replace(env, toolchain_lock_ref="latest")
