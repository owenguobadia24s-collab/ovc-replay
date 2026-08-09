from __future__ import annotations

from ovc.opt_b.sfc.evidence import rate_record
from ovc.research_orchestration.current_adapters import (
    adapter_for_stage,
    assert_exact_owner_output,
    invoke_owner_callable,
    mcarb_adapter_available,
    verify_current_source_bindings,
)
from ovc.research_orchestration.models import StageInvocation, StageSpec
from ovc.research_orchestration.profiles import CURRENT_PROFILES, profile_by_id


def spec(stage_id: str) -> StageSpec:
    return StageSpec(
        stage_id=stage_id,
        stage_version="0.1",
        stage_kind="CURRENT_OWNER_HANDOFF",
        implementation_identity=f"owner:{stage_id}",
        contract_identity=f"contract:{stage_id}",
        schema_identity=f"schema:{stage_id}",
        input_types=(),
        output_types=("OWNER_OUTPUT",),
        adapter_identity=f"IROF.CURRENT.{stage_id}",
    )


def invocation(stage: StageSpec) -> StageInvocation:
    return StageInvocation(stage.stage_id, stage.logical_hash)


def test_current_source_modules_resolve_without_importing_historical_c2_fallback() -> None:
    stages = verify_current_source_bindings()
    assert "C1" in stages
    assert "C2_REVISED" in stages
    assert "C2E_V0_2" in stages
    binding = adapter_for_stage("C2_REVISED").binding
    assert binding.source_modules == ("ovc.opt_b.c2_vnext",)


def test_required_current_profiles_are_registered_and_semantics_neutral() -> None:
    required = {
        "C1_ONLY", "C2_ONLY", "C2_C2E", "STRUCTURAL_CORE", "FAMILY_RESEARCH",
        "FULL_DESCRIPTIVE", "FULL_DESCRIPTIVE_WITH_CONTEXT",
    }
    assert required.issubset({item.profile_id for item in CURRENT_PROFILES})
    assert profile_by_id("FULL_DESCRIPTIVE").included_stage_ids[-1] == "RESEARCH_OPERATIONS"
    assert "OCCURRENCE_CONTEXT" not in profile_by_id("FULL_DESCRIPTIVE").included_stage_ids
    assert "OCCURRENCE_CONTEXT" in profile_by_id("FULL_DESCRIPTIVE_WITH_CONTEXT").included_stage_ids


def test_c2e_current_adapter_allows_synthetic_but_denies_real_execution() -> None:
    stage = spec("C2E_V0_2")
    adapter = adapter_for_stage("C2E_V0_2")
    synthetic = adapter.preflight(stage, invocation(stage), {"population_mode": "SYNTHETIC_FIXTURE"})
    assert synthetic.allowed is True
    real = adapter.preflight(stage, invocation(stage), {"population_mode": "SEALED_REAL_REPLAY"})
    assert real.allowed is False
    assert real.reason_codes == ("IROF_CURRENT_ADAPTER_REAL_EXECUTION_NOT_AUTHORISED",)


def test_occurrence_context_representation_input_is_rejected_by_default() -> None:
    stage = spec("OCCURRENCE_CONTEXT")
    adapter = adapter_for_stage("OCCURRENCE_CONTEXT")
    result = adapter.preflight(
        stage,
        invocation(stage),
        {"population_mode": "SYNTHETIC_FIXTURE", "context_role": "REPRESENTATION_INPUT"},
    )
    assert result.allowed is False
    assert "IROF_OCCURRENCE_CONTEXT_REPRESENTATION_INPUT_NOT_AUTHORISED" in result.reason_codes


def test_opaque_owner_handoff_preserves_output_references_and_hash() -> None:
    stage = spec("C1")
    adapter = adapter_for_stage("C1")
    result = adapter.execute(
        stage,
        invocation(stage),
        {
            "population_mode": "SYNTHETIC_FIXTURE",
            "owner_output_refs": ("C1.OWNER.OUTPUT",),
            "owner_scientific_payload_hash": "owner-hash",
        },
    )
    assert result.output_refs == ("C1.OWNER.OUTPUT",)
    assert result.scientific_payload_hash == "owner-hash"
    assert adapter.verify(stage, invocation(stage), result).valid is True


def test_direct_sfc_owner_callable_output_is_byte_semantically_unchanged_by_invocation() -> None:
    kwargs = {
        "metric_type": "RESIDUAL_RATE_WITH_DENOMINATOR",
        "numerator": 1,
        "denominator": 3,
        "left_scope": "CATALOG",
        "rule_pack_ids": ("OVC-SRFD-STABILITY-METRIC-SPECS-0.4",),
    }
    direct = rate_record(**kwargs)
    through_irof = invoke_owner_callable("ovc.opt_b.sfc.evidence", "rate_record", **kwargs)
    assert direct == through_irof
    assert_exact_owner_output(direct, through_irof)
    assert through_irof["rule_pack_ids"] == ["OVC-SRFD-STABILITY-METRIC-SPECS-0.4"]
    assert through_irof["numerator"] == 1
    assert through_irof["denominator"] == 3
    assert through_irof["status"] == "EVALUATED"


def test_mcarb_extension_is_not_silently_registered() -> None:
    assert mcarb_adapter_available() is False
