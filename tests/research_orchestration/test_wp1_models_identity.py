from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_orchestration.models import (
    ArtifactRef,
    AuthorityBinding,
    EXECUTION_STATUSES,
    PipelineProfile,
    PopulationSpec,
    ResearchRunSpec,
    SemanticCacheKey,
    StageDependency,
    StageSpec,
)
from ovc.research_orchestration.population import population_from_mapping
from ovc.research_orchestration.profiles import builtin_profiles
from ovc.research_orchestration.registry import RegistryError, build_registry_snapshot
from ovc.research_orchestration.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "research_orchestration" / "wp1"
SCHEMA = ROOT / "schemas" / "research_orchestration" / "core_objects_v0_1.schema.json"


def _population(**overrides):
    values = {
        "population_id": "POP.1",
        "population_mode": "SYNTHETIC_FIXTURE",
        "population_schema_version": "0.1",
        "instrument": "GBPUSD",
        "price_side": "BID",
        "clock_lattice": "15M+2H_A_L",
        "role": "FIXTURE",
        "source_adapter_id": "SYNTHETIC",
        "validation_access_state": "LOCKED_UNCONSUMED",
        "capacity_tier": "MICRO",
        "synthetic_fixture_id": "FIX.1",
        "authority_binding_ids": ("AUTH.SYNTHETIC",),
    }
    values.update(overrides)
    return PopulationSpec(**values)


def _stage(stage_id="C1", *, implementation="impl:1"):
    return StageSpec(
        stage_id=stage_id,
        stage_version="0.1",
        stage_kind="DESCRIPTIVE",
        implementation_identity=implementation,
        contract_identity=f"contract:{stage_id}:1",
        schema_identity=f"schema:{stage_id}:1",
        input_types=("INPUT",),
        output_types=(f"{stage_id}_OUT",),
        deterministic_mode="EXACT",
        adapter_identity=f"adapter:{stage_id}:1",
    )


def _run(*, workers=1, scheduling="SERIAL", root="external://a", pack="PACK.1"):
    stage = _stage()
    profile = PipelineProfile("TEST", "0.1", (stage.stage_id,), ("C1_OUT",))
    return ResearchRunSpec(
        population=_population(),
        profile=profile,
        stage_specs=(stage,),
        authority_bindings=(),
        pack_bindings={"representation": pack},
        chronology_policy_id="FIRST_VALID.v1",
        workers=workers,
        scheduling_policy=scheduling,
        physical_output_root=root,
    )


def test_population_physical_location_does_not_change_semantic_identity():
    left = _population(external_artifact_root_alias="EXTERNAL_A")
    right = _population(external_artifact_root_alias="EXTERNAL_B")
    assert left.logical_hash == right.logical_hash
    assert left.to_dict()["external_artifact_root_alias"] != right.to_dict()["external_artifact_root_alias"]


def test_run_workers_schedule_and_physical_root_do_not_change_semantic_identity():
    left = _run(workers=1, scheduling="SERIAL", root="external://a")
    right = _run(workers=8, scheduling="PARALLEL", root="external://relocated")
    assert left.semantic_run_id == right.semantic_run_id


def test_pack_change_changes_run_identity():
    assert _run(pack="PACK.1").semantic_run_id != _run(pack="PACK.2").semantic_run_id


def test_artifact_location_is_not_semantic_identity():
    common = dict(
        artifact_id="A1", logical_hash="a" * 64, artifact_type="STATE_STREAM",
        owner_stage_id="C2", owner_run_id="RUN1", lifecycle_state="COMPLETE",
        content_sha256="b" * 64,
    )
    left = ArtifactRef(**common, locations=({"root_alias": "A", "relative_path": "one"},))
    right = ArtifactRef(**common, locations=({"root_alias": "B", "relative_path": "two"},))
    assert logical_sha256(left.semantic_dict()) == logical_sha256(right.semantic_dict())


def test_cache_key_changes_on_semantic_pack_change_not_physical_path():
    base = dict(
        stage_id="SRI", stage_version="0.1", parent_semantic_hashes=("p1",),
        contract_identity="c1", schema_identity="s1", implementation_identity="i1",
        population_hash="pop", chronology_identity="first-valid-v1",
    )
    assert SemanticCacheKey(**base, pack_bindings={"rep": "R1"}).key != SemanticCacheKey(**base, pack_bindings={"rep": "R2"}).key


