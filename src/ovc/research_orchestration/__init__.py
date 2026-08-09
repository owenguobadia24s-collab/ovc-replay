"""Authority-safe, semantics-neutral OVC integrated research orchestration contracts.

IROF is infrastructure only. Importing this package grants no provider, selector,
real-data, Validation, scientific promotion, publication, probability, risk,
exposure, trading, execution or agent-write authority.
"""

from .authority import (
    AuthorityPreflightReceipt,
    AuthorityRequirementRegistry,
    AuthorityRequirementSpec,
    PopulationResolutionReceipt,
    RequirementResolution,
    StageAuthorityReceipt,
    preflight_plan_authority,
    preflight_population_resolution,
    resolve_requirement,
)
from .cache import CacheLookupReceipt, SemanticArtifactCache, assert_cached_recompute_equivalent
from .checkpoint import (
    CheckpointLedger,
    OpaqueSubstageCheckpoint,
    ResumePlan,
    RunCheckpointManifest,
    StageCompletion,
    assert_fresh_resume_equivalent,
    build_resume_plan,
)
from .models import (
    ArtifactRef,
    AuthorityBinding,
    CapacityBudget,
    CapacityReceipt,
    CheckpointRecord,
    IntegratedRunManifest,
    IntegratedRunReceipt,
    PipelineProfile,
    PopulationSpec,
    ResearchRunSpec,
    RestartLedger,
    RunComparisonRecord,
    RunFailure,
    SemanticCacheKey,
    StageDependency,
    StageExecutionReceipt,
    StageInvocation,
    StageSpec,
)

__all__ = [
    "ArtifactRef", "AuthorityBinding", "AuthorityPreflightReceipt",
    "AuthorityRequirementRegistry", "AuthorityRequirementSpec", "CacheLookupReceipt",
    "CapacityBudget", "CapacityReceipt", "CheckpointLedger", "CheckpointRecord",
    "IntegratedRunManifest", "IntegratedRunReceipt", "OpaqueSubstageCheckpoint",
    "PipelineProfile", "PopulationResolutionReceipt", "PopulationSpec", "RequirementResolution",
    "ResearchRunSpec", "RestartLedger", "ResumePlan", "RunCheckpointManifest",
    "RunComparisonRecord", "RunFailure", "SemanticArtifactCache", "SemanticCacheKey",
    "StageAuthorityReceipt", "StageCompletion", "StageDependency", "StageExecutionReceipt",
    "StageInvocation", "StageSpec", "assert_cached_recompute_equivalent",
    "assert_fresh_resume_equivalent", "build_resume_plan", "preflight_plan_authority",
    "preflight_population_resolution", "resolve_requirement",
]
