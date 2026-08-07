"""Shadow-only market-grammar research namespace.

This package has no active market or selector authority, no canonical grammar,
no Validation or semantic-promotion authority, and no probability, risk,
exposure or execution authority.
"""

from .episode_ledger import (
    BoundaryCause,
    C2LedgerInput,
    ComputabilityStatus,
    EpisodeBinding,
    EpisodeBindingRequest,
    EpisodeLedger,
    EpisodeRecord,
    EpisodeStatus,
    NestingRelation,
    NotEvaluableRecord,
    PhaseKind,
    PhaseRecord,
    build_episode_ledger,
    build_nesting_ledger,
)
from .predicate_domains import (
    ComponentClass,
    ComponentStats,
    ExclusivityRule,
    PredicateDomain,
    classify_component,
    infer_domain,
    migrate_legacy_component,
    validate_exclusivity_rule,
    validate_predicate_domain,
)

__all__ = [
    "BoundaryCause",
    "C2LedgerInput",
    "ComponentClass",
    "ComponentStats",
    "ComputabilityStatus",
    "EpisodeBinding",
    "EpisodeBindingRequest",
    "EpisodeLedger",
    "EpisodeRecord",
    "EpisodeStatus",
    "ExclusivityRule",
    "NestingRelation",
    "NotEvaluableRecord",
    "PhaseKind",
    "PhaseRecord",
    "PredicateDomain",
    "build_episode_ledger",
    "build_nesting_ledger",
    "classify_component",
    "infer_domain",
    "migrate_legacy_component",
    "validate_exclusivity_rule",
    "validate_predicate_domain",
]
