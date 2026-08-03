"""Governance-only Programme Genesis ledger, graph and projection utilities.

This namespace has no market, model, selector, publication, Validation,
agent-write, probability, risk, exposure, trading, or execution authority.
"""

from .graph import GraphValidationError, impact_analysis, validate_graph
from .ledger import AppendOnlyLedger, LedgerError, canonical_event_bytes, event_digest
from .projection import ProjectionError, build_partitioned_projection, project_programme
from .synchronisation import SynchronisationFinding, compare_programme_state

__all__ = [
    "AppendOnlyLedger",
    "GraphValidationError",
    "LedgerError",
    "ProjectionError",
    "SynchronisationFinding",
    "build_partitioned_projection",
    "canonical_event_bytes",
    "compare_programme_state",
    "event_digest",
    "impact_analysis",
    "project_programme",
    "validate_graph",
]
