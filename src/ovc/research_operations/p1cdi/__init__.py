"""P1CDI conservative source, identity, intake, and currentness primitives.

WP2 outputs are advisory and non-decision-bearing until P1CDII-G2-ALG passes.
This package grants no owner-scientific, candidate, Validation, or actuation authority.
"""

from .currentness import evaluate_two_point_currentness, require_g2_alg_for_pointer
from .identity import build_semantic_projection, exact_semantic_equal, projection_bytes
from .intake import build_intake_envelope, classify_exact_intake
from .source_resolution import build_source_frontier, resolve_owner_predicate

__all__ = [
    "build_intake_envelope",
    "build_semantic_projection",
    "build_source_frontier",
    "classify_exact_intake",
    "evaluate_two_point_currentness",
    "exact_semantic_equal",
    "projection_bytes",
    "require_g2_alg_for_pointer",
    "resolve_owner_predicate",
]
