from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ovc.opt_b.c2_vnext import owner_read_surface as owner
from ovc.research_operations.rrscg.irof import (
    RRSCGOwnerStageAdapter,
    RRSCGIROFError,
    adapt_owner_snapshot,
    build_rrscg_run_spec,
    rrscg_authority_bindings,
    rrscg_authority_registry,
    rrscg_pipeline_profile,
    rrscg_stage_specs,
)
from ovc.research_orchestration.authority import preflight_plan_authority
from ovc.research_orchestration.checkpoint import (
    StageCompletion,
    assert_fresh_resume_equivalent,
    build_resume_plan,
)
from ovc.research_orchestration.models import PopulationSpec, StageInvocation
from ovc.research_orchestration.planner import build_plan
from ovc.research_orchestration.registry import build_registry_snapshot

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schemas/research_operations/rrscg_owner_input_v0_1.schema.json"
REGISTRY = ROOT / "registries/research_operations/rrscg/RRSCG_IROF_STAGE_PACK_v0_1.json"


def _source_binding():
    return {
        "schema": owner.SOURCE_BINDING_SCHEMA,
        "source_binding_id": "RRSCG-SYNTH-BINDING",
        "source_authority_ref": "RRSCG_SYNTHETIC_CONFORMANCE_ONLY",
        "provider": "SYNTHETIC_FIXTURE",
        "instrument": "GBPUSD",
        "side": "BID",
        "local_clock": "15M",
        "parent_clock": "2H_A_L",
        "partition_id": "SYNTH-P0",
        "context_start_utc": "2026-01-01T00:00:00Z",
        "context_end_exclusive_utc": "2026-01-03T00:00:00Z",
        "target_start_utc": "2026-01-01T00:00:00Z",
        "target_end_exclusive_utc": "2026-01-02T00:00:00Z",
        "source_slice_id": "SYNTH-SLICE",
        "source_manifest_sha256": "1" * 64,
        "opt_a_release_id": "SYNTH-OPT-A",
        "opt_a_manifest_id": "SYNTH-OPT-A-MANIFEST",
        "opt_a_manifest_sha256": "2" * 64,
        "c1_release_id": "SYNTH-C1",
        "c1_manifest_id": "SYNTH-C1-MANIFEST",
        "source_object_ids": ["SYNTH-ROW-1"],
    }


def _snapshot():
    body = {
        "schema": owner.SNAPSHOT_SCHEMA,
        "handoff_id": owner.HANDOFF_ID,
        "owner_authority_id": owner.OWNER_AUTHORITY_ID,
        "owner_generation_id": owner.OWNER_GENERATION_ID,
        "owner_package_id": owner.OWNER_PACKAGE_ID,
        "owner_package_sha256": owner.OWNER_PACKAGE_SHA256,
        "source_binding": _source_binding(),
        "instrument": "GBPUSD",
        "side": "BID",
        "clocks": {"local": "15M", "parent": "2H_A_L"},
        "observation_id": "OBS-SYNTH-1",
        "interval_start": "2026-01-01T00:00:00Z",
        "interval_end": "2026-01-01T00:15:00Z",
        "effective_time": "2026-01-01T00:15:00Z",
        "first_valid_time": "2026-01-01T00:15:00Z",
        "target_eligible": True,
        "continuity": {"status": "SEGMENT_START"},
        "projection_eligibility": {"status": "WARM_UP_INSUFFICIENT"},
        "component_refs": {
            "horizon_membership_ids": [],
            "level_ids": [],
            "container_ids": [],
            "relation_set_ids": [],
            "profile_output_ids": {},
            "context_bundle_id": None,
            "fixed_parent_observation_id": None,
        },
        "owner_records": {
            "observation": {"observation_id": "OBS-SYNTH-1"},
            "horizon_memberships": [],
            "levels": [],
            "containers": [],
            "relations": [],
            "relation_sets": [],
            "formula_profiles": {},
            "parent_context": None,
            "transitions": [],
            "computability": [],
        },
        "component_availability": {
            "observation": "PRESENT",
            "horizon": "TYPED_ABSTENTION",
            "level": "TYPED_ABSTENTION",
            "container": "TYPED_ABSTENTION",
            "relation": "TYPED_ABSTENTION",
            "formula": "TYPED_ABSTENTION",
            "parent_context": "TYPED_ABSTENTION",
            "transition": "NOT_EMITTED_BY_BOUND_OWNER_MATERIALISATION",
            "computability": "NOT_EMITTED_BY_BOUND_OWNER_MATERIALISATION",
        },
        "authority": {
            "read_only": True,
            "owner_state_write": "DENIED",
            "new_source_authority": "DENIED",
            "validation": "LOCKED_UNCONSUMED",
            "publication": "NONE",
            "probability_risk_exposure_execution": "NONE",
            "agent_write": "NONE",
        },
    }
    return {**body, "snapshot_id": owner.canonical_sha256(body)}


