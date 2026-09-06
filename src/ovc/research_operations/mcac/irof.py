from __future__ import annotations

from ovc.research_orchestration.authority import AuthorityRequirementRegistry, AuthorityRequirementSpec
from ovc.research_orchestration.models import PipelineProfile, StageDependency, StageSpec

MCAC_INACTIVE_REQUIREMENT = "AUTH.LSIAC.MCAC.INACTIVE.CONFORMANCE.v0.1"
MCAC_OWNER_READ_REQUIREMENT = "AUTH.OPT-B.C2.vNext.OWNER_STRUCTURAL_SNAPSHOT.READ.v0.1"
SOURCE_USE_CLASSES = frozenset({
    "SYNTHETIC_CONFORMANCE", "SEALED_CONSUMED_REFERENCE", "OWNER_PUBLISHED_DERIVED_RECORDS",
    "LOCATOR_ONLY", "UNAVAILABLE_CONTEXT", "FORBIDDEN",
})


def preflight_source_use(source_use_class: str, *, reference_authority_effective: bool = False, owner_authority_effective: bool = False) -> str:
    if source_use_class not in SOURCE_USE_CLASSES:
        return "NOT_AUTHORISED"
    if source_use_class == "SYNTHETIC_CONFORMANCE":
        return "READY"
    if source_use_class == "SEALED_CONSUMED_REFERENCE":
        return "READY" if reference_authority_effective else "NOT_AUTHORISED"
    if source_use_class == "OWNER_PUBLISHED_DERIVED_RECORDS":
        return "READY" if owner_authority_effective else "NOT_AUTHORISED"
    return "NOT_AUTHORISED"


def mcac_stage_specs() -> tuple[StageSpec, ...]:
    align = StageSpec(
        stage_id="MCAC_ALIGNMENT", stage_version="0.1", stage_kind="INACTIVE_CAUSAL_ALIGNMENT",
        implementation_identity="ovc.research_operations.mcac.alignment:align",
        contract_identity="OVC.MCAC.ALIGNMENT.v0.1", schema_identity="MCAC_COMPARISON_RESULT_v0.1",
        input_types=("MCAC_COMPARABILITY_CONTEXT_v0.1", "MCAC_CLOCK_INDEXED_OCCURRENCE_REF_v0.1"),
        output_types=("MCAC_ALIGNMENT_RESULT_v0.1",), authority_requirements=(MCAC_INACTIVE_REQUIREMENT,),
        deterministic_mode="EXACT", checkpoint_capability="STAGE", cache_capability="SEMANTIC",
        qa_requirements=("FVT_SAFE", "CLOCK_EXPLICIT", "DOCTRINE_BOUND"), adapter_identity="MCAC.IROF.ALIGNMENT.v0.1",
    )
    correspondence = StageSpec(
        stage_id="MCAC_CORRESPONDENCE", stage_version="0.1", stage_kind="INACTIVE_TYPED_CORRESPONDENCE",
        implementation_identity="ovc.research_operations.mcac.correspondence:correspond",
        contract_identity="OVC.MCAC.CORRESPONDENCE.v0.1", schema_identity="MCAC_COMPARISON_RESULT_v0.1",
        input_types=("MCAC_ALIGNMENT_RESULT_v0.1", "MCAC_CORRESPONDENCE_RULE_v0.1"),
        output_types=("MCAC_CORRESPONDENCE_RESULT_v0.1",),
        dependencies=(StageDependency("MCAC_ALIGNMENT", "REQUIRED", ("MCAC_ALIGNMENT_RESULT_v0.1",)),),
        authority_requirements=(MCAC_INACTIVE_REQUIREMENT,), deterministic_mode="EXACT",
        checkpoint_capability="STAGE", cache_capability="SEMANTIC",
        qa_requirements=("GLOBAL_FINALISATION", "IDENTITY_EFFECT_NONE", "COMPOSITION_EFFECT_NONE"),
        adapter_identity="MCAC.IROF.CORRESPONDENCE.v0.1",
    )
    return align, correspondence


def mcac_pipeline_profile() -> PipelineProfile:
    return PipelineProfile(
        profile_id="MCAC.INACTIVE.CONFORMANCE.v0.1", profile_version="0.1",
        included_stage_ids=tuple(stage.stage_id for stage in mcac_stage_specs()),
        required_terminal_outputs=("MCAC_CORRESPONDENCE_RESULT_v0.1",),
        prerequisites=("RRSCG_CORE_COMPLETE_REPOSITORY_EFFECTIVE", "MCAC-G0:PASS"),
        authority_policy_ref="MCAC_EXISTING_OWNER_OR_SYNTHETIC_AUTHORITY_ONLY",
        observability_requirements=("COMPLETE_CLOCK_COORDINATES", "MAX_DEPENDENCY_FVT", "DOCTRINE_HASH", "SOURCE_USE_CLASS"),
    )


def mcac_authority_registry() -> AuthorityRequirementRegistry:
    return AuthorityRequirementRegistry((
        AuthorityRequirementSpec(MCAC_INACTIVE_REQUIREMENT, "OVC-LSIAC-v0.1", "MCAC-G0", "INACTIVE_CAPABILITY_CONSTRUCTION", "OVC.MCAC.INACTIVE.DESCRIPTIVE.UTILITY.v0.1", required_scope={"capability_state": "INACTIVE", "validation": "LOCKED_UNCONSUMED"}),
        AuthorityRequirementSpec(MCAC_OWNER_READ_REQUIREMENT, "OVC-ACTIVE-STACK-RECLASSIFICATION-v0.1", "C2-OWNER-READ-HANDOFF-G1", "CURRENT_OWNER_STRUCTURAL_SNAPSHOT_READ", "C2VNEXT.OWNER.GENERATION.ASR00.C2AR-PACKAGE-v1.READ-v0.1", required_scope={"instrument": "GBPUSD", "local_clock": "15M", "parent_clock": "2H_A_L"}),
    ))
