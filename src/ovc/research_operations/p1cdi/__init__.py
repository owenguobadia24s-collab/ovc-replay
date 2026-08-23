"""P1CDI advisory, non-decision-bearing conformance primitives.

P1CDII-G2-ALG qualifies the exact resolver mechanics but does not grant operational
publication. WP3 bootstrap is historical-only. WP4/G4 qualifies deterministic
identity/evidence/correspondence. WP5 adds activity/currentness, demand, one-way RCCR
referral and explicitly non-actuating NEXT_DISCOVERY_WORK machinery. This package
grants no owner-scientific, candidate, Validation, operational-read, intake-write or
actuation authority.
"""

from .bootstrap import (
    build_historical_membership_events,
    freeze_source_census,
    reconcile_source_census,
    scan_repository_source_subjects,
)
from .currentness import evaluate_two_point_currentness, require_g2_alg_for_pointer
from .demand import (
    assess_demand_eligibility,
    assert_non_actuating,
    build_discovery_demand,
    build_discovery_work_recommendation,
    build_gap_demand,
    build_non_actuation_proof,
    build_rccr_referral,
    build_stack_sufficiency_binding,
    validate_one_way_rccr_return,
)
from .identity import build_semantic_projection, exact_semantic_equal, projection_bytes
from .intake import build_intake_envelope, classify_exact_intake
from .lifecycle import (
    build_lifecycle_event,
    project_inventory_activity,
    validate_lifecycle_event,
)
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
    "assess_demand_eligibility",
    "assert_non_actuating",
    "build_discovery_demand",
    "build_discovery_work_recommendation",
    "build_gap_demand",
    "build_intake_envelope",
    "build_historical_membership_events",
    "build_lifecycle_event",
    "build_non_actuation_proof",
    "build_rccr_referral",
    "build_semantic_projection",
    "build_source_frontier",
    "build_stack_sufficiency_binding",
    "classify_exact_intake",
    "assemble_evidence_reference",
    "assign_series_generation",
    "build_correspondence_plane_evidence",
    "evaluate_two_point_currentness",
    "exact_semantic_equal",
    "projection_bytes",
    "freeze_source_census",
    "project_inventory_activity",
    "reconcile_source_census",
    "replay_as_of",
    "resolve_dmrp_independence",
    "require_g2_alg_for_pointer",
    "resolve_owner_predicate",
    "scan_repository_source_subjects",
    "stage_correspondence",
    "validate_lifecycle_event",
    "validate_one_way_rccr_return",
]