def test_duplicate_stage_and_profile_ids_fail_closed():
    stage = _stage()
    profile = PipelineProfile("P", "0.1", ("C1",))
    with pytest.raises(RegistryError, match="IROF_DUPLICATE_STAGE_ID"):
        build_registry_snapshot(stage_specs=(stage, stage), profiles=(profile,))
    with pytest.raises(RegistryError, match="IROF_DUPLICATE_PROFILE_ID"):
        build_registry_snapshot(stage_specs=(stage,), profiles=(profile, profile))


def test_profile_unknown_stage_fails_closed():
    with pytest.raises(RegistryError, match="IROF_PROFILE_UNKNOWN_STAGE"):
        build_registry_snapshot(stage_specs=(_stage(),), profiles=(PipelineProfile("BAD", "0.1", ("C2",)),))


def test_wrapper_scientific_mutation_policy_is_rejected():
    with pytest.raises(ValueError, match="scientific wrapper mutation"):
        StageSpec(
            stage_id="X", stage_version="0.1", stage_kind="TEST",
            implementation_identity="i", contract_identity="c", schema_identity="s",
            input_types=(), output_types=("X",), adapter_identity="a",
            wrapper_mutation_policy="ALLOW_IMPUTATION",
        )


def test_population_mode_specific_requirements_fail_closed():
    with pytest.raises(ValueError, match="synthetic_fixture_id"):
        _population(synthetic_fixture_id=None)
    with pytest.raises(ValueError, match="source_release_id"):
        _population(population_mode="SEALED_REAL_REPLAY", synthetic_fixture_id=None)


def test_authority_binding_is_a_record_not_a_self_grant():
    binding = AuthorityBinding(
        binding_id="B1", owner_programme="OWNER", owner_gate="G1", authority_kind="REAL_REPLAY",
        subject="C2E", exact_scope={"population": "P"}, decision="NOT_AUTHORISED",
        status="CURRENT", source_decision_artifact="owner/decision.json",
    )
    assert binding.decision == "NOT_AUTHORISED"
    assert "grant" not in binding.to_dict()


def test_scientific_null_statuses_are_not_execution_statuses():
    for value in ("NOT_EVALUABLE", "NOT_COMPARABLE", "AMBIGUOUS", "RESIDUAL", "NO_STABLE_FAMILY"):
        assert value not in EXECUTION_STATUSES


def test_fixture_population_examples_parse_deterministically():
    for name in ("population_synthetic_fixture.json", "population_synthetic_generated.json", "population_sealed_replay_request.json"):
        raw = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        first = population_from_mapping(raw)
        second = population_from_mapping(raw)
        assert first.logical_hash == second.logical_hash


def test_core_schema_declares_every_required_wp1_object():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    expected = {
        "PopulationSpec", "PipelineProfile", "StageSpec", "StageInvocation", "StageDependency",
        "AuthorityBinding", "ResearchRunSpec", "IntegratedRunManifest", "StageExecutionReceipt",
        "IntegratedRunReceipt", "ArtifactRef", "SemanticCacheKey", "CheckpointRecord", "RestartLedger",
        "CapacityBudget", "CapacityReceipt", "RunFailure", "RunComparisonRecord",
    }
    assert expected <= set(schema["$defs"])


def test_builtin_profiles_are_unique_and_future_profiles_are_not_present():
    profiles = builtin_profiles()
    ids = [item.profile_id for item in profiles]
    assert len(ids) == len(set(ids))
    assert "FULL_DESCRIPTIVE" in ids
    assert "FULL_DESCRIPTIVE_WITH_CONTEXT" in ids
    assert "OUTCOME_RESEARCH" not in ids
    assert "FULL_ABCD" not in ids


def test_stage_dependency_disposition_contract():
    dep = StageDependency("C1", "REQUIRED", ("C1_OUT",))
    assert dep.to_dict()["disposition"] == "REQUIRED"
    with pytest.raises(ValueError, match="invalid dependency disposition"):
        StageDependency("C1", "IMPLICIT", ())
