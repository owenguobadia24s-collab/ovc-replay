"""OPT-B Empirical Structural Language common contracts (ESLI-WP1).

Inactive deterministic conformance-only namespace. This package grants no active market
or selector authority, no canonical representation or family promotion, no semantic-promotion,
no Validation consumption, and no probability, risk, exposure, execution authority, or
agent-write authority. It fails closed at the ratified ESL boundary.
"""

from .model import (
    ComparabilityDomain,
    DependencyRef,
    DependencyRole,
    EvidenceFrontier,
    EvidenceState,
    ExecutionProfile,
    GenerationCorrespondence,
    OccurrenceAnchor,
    OccurrencePack,
    StructuralDimension,
    StructuralFacet,
    StructuralOccurrenceRecord,
)
from .validators import ESLValidationError, validate_occurrence

__all__ = [
    "ComparabilityDomain",
    "DependencyRef",
    "DependencyRole",
    "EvidenceFrontier",
    "EvidenceState",
    "ExecutionProfile",
    "GenerationCorrespondence",
    "OccurrenceAnchor",
    "OccurrencePack",
    "StructuralDimension",
    "StructuralFacet",
    "StructuralOccurrenceRecord",
    "ESLValidationError",
    "validate_occurrence",
]
