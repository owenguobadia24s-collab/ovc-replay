"""Structural Future Frontier synthetic/conformance implementation.

This namespace is mechanics-only.  It intentionally contains no real-source
loader, publication adapter, exposure surface, or mutable model runtime.
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