def _population(**overrides):
    values = {
        "population_id": "RRSCG-SYNTH-P0",
        "population_mode": "SYNTHETIC_FIXTURE",
        "population_schema_version": "0.1",
        "instrument": "GBPUSD",
        "price_side": "BID",
        "clock_lattice": "15M",
        "role": "DEVELOPMENT",
        "source_adapter_id": "RRSCG.C2.OWNER.STRUCTURAL.SNAPSHOT.ADAPTER.v0.1",
        "validation_access_state": "LOCKED_UNCONSUMED",
        "capacity_tier": "MICRO",
        "synthetic_fixture_id": "RRSCG-SYNTH-FIXTURE-v0.1",
        "authority_binding_ids": tuple(item.binding_id for item in rrscg_authority_bindings()),
    }
    values.update(overrides)
    return PopulationSpec(**values)


def test_owner_adapter_preserves_exact_nested_owner_truth_and_missingness():
    snapshot = _snapshot()
    before = copy.deepcopy(snapshot)
    adapted = adapt_owner_snapshot(snapshot).to_dict()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(adapted)
    assert snapshot == before
    assert adapted["owner_snapshot"] == snapshot
    assert adapted["snapshot_id"] == snapshot["snapshot_id"]
    assert adapted["flattening"] == "NONE_OWNER_RECORDS_PRESERVED"
    assert adapted["owner_snapshot"]["component_availability"]["horizon"] == "TYPED_ABSTENTION"
    assert "probability" not in adapted


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ({"owner_generation_id": "FORGED"}, "BINDING_MISMATCH"),
        ({"first_valid_time": "2026-01-01T00:00:00Z"}, "FVT_MISMATCH"),
        ({"side": "MID"}, "SIDE_DENIED"),
    ],
)
def test_owner_adapter_fails_closed_on_owner_or_scope_drift(mutation, reason):
    snapshot = _snapshot()
    snapshot.update(mutation)
    with pytest.raises(RRSCGIROFError, match=reason):
        adapt_owner_snapshot(snapshot)


def test_owner_adapter_rejects_content_identity_tamper():
    snapshot = _snapshot()
    snapshot["continuity"] = {"status": "GAP_RESET"}
    with pytest.raises(RRSCGIROFError, match="SNAPSHOT_ID_MISMATCH"):
        adapt_owner_snapshot(snapshot)


def test_rrscg_stage_pack_forms_deterministic_existing_irof_dag():
    stages = rrscg_stage_specs()
    profile = rrscg_pipeline_profile()
    registry = build_registry_snapshot(stage_specs=reversed(stages), profiles=(profile,))
    plan = build_plan(
        snapshot=registry,
        profile_id=profile.profile_id,
        external_input_types=("C2_OWNER_STRUCTURAL_SNAPSHOT_READ_V0_1",),
    )
    assert plan.ordered_stage_ids == (
        "RRSCG_C2_OWNER_ADAPTER",
        "RRSCG_R2_KERNEL",
        "RRSCG_D9_OBSERVER",
        "RRSCG_D10_REDUCER",
    )
    assert all(stage.deterministic_mode == "EXACT" for stage in stages)
    assert all(stage.checkpoint_capability == "STAGE" for stage in stages)
    assert profile.required_terminal_outputs == (
        "RRSCG_D9_OBSERVER_STATE_V0_1",
        "RRSCG_D10_REDUCER_RECORD_V0_1",
    )
    registered = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert {item["stage_id"]: item["logical_hash"] for item in registered["stage_specs"]} == {
        stage.stage_id: stage.logical_hash for stage in stages
    }
    assert registered["profile"]["logical_hash"] == profile.logical_hash
    assert registered["execution_backend"] == "EXISTING_IROF_PYTHON_IN_PROCESS"


