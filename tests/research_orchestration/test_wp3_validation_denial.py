from __future__ import annotations

from ovc.research_orchestration.authority import AuthorityRequirementRegistry, preflight_plan_authority
from ovc.research_orchestration.models import PipelineProfile, PopulationSpec, StageSpec
from ovc.research_orchestration.planner import build_plan
from ovc.research_orchestration.registry import build_registry_snapshot


def source_stage() -> StageSpec:
    return StageSpec(
        stage_id="VALIDATION_SOURCE",
        stage_version="0.1",
        stage_kind="SOURCE_BINDING",
        implementation_identity="impl:validation-source",
        contract_identity="contract:validation-source",
        schema_identity="schema:validation-source",
        input_types=(),
        output_types=("RAW",),
        authority_requirements=("VALIDATION_REAL_ACCESS",),
    )


def validation_population() -> PopulationSpec:
    return PopulationSpec(
        population_id="P.VALIDATION.PROTECTED",
        population_mode="SEALED_REAL_REPLAY",
        population_schema_version="0.1",
        instrument="GBPUSD",
        price_side="BID",
        clock_lattice="15M",
        role="VALIDATION",
        source_adapter_id="PROTECTED_VALIDATION_ADAPTER",
        validation_access_state="LOCKED_UNCONSUMED",
        capacity_tier="MICRO",
        source_release_id="VALIDATION.RELEASE.SECRET",
        source_manifest_hash="VALIDATION.MANIFEST.SECRET",
        start_time="2025-01-01T00:00:00Z",
        end_time="2026-01-01T00:00:00Z",
        external_artifact_root_alias="SHOULD_NOT_RESOLVE",
    )


def test_validation_is_denied_before_protected_location_object_time_or_row_resolution() -> None:
    stage = source_stage()
    profile = PipelineProfile("VALIDATION_PROFILE", "0.1", (stage.stage_id,), ("RAW",))
    plan = build_plan(snapshot=build_registry_snapshot(stage_specs=(stage,), profiles=(profile,)), profile_id=profile.profile_id)
    receipt = preflight_plan_authority(
        plan=plan,
        stage_specs=(stage,),
        population=validation_population(),
        requirement_registry=AuthorityRequirementRegistry(()),
        bindings=(),
    )
    assert receipt.execution_status == "NOT_AUTHORISED"
    assert receipt.population.status == "NOT_AUTHORISED"
    assert receipt.population.reason_codes == ("IROF_VALIDATION_DENIED_BEFORE_PROTECTED_RESOLUTION",)
    assert receipt.population.protected_resolution_performed is False
    assert receipt.population.physical_location_resolved is False
    assert receipt.population.source_release_id is None
    assert receipt.population.source_manifest_hash is None
    assert receipt.token_consumption_performed is False
    assert receipt.blocked_stage_ids == ("VALIDATION_SOURCE",)
