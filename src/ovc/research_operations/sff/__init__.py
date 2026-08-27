"""Structural Future Frontier synthetic/conformance implementation.

This namespace is bounded synthetic research mechanics and conformance only.
It intentionally contains no real-source loader, target activation, semantic
promotion, Validation consumption, OPT-F admission, publication adapter,
probability-as-exposure, risk, trading, execution, agent-write authority, or
mutable model runtime.  Every missing authority or owner dependency fails
closed.
"""

from .core import (
    AuthorityError,
    ChronologyError,
    ResearchFreezeFrontier,
    TargetComplexityBudget,
    TargetGrammarExposureManifest,
    canonical_bytes,
    content_identity,
)
from .owner import OwnerFact, OwnerResolver

__all__ = [
    "AuthorityError",
    "ChronologyError",
    "OwnerFact",
    "OwnerResolver",
    "ResearchFreezeFrontier",
    "TargetComplexityBudget",
    "TargetGrammarExposureManifest",
    "canonical_bytes",
    "content_identity",
]
