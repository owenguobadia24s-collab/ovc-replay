"""P1CDI advisory, non-decision-bearing conformance primitives.

P1CDII-G2-ALG qualifies the exact resolver mechanics but does not grant operational
publication. WP3 bootstrap is historical-only. WP4/G4 qualifies deterministic
identity/evidence/correspondence. WP5 adds activity/currentness, demand, one-way RCCR
referral and explicitly non-actuating NEXT_DISCOVERY_WORK machinery. WP6 adds
candidate ancestry and mechanical-readiness projections behind a hard DMRP candidate,
freeze and C-admission firewall. WP7 adds pre-index visibility classification,
cross-mode/protected-source filtering and Validation negative reachability. WP8 adds
rebuildable optimized indexes with reference equivalence and measured capacity. WP9
adds typed read-only query/consumer projections without consumer admission or
operational reliance. This package grants no owner-scientific, candidate, Validation,
operational-read, intake-write or actuation authority.
"""

from .bootstrap import (
    build_historical_membership_events,
    freeze_source_census,
    reconcile_source_census,
    scan_repository_source_subjects,
)
from .candidate_firewall import (
    assert_candidate_firewall,
    assert_no_outcome_repair,
    bind_source_disposition,
    build_candidate_derivation_manifest,
    build_proposal_readiness_assessment,
    preserve_frozen_candidate,
    project_freeze_disposition,
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
from .projections import (
    P1CDIProjectionError,
    build_console_projection,
    build_source_admission_packet,
)
from .query import P1CDIQueryError, P1CDIReadOnlyQueryService, QUERY_FAMILIES
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
from .visibility import (
    LEAK_SURFACES,
    PATH1_SAFE_REDACTED_FIELDS,
    VISIBILITY_CLASSES,
    build_visibility_decision,
    build_visibility_safe_index_entry,
    deny_validation_before_resolution,
    project_independence_state,
    project_visible_record,
    validate_visibility_decision,
)

__all__ = [
    "CONFORMANCE_SEPARATION_PRINCIPLE",
    "LEAK_SURFACES",
    "P1CDIProjectionError",
    "P1CDIQueryError",
    "P1CDIReadOnlyQueryService",
    "PATH1_SAFE_REDACTED_FIELDS",
    "QUERY_FAMILIES",
    "VISIBILITY_CLASSES",
    "assess_demand_eligibility",
    "assert_candidate_firewall",
    "assert_no_outcome_repair",
    "assert_non_actuating",
    "bind_source_disposition",
    "build_candidate_derivation_manifest",
    "build_console_projection",
    "build_discovery_demand",
    "build_discovery_work_recommendation",
    "build_gap_demand",
    "build_intake_envelope",
    "build_historical_membership_events",
    "build_lifecycle_event",
    "build_non_actuation_proof",
    "build_proposal_readiness_assessment",
    "build_rccr_referral",
    "build_semantic_projection",
    "build_source_admission_packet",
    "build_source_frontier",
    "build_stack_sufficiency_binding",
    "build_visibility_decision",
    "build_visibility_safe_index_entry",
    "classify_exact_intake",
    "assemble_evidence_reference",
    "assign_series_generation",
    "build_correspondence_plane_evidence",
    "deny_validation_before_resolution",
    "evaluate_two_point_currentness",
    "exact_semantic_equal",
    "projection_bytes",
    "freeze_source_census",
    "preserve_frozen_candidate",
    "project_freeze_disposition",
    "project_independence_state",
    "project_inventory_activity",
    "project_visible_record",
    "reconcile_source_census",
    "replay_as_of",
    "resolve_dmrp_independence",
    "require_g2_alg_for_pointer",
    "resolve_owner_predicate",
    "scan_repository_source_subjects",
    "stage_correspondence",
    "validate_lifecycle_event",
    "validate_one_way_rccr_return",
    "validate_visibility_decision",
]
