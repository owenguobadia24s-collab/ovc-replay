"""Inactive descriptive Research Operations conformance utility.

MCAC creates no clock or source authority, shared state/phase ontology, selector,
Validation access, publication, probability, risk, exposure, trading, execution,
or agent-write authority. It fails closed at owner and IROF boundaries.
"""

from .alignment import AlignmentResult, Relation, align, temporal_containment
from .contracts import (
    ClockCoordinateIdentity,
    ClockIndexedOccurrenceRef,
    ClockRegistryEntry,
    ComparabilityContext,
    MCACContractError,
)
from .correspondence import CandidateEdge, CorrespondenceResult, CorrespondenceRule, correspond

__all__ = [
    "AlignmentResult", "CandidateEdge", "ClockCoordinateIdentity", "ClockIndexedOccurrenceRef",
    "ClockRegistryEntry", "ComparabilityContext", "CorrespondenceResult", "CorrespondenceRule",
    "MCACContractError", "Relation", "align", "correspond", "temporal_containment",
]
