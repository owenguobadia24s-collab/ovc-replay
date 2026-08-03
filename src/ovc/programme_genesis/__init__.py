"""Governance-only Programme Genesis ledger and projection utilities.

This namespace has no market, model, selector, publication, Validation,
agent-write, probability, risk, exposure, trading, or execution authority.
"""

from .ledger import AppendOnlyLedger, LedgerError, canonical_event_bytes, event_digest
from .projection import ProjectionError, build_partitioned_projection, project_programme
from .synchronisation import SynchronisationFinding, compare_programme_state

__all__ = [
    "AppendOnlyLedger",
    "LedgerError",
    "ProjectionError",
    "SynchronisationFinding",
    "build_partitioned_projection",
    "canonical_event_bytes",
    "compare_programme_state",
    "event_digest",
    "project_programme",
]
