"""P1CDI advisory, non-decision-bearing conformance primitives.

P1CDII-G2-ALG qualifies the exact resolver mechanics but does not grant operational
publication. WP3 bootstrap is historical-only. This package grants no owner-scientific,
candidate, Validation, or actuation authority.
"""

from .bootstrap import (
    build_historical_membership_events,
    freeze_source_census,
    reconcile_source_census,
    scan_repository_source_subjects,
)
from .currentness import evaluate_two_point_currentness, require_g2_alg_for_pointer
from .identity import build_semantic_projection, exact_semantic_equal, projection_bytes
from .intake import build_intake_envelope, classify_exact_intake
from . import reference as _reference
from .series_root_guard import install_reference_series_root_guard

install_reference_series_root_guard(_reference)

from .reference import (
    CONFORMANCE_SEPARATION_PRINCIPLE,
    assemble_evidence_reference,
    assign_series_generation,
    build_correspondence_plane_evidence,
    replay_as_of,
    resolve_dmrp_independence,
    stage_correspondence,
)
from .source_resolution import build_source_frontier, resolve_owner_predicate

__all__ = [
    "CONFORMANCE_SEPARATION_PRINCIPLE",
    "build_intake_envelope",
    "build_historical_membership_events",
    "build_semantic_projection",
    "build_source_frontier",
    "classify_exact_intake",
    "assemble_evidence_reference",
    "assign_series_generation",
    "build_correspondence_plane_evidence",
    "evaluate_two_point_currentness",
    "exact_semantic_equal",
    "projection_bytes",
    "freeze_source_census",
    "reconcile_source_census",
    "replay_as_of",
    "resolve_dmrp_independence",
    "require_g2_alg_for_pointer",
    "resolve_owner_predicate",
    "scan_repository_source_subjects",
    "stage_correspondence",
]
