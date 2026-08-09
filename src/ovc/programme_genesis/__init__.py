"""Governance-only Programme Genesis ledger, graph, migration, read-model, upkeep and projection utilities.

This namespace has no market, model, selector, publication, Validation,
agent-write, probability, risk, exposure, trading, or execution authority.
"""

from .component_projection import component_dossier, portfolio_projection, programme_dossier
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
from .topology import (
    TopologyError,
    build_repository_topology,
    build_topology_from_inventory,
    compact_topology_summary,
    resolve_commit,
    tracked_inventory,
)
from .topology_health import anomaly_summary, anomalies_for_component, anomalies_for_programme
from .upkeep import (
    UpkeepError,
    build_candidate_event,
    candidate_event_id,
    load_upkeep_registry,
    persist_candidate_event,
    preview_candidate_events,
    validate_candidate_event,
)

__all__ = [
    "AppendOnlyLedger",
    "GraphValidationError",
    "LedgerError",
    "MigrationError",
    "ProjectionError",
    "ReadModelError",
    "SynchronisationFinding",
    "TopologyError",
    "UpkeepError",
    "anomalies_for_component",
    "anomalies_for_programme",
    "anomaly_summary",
    "build_candidate_event",
    "build_compact_portfolio_report",
    "build_conflict_ledger",
    "build_disabled_control_plane_projection",
    "build_migration_record",
    "build_migration_snapshot",
    "build_partitioned_projection",
    "build_portfolio_health_report",
    "build_portfolio_read_model",
    "build_repository_topology",
    "build_snapshot_from_registry",
    "build_topology_from_inventory",
    "candidate_event_id",
    "canonical_event_bytes",
    "compare_programme_state",
    "compact_topology_summary",
    "component_dossier",
    "discover_programme_state_paths",
    "event_digest",
    "impact_analysis",
    "load_migration_source_registry",
    "load_upkeep_registry",
    "persist_candidate_event",
    "portfolio_projection",
    "preview_candidate_events",
    "programme_dossier",
    "project_programme",
    "resolve_commit",
    "tracked_inventory",
    "validate_candidate_event",
    "validate_graph",
    "write_snapshot",
]
