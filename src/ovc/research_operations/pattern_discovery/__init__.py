"""Derived C2 Pattern Discovery services.

PD-WP1 provides transitions and CandidateWindows. PD-WP2 adds deterministic
trigger evaluation, controls, backpressure and non-authoritative novelty shadow.
PD-WP3 adds deterministic fingerprints, composite distance and provisional PAM
clusters. PD-WP4 adds typed review projections, an exact-source price strip and
a fail-closed local evidence-bridge candidate. Canonical evidence-write authority
remains disabled pending PD-G4 operator approval.
"""

from .backpressure import LatencyObservation, QueuePolicy, degradation_states, project_review_queue
from .bridge import AppendRequest, EvidenceBridgeError, LocalEvidenceBridge, OperatorSigner, SourceResolver
from .clustering import (
    ALGORITHM_VERSION,
    MAX_ACTIVE_PARTITION,
    build_cluster_versions,
    build_partition_cluster_version,
    deterministic_pam,
    eligible_clustering_population,
    map_cluster_lineage,
)
from .controls import (
    ControlSamplingPack,
    assess_control_representation,
    required_control_counts,
    select_matched_control,
    select_population_control,
)
from .distance import (
    DISTANCE_VERSION,
    DistancePack,
    ScalePack,
    build_scale_pack,
    composite_distance,
    normalized_levenshtein,
)
from .engine import PatternDiscoveryEngine
from .evaluation import (
    EVALUATOR_VERSION,
    TriggerEvaluation,
    evaluate_cross_scale_triggers,
    evaluate_persistence_trigger,
    evaluate_switching_trigger,
    evaluate_transition_triggers,
    materialize_fired_events,
)
from .fingerprints import FINGERPRINT_VERSION, build_pattern_fingerprint, partition_key
from .models import (
    AXES,
    C2Snapshot,
    ChronologyError,
    DuplicateDerivedRecordError,
    PatternDiscoveryError,
    SourceBindingError,
)
from .novelty import NoveltyBaseline, canonical_signature, jaccard_distance
from .persistence import AppendOnlyJsonlStore, PatternDiscoveryEventLedger
from .price_strip import build_price_strip
from .review import EVIDENCE_CLASSES, build_candidate_detail, build_cluster_view, build_review_queue_item
from .transitions import EXTRACTOR_VERSION, extract_transitions
from .triggers import PRECEDENCE, build_trigger_event, mark_display_primary
from .windows import CandidateWindowManager

__all__ = [
    "AXES", "C2Snapshot", "ChronologyError", "DuplicateDerivedRecordError",
    "PatternDiscoveryError", "SourceBindingError", "AppendOnlyJsonlStore",
    "PatternDiscoveryEventLedger", "EXTRACTOR_VERSION", "extract_transitions",
    "PRECEDENCE", "build_trigger_event", "mark_display_primary",
    "CandidateWindowManager", "PatternDiscoveryEngine", "EVALUATOR_VERSION",
    "TriggerEvaluation", "evaluate_transition_triggers", "evaluate_cross_scale_triggers",
    "evaluate_persistence_trigger", "evaluate_switching_trigger", "materialize_fired_events",
    "ControlSamplingPack", "select_population_control", "select_matched_control",
    "required_control_counts", "assess_control_representation", "NoveltyBaseline",
    "canonical_signature", "jaccard_distance", "QueuePolicy", "LatencyObservation",
    "project_review_queue", "degradation_states", "FINGERPRINT_VERSION",
    "build_pattern_fingerprint", "partition_key", "DISTANCE_VERSION", "DistancePack",
    "ScalePack", "build_scale_pack", "composite_distance", "normalized_levenshtein",
    "ALGORITHM_VERSION", "MAX_ACTIVE_PARTITION", "eligible_clustering_population",
    "deterministic_pam", "build_partition_cluster_version", "build_cluster_versions",
    "map_cluster_lineage", "EVIDENCE_CLASSES", "build_review_queue_item",
    "build_candidate_detail", "build_cluster_view", "build_price_strip", "AppendRequest",
    "EvidenceBridgeError", "OperatorSigner", "SourceResolver", "LocalEvidenceBridge",
]
