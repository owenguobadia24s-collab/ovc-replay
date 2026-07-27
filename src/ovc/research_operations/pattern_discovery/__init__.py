"""Derived C2 Pattern Discovery transition, trigger and triage services.

PD-WP1 provides the accepted transition and CandidateWindow foundation. PD-WP2
adds deterministic trigger evaluation, controls, backpressure and non-authoritative
novelty shadow. No live processing, active novelty ranking, evidence-write,
selector, release, clustering, probability, exposure, trading, execution or agent
authority is granted.
"""

from .backpressure import LatencyObservation, QueuePolicy, degradation_states, project_review_queue
from .controls import (
    ControlSamplingPack,
    assess_control_representation,
    required_control_counts,
    select_matched_control,
    select_population_control,
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
from .transitions import EXTRACTOR_VERSION, extract_transitions
from .triggers import PRECEDENCE, build_trigger_event, mark_display_primary
from .windows import CandidateWindowManager

__all__ = [
    "AXES",
    "C2Snapshot",
    "ChronologyError",
    "DuplicateDerivedRecordError",
    "PatternDiscoveryError",
    "SourceBindingError",
    "AppendOnlyJsonlStore",
    "PatternDiscoveryEventLedger",
    "EXTRACTOR_VERSION",
    "extract_transitions",
    "PRECEDENCE",
    "build_trigger_event",
    "mark_display_primary",
    "CandidateWindowManager",
    "PatternDiscoveryEngine",
    "EVALUATOR_VERSION",
    "TriggerEvaluation",
    "evaluate_transition_triggers",
    "evaluate_cross_scale_triggers",
    "evaluate_persistence_trigger",
    "evaluate_switching_trigger",
    "materialize_fired_events",
    "ControlSamplingPack",
    "select_population_control",
    "select_matched_control",
    "required_control_counts",
    "assess_control_representation",
    "NoveltyBaseline",
    "canonical_signature",
    "jaccard_distance",
    "QueuePolicy",
    "LatencyObservation",
    "project_review_queue",
    "degradation_states",
]