def test_population_profile_and_authority_bindings_preflight_ready_without_token_consumption():
    run = build_rrscg_run_spec(_population())
    snapshot = build_registry_snapshot(stage_specs=run.stage_specs, profiles=(run.profile,))
    plan = build_plan(
        snapshot=snapshot,
        profile_id=run.profile.profile_id,
        external_input_types=("C2_OWNER_STRUCTURAL_SNAPSHOT_READ_V0_1",),
    )
    receipt = preflight_plan_authority(
        plan=plan,
        stage_specs=run.stage_specs,
        population=run.population,
        requirement_registry=rrscg_authority_registry(),
        bindings=run.authority_bindings,
    )
    assert receipt.execution_status == "READY"
    assert receipt.blocked_stage_ids == ()
    assert receipt.token_consumption_performed is False
    assert run.population.validation_access_state == "LOCKED_UNCONSUMED"
    assert set(run.pack_bindings) == {"RRSCG_R2", "RRSCG_D9", "RRSCG_D10"}


def test_real_source_and_validation_remain_denied():
    with pytest.raises(RRSCGIROFError, match="REAL_SOURCE_RUN_NOT_AUTHORISED"):
        build_rrscg_run_spec(
            _population(
                population_mode="SEALED_REAL_REPLAY",
                source_release_id="REAL",
                source_manifest_hash="3" * 64,
                synthetic_fixture_id=None,
            )
        )
    with pytest.raises(RRSCGIROFError, match="VALIDATION_CONSUMPTION_DENIED"):
        build_rrscg_run_spec(_population(role="VALIDATION"))


def test_owner_stage_resume_reproduces_exact_content_identity():
    stage = rrscg_stage_specs()[0]
    invocation = StageInvocation(stage.stage_id, stage.logical_hash)
    adapter = RRSCGOwnerStageAdapter()
    envelope = {"population_mode": "SYNTHETIC_FIXTURE", "owner_snapshot": _snapshot()}
    fresh = adapter.execute(stage, invocation, envelope)
    repeated = adapter.execute(stage, invocation, envelope)
    resumed = adapter.resume(stage, invocation, envelope, "CHECKPOINT.1")
    assert fresh.output_refs == repeated.output_refs == resumed.output_refs
    assert fresh.scientific_payload_hash == repeated.scientific_payload_hash == resumed.scientific_payload_hash
    assert resumed.checkpoint_ref == "CHECKPOINT.1"
    assert adapter.verify(stage, invocation, resumed).valid is True
    assert_fresh_resume_equivalent(fresh.output_refs[0], repeated.output_refs[0], resumed.output_refs[0])


def test_existing_checkpoint_planner_reuses_verified_prefix_and_reruns_descendants_on_drift():
    stages = rrscg_stage_specs()
    profile = rrscg_pipeline_profile()
    plan = build_plan(
        snapshot=build_registry_snapshot(stage_specs=stages, profiles=(profile,)),
        profile_id=profile.profile_id,
        external_input_types=("C2_OWNER_STRUCTURAL_SNAPSHOT_READ_V0_1",),
    )
    completions = tuple(
        StageCompletion(stage.stage_id, stage.logical_hash, f"logical-{stage.stage_id}", f"content-{stage.stage_id}", "ATTEMPT.1")
        for stage in stages
    )
    expected = {stage.stage_id: stage.logical_hash for stage in stages}
    observed = {stage.stage_id: f"content-{stage.stage_id}" for stage in stages}
    resume = build_resume_plan(
        plan=plan,
        semantic_run_id="IROF.RUN.RRSCG",
        completions=completions,
        expected_stage_spec_hashes=expected,
        observed_content_hashes=observed,
        new_attempt_id="ATTEMPT.2",
    )
    assert resume.rerun_stage_ids == ()
    assert resume.reusable_completed_stage_ids == plan.ordered_stage_ids

    observed["RRSCG_D9_OBSERVER"] = "tampered"
    drift = build_resume_plan(
        plan=plan,
        semantic_run_id="IROF.RUN.RRSCG",
        completions=completions,
        expected_stage_spec_hashes=expected,
        observed_content_hashes=observed,
        new_attempt_id="ATTEMPT.3",
    )
    assert drift.reusable_completed_stage_ids == ("RRSCG_C2_OWNER_ADAPTER", "RRSCG_R2_KERNEL")
    assert drift.rerun_stage_ids == ("RRSCG_D9_OBSERVER", "RRSCG_D10_REDUCER")
