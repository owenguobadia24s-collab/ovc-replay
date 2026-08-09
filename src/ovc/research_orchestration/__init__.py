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
    "CapacityBudget", "CapacityReceipt", "CheckpointRecord", "IntegratedRunManifest",
    "IntegratedRunReceipt", "PipelineProfile", "PopulationResolutionReceipt",
    "PopulationSpec", "RequirementResolution", "ResearchRunSpec", "RestartLedger",
    "RunComparisonRecord", "RunFailure", "SemanticArtifactCache", "SemanticCacheKey",
    "StageAuthorityReceipt", "StageDependency", "StageExecutionReceipt", "StageInvocation",
    "StageSpec", "assert_cached_recompute_equivalent", "preflight_plan_authority",
    "preflight_population_resolution", "resolve_requirement",
]
