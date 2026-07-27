"""Derived C2 Pattern Discovery transition and candidate-window services.

PD-WP1 provides fixture and approved read-only C2 computation only. It grants
no live prospective processing, evidence-write, selector, release, clustering,
probability, exposure, trading, execution or agent authority.
"""

from .engine import PatternDiscoveryEngine
from .models import (
    AXES,
    C2Snapshot,
    ChronologyError,
    DuplicateDerivedRecordError,
    PatternDiscoveryError,
    SourceBindingError,
)
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
]
