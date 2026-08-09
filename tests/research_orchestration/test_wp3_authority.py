from __future__ import annotations

from ovc.research_orchestration.authority import (
    AuthorityRequirementRegistry,
    AuthorityRequirementSpec,
    preflight_plan_authority,
    resolve_requirement,
)
from ovc.research_orchestration.models import AuthorityBinding, PipelineProfile, PopulationSpec, StageDependency, StageSpec
from ovc.research_orchestration.planner import build_plan
from ovc.research_orchestration.profiles import profile_by_id
from ovc.research_orchestration.registry import build_registry_snapshot


def stage(stage_id: str, *, kind="COMPUTE", inputs=(), outputs=(), deps=(), authority=()) -> StageSpec:
    return StageSpec(
        stage_id=stage_id,
        stage_version="0.1",
        stage_kind=kind,
        implementation_identity=f"impl:{stage_id}",
        contract_identity=f"contract:{stage_id}",
        schema_identity=f"schema:{stage_id}",
        input_types=tuple(inputs),
        output_types=tuple(outputs),
        dependencies=tuple(deps),
        authority_requirements=tuple(authority),
    )


def binding(
    binding_id: str,
    *,
    owner_programme: str,
    owner_gate: str,
    authority_kind: str,
    subject: str,
    scope: dict[str, str],
    decision="ALLOW",
    status="APPROVED",
    token_state=None,
) -> AuthorityBinding:
    return AuthorityBinding(
        binding_id=binding_id,
        owner_programme=owner_programme,
        owner_gate=owner_gate,
        authority_kind=authority_kind,
        subject=subject,
        exact_scope=scope,
        decision=decision,
        status=status,
        source_decision_artifact=f"fixture:{binding_id}",
        token_state=token_state,
    )


def synthetic_population() -> PopulationSpec:
    return PopulationSpec(
        population_id="P.SYN",
        population_mode="SYNTHETIC_FIXTURE",
        population_schema_version="0.1",
        instrument="GBPUSD",
        price_side="BID",
        clock_lattice="15M",
        role="DISCOVERY_FIXTURE",
        source_adapter_id="SYNTHETIC",
        validation_access_state="LOCKED_UNCONSUMED",
        capacity_tier="MICRO",
        synthetic_fixture_id="FIX.WP3",
    )


def june_population(*, role="DISCOVERY", validation_state="LOCKED_UNCONSUMED") -> PopulationSpec:
    return PopulationSpec(
        population_id="SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd",
        population_mode="SEALED_REAL_REPLAY",
        population_schema_version="0.1",
        instrument="GBPUSD",
        price_side="BID_ASK",
        clock_lattice="15M+2H_A_L",
        role=role,
        source_adapter_id="OPT_A_SEALED_HANDOFF",
        validation_access_state=validation_state,
        capacity_tier="LARGE",
        source_release_id="RPS.DUKASCOPY.GBPUSD.20260622_20260725",
        source_manifest_hash="fixture-manifest-hash",
        start_time="2026-06-01T00:00:00Z",
        end_time="2026-07-01T00:00:00Z",
    )


