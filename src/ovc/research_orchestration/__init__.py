"""Authority-safe, semantics-neutral OVC integrated research orchestration contracts.

IROF is infrastructure only. Importing this package grants no provider, selector,
real-data, Validation, scientific promotion, publication, probability, risk,
exposure, trading, execution or agent-write authority.
"""

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
    "ArtifactRef", "AuthorityBinding", "CapacityBudget", "CapacityReceipt",
    "CheckpointRecord", "IntegratedRunManifest", "IntegratedRunReceipt",
    "PipelineProfile", "PopulationSpec", "ResearchRunSpec", "RestartLedger",
    "RunComparisonRecord", "RunFailure", "SemanticCacheKey", "StageDependency",
    "StageExecutionReceipt", "StageInvocation", "StageSpec",
]
