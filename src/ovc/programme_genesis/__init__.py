"""Governance-only Programme Genesis ledger, graph, migration, read-model and projection utilities.

This namespace has no market, model, selector, publication, Validation,
agent-write, probability, risk, exposure, trading, or execution authority.
"""

from .graph import GraphValidationError, impact_analysis, validate_graph
from .ledger import AppendOnlyLedger, LedgerError, canonical_event_bytes, event_digest
from .migration import (
    MigrationError,
    build_conflict_ledger,
    build_migration_record,
    build_migration_snapshot,
    build_snapshot_from_registry,
    discover_programme_state_paths,
    load_migration_source_registry,
    write_snapshot,
)
from .projection import ProjectionError, build_partitioned_projection, project_programme
from .read_model import (
    ReadModelError,
    build_compact_portfolio_report,
    build_disabled_control_plane_projection,
    build_portfolio_health_report,
    build_portfolio_read_model,
)
from .synchronisation import SynchronisationFinding, compare_programme_state

__all__ = [
    "AppendOnlyLedger",
    "GraphValidationError",
    "LedgerError",
    "MigrationError",
    "ProjectionError",
    "ReadModelError",
    "SynchronisationFinding",
    "build_compact_portfolio_report",
    "build_conflict_ledger",
    "build_disabled_control_plane_projection",
    "build_migration_record",
    "build_migration_snapshot",
    "build_partitioned_projection",
    "build_portfolio_health_report",
    "build_portfolio_read_model",
    "build_snapshot_from_registry",
    "canonical_event_bytes",
    "compare_programme_state",
    "discover_programme_state_paths",
    "event_digest",
    "impact_analysis",
    "load_migration_source_registry",
    "project_programme",
    "validate_graph",
    "write_snapshot",
]