def full_descriptive_stages() -> tuple[StageSpec, ...]:
    return (
        stage("POPULATION_SOURCE_OPT_A", kind="SOURCE_BINDING", outputs=("OPT_A_OBSERVATIONS",), authority=("OPT_A_SEALED_REPLAY_READ",)),
        stage("C1", inputs=("OPT_A_OBSERVATIONS",), outputs=("C1_RECORDS",), deps=(StageDependency("POPULATION_SOURCE_OPT_A", "REQUIRED", ("OPT_A_OBSERVATIONS",)),)),
        stage("C2_REVISED", inputs=("C1_RECORDS",), outputs=("C2_STATE_STREAM",), deps=(StageDependency("C1", "REQUIRED", ("C1_RECORDS",)),)),
        stage("C2E_V0_2", inputs=("C2_STATE_STREAM",), outputs=("C2E_STREAM",), deps=(StageDependency("C2_REVISED", "REQUIRED", ("C2_STATE_STREAM",)),), authority=("C2E_V0_2_REAL_REPLAY",)),
        stage("SRI_REPRESENTATION", inputs=("C2E_STREAM",), outputs=("REPRESENTATION_POPULATION",), deps=(StageDependency("C2E_V0_2", "REQUIRED", ("C2E_STREAM",)),)),
        stage("COMPARABILITY_COMPARISON_DISTANCE", inputs=("REPRESENTATION_POPULATION",), outputs=("COMPARISON_SURFACE",), deps=(StageDependency("SRI_REPRESENTATION", "REQUIRED", ("REPRESENTATION_POPULATION",)),)),
        stage("FDI_C2G_FAMILY", inputs=("COMPARISON_SURFACE",), outputs=("FAMILY_CATALOG",), deps=(StageDependency("COMPARABILITY_COMPARISON_DISTANCE", "REQUIRED", ("COMPARISON_SURFACE",)),)),
        stage("FAMILY_EVIDENCE_STREAM", inputs=("FAMILY_CATALOG",), outputs=("FAMILY_EVIDENCE_STREAM",), deps=(StageDependency("FDI_C2G_FAMILY", "REQUIRED", ("FAMILY_CATALOG",)),)),
        stage("RESEARCH_OPERATIONS", inputs=("FAMILY_EVIDENCE_STREAM",), outputs=("RESEARCH_OPERATIONS_EVIDENCE",), deps=(StageDependency("FAMILY_EVIDENCE_STREAM", "REQUIRED", ("FAMILY_EVIDENCE_STREAM",)),)),
    )


def june_requirement_registry(population_id: str) -> AuthorityRequirementRegistry:
    scope = {"population_id": population_id}
    return AuthorityRequirementRegistry((
        AuthorityRequirementSpec(
            "OPT_A_SEALED_REPLAY_READ", "OVC-OPT-A-v2", "A2-G1", "SEALED_REPLAY_READ", "OPT_A_ACCEPTED_RELEASE", required_scope=scope,
        ),
        AuthorityRequirementSpec(
            "C2E_V0_2_REAL_REPLAY", "OVC-C2E-CAUSAL-EPISODE-CONFORMANCE-v0.2", "C2E2-G6-RUN-AUTH", "REAL_REPLAY_EXECUTION", "C2E_V0_2_JUNE_REPLAY", required_scope=scope, require_unconsumed_token=True,
        ),
    ))


def test_synthetic_profile_executes_only_with_explicit_irof_synthetic_authority() -> None:
    source = stage("SYN_SOURCE", kind="SOURCE_BINDING", outputs=("RAW",), authority=("IROF_SYNTHETIC_EXECUTION",))
    profile = PipelineProfile("SYN", "0.1", ("SYN_SOURCE",), ("RAW",))
    snapshot = build_registry_snapshot(stage_specs=(source,), profiles=(profile,))
    plan = build_plan(snapshot=snapshot, profile_id="SYN")
    registry = AuthorityRequirementRegistry((AuthorityRequirementSpec(
        "IROF_SYNTHETIC_EXECUTION", "OVC-IROF-v0.1", "IROF-G0", "SYNTHETIC_EXECUTION", "IROF_SYNTHETIC_POPULATIONS"
    ),))
    allow = binding(
        "B.IROF.SYN", owner_programme="OVC-IROF-v0.1", owner_gate="IROF-G0", authority_kind="SYNTHETIC_EXECUTION", subject="IROF_SYNTHETIC_POPULATIONS", scope={}
    )
    receipt = preflight_plan_authority(plan=plan, stage_specs=(source,), population=synthetic_population(), requirement_registry=registry, bindings=(allow,))
    assert receipt.execution_status == "READY"
    assert receipt.blocked_stage_ids == ()
    assert receipt.token_consumption_performed is False


