from __future__ import annotations

import pytest

from ovc.research_orchestration.dag import DagError, build_canonical_dag
from ovc.research_orchestration.models import PipelineProfile, StageDependency, StageSpec
from ovc.research_orchestration.planner import build_plan
from ovc.research_orchestration.registry import build_registry_snapshot


def stage(stage_id: str, *, inputs=(), outputs=(), deps=()) -> StageSpec:
    return StageSpec(
        stage_id=stage_id,
        stage_version="0.1",
        stage_kind="FIXTURE",
        implementation_identity=f"impl:{stage_id}",
        contract_identity=f"contract:{stage_id}",
        schema_identity=f"schema:{stage_id}",
        input_types=tuple(inputs),
        output_types=tuple(outputs),
        dependencies=tuple(deps),
    )


def test_registration_and_parent_order_do_not_change_canonical_plan() -> None:
    a = stage("A", outputs=("A_OUT",))
    b = stage("B", inputs=("A_OUT",), outputs=("B_OUT",), deps=(StageDependency("A", "REQUIRED", ("A_OUT",)),))
    c = stage("C", inputs=("A_OUT",), outputs=("C_OUT",), deps=(StageDependency("A", "REQUIRED", ("A_OUT",)),))
    d1 = stage("D", inputs=("B_OUT", "C_OUT"), outputs=("D_OUT",), deps=(StageDependency("B", "REQUIRED", ("B_OUT",)), StageDependency("C", "REQUIRED", ("C_OUT",))))
    d2 = stage("D", inputs=("B_OUT", "C_OUT"), outputs=("D_OUT",), deps=(StageDependency("C", "REQUIRED", ("C_OUT",)), StageDependency("B", "REQUIRED", ("B_OUT",))))
    profile = PipelineProfile("P", "0.1", ("A", "B", "C", "D"))
    first = build_plan(snapshot=build_registry_snapshot(stage_specs=(d1, c, a, b), profiles=(profile,)), profile_id="P")
    second = build_plan(snapshot=build_registry_snapshot(stage_specs=(b, a, d2, c), profiles=(profile,)), profile_id="P")
    assert first.ordered_stage_ids == ("A", "B", "C", "D")
    assert first.logical_hash == second.logical_hash


def test_cycle_fails_closed() -> None:
    a = stage("A", outputs=("A_OUT",), deps=(StageDependency("B", "REQUIRED", ("B_OUT",)),))
    b = stage("B", outputs=("B_OUT",), deps=(StageDependency("A", "REQUIRED", ("A_OUT",)),))
    with pytest.raises(DagError, match="IROF_DEPENDENCY_CYCLE"):
        build_canonical_dag(stage_specs=(a, b), included_stage_ids=("A", "B"))


def test_missing_required_parent_fails_closed() -> None:
    a = stage("A", outputs=("A_OUT",))
    b = stage("B", inputs=("A_OUT",), outputs=("B_OUT",), deps=(StageDependency("A", "REQUIRED", ("A_OUT",)),))
    with pytest.raises(DagError, match="IROF_MISSING_REQUIRED_DEPENDENCY"):
        build_canonical_dag(stage_specs=(a, b), included_stage_ids=("B",))


def test_forbidden_edge_fails_closed() -> None:
    a = stage("A", outputs=("A_OUT",))
    b = stage("B", outputs=("B_OUT",), deps=(StageDependency("A", "FORBIDDEN"),))
    with pytest.raises(DagError, match="IROF_FORBIDDEN_DEPENDENCY"):
        build_canonical_dag(stage_specs=(a, b), included_stage_ids=("A", "B"))


def test_dependency_expected_output_mismatch_fails_closed() -> None:
    a = stage("A", outputs=("A_OUT",))
    b = stage("B", outputs=("B_OUT",), deps=(StageDependency("A", "REQUIRED", ("NOT_A_OUT",)),))
    with pytest.raises(DagError, match="IROF_DEPENDENCY_OUTPUT_TYPE_MISMATCH"):
        build_canonical_dag(stage_specs=(a, b), included_stage_ids=("A", "B"))


def test_hidden_extra_dependency_is_not_inferred_from_profile_membership() -> None:
    a = stage("A", outputs=("SECRET",))
    b = stage("B", inputs=("SECRET",), outputs=("B_OUT",))
    profile = PipelineProfile("P", "0.1", ("A", "B"))
    snapshot = build_registry_snapshot(stage_specs=(a, b), profiles=(profile,))
    with pytest.raises(DagError, match="IROF_INPUT_TYPE_UNSATISFIED"):
        build_plan(snapshot=snapshot, profile_id="P")


def test_external_input_binding_is_explicit_and_semantic() -> None:
    a = stage("A", inputs=("EXTERNAL",), outputs=("A_OUT",))
    profile = PipelineProfile("P", "0.1", ("A",))
    snapshot = build_registry_snapshot(stage_specs=(a,), profiles=(profile,))
    plan = build_plan(snapshot=snapshot, profile_id="P", external_input_types=("EXTERNAL",))
    assert plan.ordered_stage_ids == ("A",)
    assert plan.external_input_types == ("EXTERNAL",)


def test_blocked_descendants_are_transitive_and_do_not_include_source_block() -> None:
    a = stage("A", outputs=("A_OUT",))
    b = stage("B", outputs=("B_OUT",), deps=(StageDependency("A", "REQUIRED", ("A_OUT",)),))
    c = stage("C", outputs=("C_OUT",), deps=(StageDependency("B", "REQUIRED", ("B_OUT",)),))
    dag = build_canonical_dag(stage_specs=(c, a, b), included_stage_ids=("A", "B", "C"))
    assert dag.blocked_descendants(("A",)) == ("B", "C")


def test_extension_stage_registers_without_scheduler_change() -> None:
    a = stage("A", outputs=("A_OUT",))
    extension = stage("ZZ_FUTURE", inputs=("A_OUT",), outputs=("META",), deps=(StageDependency("A", "REQUIRED", ("A_OUT",)),))
    profile = PipelineProfile("EXT", "0.1", ("A", "ZZ_FUTURE"), ("META",))
    snapshot = build_registry_snapshot(stage_specs=(extension, a), profiles=(profile,))
    plan = build_plan(snapshot=snapshot, profile_id="EXT")
    assert plan.ordered_stage_ids == ("A", "ZZ_FUTURE")