def test_current_june_full_descriptive_preflight_blocks_at_c2e_and_does_not_union_srfd_token() -> None:
    population = june_population()
    stages = full_descriptive_stages()
    profile = profile_by_id("FULL_DESCRIPTIVE")
    snapshot = build_registry_snapshot(stage_specs=stages, profiles=(profile,))
    plan = build_plan(snapshot=snapshot, profile_id="FULL_DESCRIPTIVE")
    registry = june_requirement_registry(population.population_id)
    scope = {"population_id": population.population_id}
    opt_a = binding(
        "B.OPT_A.REPLAY", owner_programme="OVC-OPT-A-v2", owner_gate="A2-G1", authority_kind="SEALED_REPLAY_READ", subject="OPT_A_ACCEPTED_RELEASE", scope=scope
    )
    c2e_denied = binding(
        "B.C2E.CURRENT.DENIAL", owner_programme="OVC-C2E-CAUSAL-EPISODE-CONFORMANCE-v0.2", owner_gate="C2E2-G6-RUN-AUTH", authority_kind="REAL_REPLAY_EXECUTION", subject="C2E_V0_2_JUNE_REPLAY", scope=scope, decision="NOT_AUTHORISED", status="APPROVED", token_state="INVALIDATED_UNCONSUMED_BY_OPERATOR_SUPERSESSION"
    )
    srfd_v07 = binding(
        "SRFD.JUNE.AUTH.baad8aa9752b789cea06f41c3bc134e86711a257f1219d04b4034a664a8f1ef5",
        owner_programme="OVC-SRFD-BENCHMARK-v0.1", owner_gate="SRFDI-G-JUNE-AUTH", authority_kind="JUNE_BENCHMARK_EXECUTION", subject="SRFDI-WP10-v0.7", scope=scope, token_state="UNCONSUMED"
    )
    receipt = preflight_plan_authority(
        plan=plan,
        stage_specs=stages,
        population=population,
        requirement_registry=registry,
        bindings=(opt_a, c2e_denied, srfd_v07),
        reusable_stage_ids=("POPULATION_SOURCE_OPT_A", "C1", "C2_REVISED"),
    )
    assert receipt.execution_status == "NOT_AUTHORISED"
    assert receipt.blocked_stage_ids == ("C2E_V0_2",)
    assert set(receipt.blocked_descendant_ids) == {"SRI_REPRESENTATION", "COMPARABILITY_COMPARISON_DISTANCE", "FDI_C2G_FAMILY", "FAMILY_EVIDENCE_STREAM", "RESEARCH_OPERATIONS"}
    assert receipt.reusable_ancestor_stage_ids == ("POPULATION_SOURCE_OPT_A", "C1", "C2_REVISED")
    srfd_observation = next(item for item in receipt.owner_authority_observations if item.binding_id.startswith("SRFD.JUNE.AUTH"))
    assert srfd_observation.token_state == "UNCONSUMED"
    assert srfd_observation.used_by_stage_ids == ()
    assert receipt.token_consumption_performed is False
    assert receipt.synthetic_substitution_applied is False
    assert receipt.profile_degraded is False


def test_scope_fragments_from_multiple_bindings_never_union() -> None:
    requirement = AuthorityRequirementSpec(
        "REQ", "OWNER", "GATE", "RUN", "SUBJECT", required_scope={"population_id": "P", "run_id": "R"}
    )
    left = binding("LEFT", owner_programme="OWNER", owner_gate="GATE", authority_kind="RUN", subject="SUBJECT", scope={"population_id": "P"})
    right = binding("RIGHT", owner_programme="OWNER", owner_gate="GATE", authority_kind="RUN", subject="SUBJECT", scope={"run_id": "R"})
    resolution = resolve_requirement(requirement, (left, right))
    assert resolution.decision == "NOT_AUTHORISED"
    assert "IROF_OWNER_SCOPE_MISMATCH" in resolution.reason_codes


def test_real_source_without_declared_authority_requirement_fails_without_synthetic_substitution() -> None:
    source = stage("REAL_SOURCE", kind="SOURCE_BINDING", outputs=("RAW",))
    profile = PipelineProfile("REAL", "0.1", ("REAL_SOURCE",), ("RAW",))
    plan = build_plan(snapshot=build_registry_snapshot(stage_specs=(source,), profiles=(profile,)), profile_id="REAL")
    receipt = preflight_plan_authority(
        plan=plan,
        stage_specs=(source,),
        population=june_population(),
        requirement_registry=AuthorityRequirementRegistry(()),
        bindings=(),
    )
    assert receipt.execution_status == "NOT_AUTHORISED"
    assert receipt.blocked_stage_ids == ("REAL_SOURCE",)
    assert receipt.stage_receipts[0].reason_codes == ("IROF_REAL_SOURCE_AUTHORITY_REQUIREMENT_MISSING",)
    assert receipt.synthetic_substitution_applied is False
