from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

from . import _topology_engine as _engine


TopologyError = _engine.TopologyError
DEFAULT_SCAN_ROOTS = _engine.DEFAULT_SCAN_ROOTS
COMPONENT_TYPES = _engine.COMPONENT_TYPES
EDGE_TYPES = _engine.EDGE_TYPES
EVIDENCE_CLASSES = _engine.EVIDENCE_CLASSES
ANOMALY_CODES = _engine.ANOMALY_CODES
canonical_json_bytes = _engine.canonical_json_bytes
canonical_sha256 = _engine.canonical_sha256
resolve_commit = _engine.resolve_commit
tracked_inventory = _engine.tracked_inventory
classify_component = _engine.classify_component


def _build_anomalies_fixed(
    programmes: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    crosswalks: Sequence[Mapping[str, Any]],
    component_edges: Sequence[Mapping[str, Any]],
    programme_dependencies: Sequence[Mapping[str, Any]],
    unresolved_refs: Mapping[str, Sequence[str]],
    content_by_path: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Build authority-neutral health findings with exact denominators.

    This wrapper supersedes only the implementation defect in the original GRT-WP6
    helper. It keeps the frozen anomaly vocabulary and source-precedence behaviour
    while ensuring every denominator is an integer count rather than a truthy list.
    """

    anomalies: list[dict[str, Any]] = []
    programme_count = len(programmes)
    component_count = len(components)
    by_id = {str(component["component_id"]): component for component in components}
    by_path = {str(component["path"]): component for component in components}
    crosswalk_by_programme = {str(row["programme_id"]): row for row in crosswalks}
    implementation_count = sum(1 for component in components if component["component_type"] in _engine._IMPLEMENTATION_TYPES)
    owned_implementation_count = sum(
        1
        for component in components
        if component["component_type"] in _engine._IMPLEMENTATION_TYPES and bool(component.get("owner_programme_ids"))
    )
    programmes_with_implementation = sum(1 for row in crosswalks if row.get("implementation_namespaces"))
    completed_programmes = sum(1 for programme in programmes if str(programme.get("status", "")).upper() == "COMPLETED")

    connected: set[str] = set()
    for edge in component_edges:
        from_id = str(edge.get("from_id", ""))
        to_id = str(edge.get("to_id", ""))
        if from_id in by_id:
            connected.add(from_id)
        if to_id in by_id:
            connected.add(to_id)

    for programme in programmes:
        programme_id = str(programme["programme_id"])
        row = crosswalk_by_programme.get(programme_id)
        if row is None:
            continue
        implementation = list(row.get("implementation_namespaces", []))
        if not implementation:
            anomalies.append(_engine._anomaly(
                "PROGRAMME_WITHOUT_IMPLEMENTATION",
                "WARNING",
                programmes=[programme_id],
                source_evidence=programme.get("source_refs", []),
                denominator_name="programmes",
                denominator_count=programme_count,
                recommendation="REVIEW_PROGRAMME_IMPLEMENTATION_COVERAGE",
                detail="No owned executable implementation component was derived for this programme.",
            ))
        else:
            for category, code in (
                ("contracts", "MISSING_CONTRACT"),
                ("schemas", "MISSING_SCHEMA"),
                ("fixtures", "MISSING_FIXTURE"),
                ("tests", "MISSING_TEST"),
            ):
                if not row.get(category):
                    anomalies.append(_engine._anomaly(
                        code,
                        "INFO",
                        components=implementation,
                        programmes=[programme_id],
                        source_evidence=programme.get("source_refs", []),
                        denominator_name="programmes_with_implementation",
                        denominator_count=programmes_with_implementation,
                        recommendation="REVIEW_SUPPORTING_GOVERNANCE_COVERAGE",
                        detail=f"Programme has implementation but no derived {category} association.",
                    ))
        authority_components = list(row.get("programme_state_records", [])) + list(row.get("authority_records", []))
        if not authority_components:
            anomalies.append(_engine._anomaly(
                "MISSING_AUTHORITY_RECORD",
                "WARNING",
                programmes=[programme_id],
                source_evidence=programme.get("source_refs", []),
                denominator_name="programmes",
                denominator_count=programme_count,
                recommendation="REVIEW_AUTHORITATIVE_SOURCE_COVERAGE",
                detail="No programme-state or authority-bearing record was derived for this programme.",
            ))
        if str(programme.get("status", "")).upper() == "COMPLETED" and not row.get("completion_evidence"):
            anomalies.append(_engine._anomaly(
                "PROGRAMME_WITHOUT_ACCEPTED_COMPLETION_EVIDENCE",
                "WARNING",
                programmes=[programme_id],
                source_evidence=programme.get("source_refs", []),
                denominator_name="completed_programmes",
                denominator_count=completed_programmes,
                recommendation="REVIEW_COMPLETION_LINEAGE",
                detail="Programme projects COMPLETED but no decision/receipt completion evidence was associated.",
            ))

    for component in components:
        component_id = str(component["component_id"])
        component_type = str(component["component_type"])
        owners = list(component.get("owner_programme_ids", []))
        if component_type in _engine._IMPLEMENTATION_TYPES and not owners:
            anomalies.append(_engine._anomaly(
                "IMPLEMENTATION_WITHOUT_PROGRAMME_OWNER",
                "WARNING",
                components=[component_id],
                source_evidence=component.get("source_refs", []),
                denominator_name="implementation_components",
                denominator_count=implementation_count,
                recommendation="RESOLVE_OWNERSHIP_OR_PRESERVE_UNRESOLVED",
                detail="Executable implementation is tracked without a defensible programme owner.",
            ))
        if component_type in _engine._IMPLEMENTATION_TYPES and owners and not component.get("owner_genesis_id"):
            anomalies.append(_engine._anomaly(
                "IMPLEMENTATION_WITHOUT_GENESIS_CROSSWALK",
                "INFO",
                components=[component_id],
                programmes=owners,
                source_evidence=component.get("source_refs", []),
                denominator_name="owned_implementation_components",
                denominator_count=owned_implementation_count,
                recommendation="PRESERVE_NON_NATIVE_OR_DEFERRED_GENESIS_STATUS",
                detail="Implementation ownership is derived, but no accepted native Genesis identity is bound.",
            ))
        if len(owners) > 1:
            explicit_owners = {
                item.get("programme_id")
                for item in component.get("ownership_evidence", [])
                if item.get("evidence_class") == "SOURCE_EXPLICIT"
            }
            code = "CONFLICTING_PROGRAMME_OWNERSHIP" if len(explicit_owners) > 1 else "DUPLICATE_COMPONENT_OWNERSHIP"
            anomalies.append(_engine._anomaly(
                code,
                "WARNING" if code == "CONFLICTING_PROGRAMME_OWNERSHIP" else "INFO",
                components=[component_id],
                programmes=owners,
                source_evidence=component.get("source_refs", []),
                denominator_name="components",
                denominator_count=component_count,
                recommendation="REVIEW_SHARED_OR_CONFLICTING_OWNERSHIP",
                detail="Component is associated with more than one programme; no canonical owner was guessed.",
            ))
        orphan_code = {
            "CONTRACT": "ORPHAN_CONTRACT",
            "SCHEMA": "ORPHAN_SCHEMA",
            "REGISTRY": "ORPHAN_REGISTRY",
            "FIXTURE": "ORPHAN_FIXTURE",
            "TEST": "ORPHAN_TEST",
            "WORKFLOW": "ORPHAN_WORKFLOW",
        }.get(component_type)
        if orphan_code and component_id not in connected and not owners:
            anomalies.append(_engine._anomaly(
                orphan_code,
                "INFO",
                components=[component_id],
                source_evidence=component.get("source_refs", []),
                denominator_name=f"{component_type.lower()}_components",
                denominator_count=sum(1 for row in components if row["component_type"] == component_type),
                recommendation="REVIEW_ORPHAN_OR_PRESERVE_AS_STANDALONE",
                detail="Supporting component has no derived owner and no derived component relationship.",
            ))
        if component_type in {"RELEASE_RECORD", "MANIFEST"} and not owners:
            release_denominator = sum(1 for row in components if row["component_type"] in {"RELEASE_RECORD", "MANIFEST"})
            for code in ("RELEASE_WITHOUT_PROGRAMME_LINEAGE", "MISSING_RELEASE_LINEAGE"):
                anomalies.append(_engine._anomaly(
                    code,
                    "WARNING",
                    components=[component_id],
                    source_evidence=component.get("source_refs", []),
                    denominator_name="release_or_manifest_components",
                    denominator_count=release_denominator,
                    recommendation="REVIEW_RELEASE_LINEAGE",
                    detail="Release/manifest evidence has no derived programme lineage.",
                ))

    for source_path, refs in sorted(unresolved_refs.items()):
        refs = list(refs)
        if not refs:
            continue
        source_component = by_path.get(source_path)
        anomalies.append(_engine._anomaly(
            "UNRESOLVED_DEPENDENCY",
            "INFO",
            components=[source_component["component_id"]] if source_component else [],
            programmes=source_component.get("owner_programme_ids", []) if source_component else [],
            source_evidence=[source_path, *refs[:20]],
            denominator_name="components",
            denominator_count=component_count,
            recommendation="REVIEW_MISSING_OR_HISTORICAL_REFERENCE",
            detail=f"{len(refs)} repository-like path reference(s) do not resolve to a scanned tracked component.",
        ))

    for dependency in programme_dependencies:
        if dependency.get("hardness") == "HARD" and dependency.get("source_kind") != "SOURCE_EXPLICIT":
            anomalies.append(_engine._anomaly(
                "INFERRED_HARD_DEPENDENCY",
                "BLOCKER",
                programmes=[str(dependency.get("from_programme_id")), str(dependency.get("to_programme_id"))],
                source_evidence=[str(dependency.get("source_ref"))],
                denominator_name="programme_dependencies",
                denominator_count=len(programme_dependencies),
                recommendation="DO_NOT_USE_AS_HARD_PREREQUISITE",
                detail="A hard programme dependency is not source-explicit; topology cannot promote it.",
            ))

    incoming_to: defaultdict[str, list[str]] = defaultdict(list)
    active_sources: set[str] = set()
    for edge in component_edges:
        source = by_id.get(str(edge.get("from_id", "")))
        target = by_id.get(str(edge.get("to_id", "")))
        if source and target and edge.get("edge_type") in {"DEPENDS_ON", "REFERENCES", "EXECUTED_BY", "TESTED_BY"}:
            incoming_to[str(target["component_id"])].append(str(source["component_id"]))
            if source["component_type"] in _engine._IMPLEMENTATION_TYPES and source.get("historical_state") == "CURRENT":
                active_sources.add(str(source["component_id"]))

    historical_count = sum(1 for component in components if component.get("historical_state") in {"SUPERSEDED", "LEGACY"})
    for component in components:
        if component.get("historical_state") in {"SUPERSEDED", "LEGACY"}:
            referrers = [item for item in incoming_to.get(str(component["component_id"]), []) if item in active_sources]
            if referrers:
                anomalies.append(_engine._anomaly(
                    "SUPERSEDED_COMPONENT_STILL_REFERENCED",
                    "WARNING",
                    components=[str(component["component_id"]), *referrers],
                    programmes=component.get("owner_programme_ids", []),
                    source_evidence=component.get("source_refs", []),
                    denominator_name="historical_or_legacy_components",
                    denominator_count=historical_count,
                    recommendation="REVIEW_RUNTIME_REACHABILITY",
                    detail="Current implementation evidence references a superseded or legacy component.",
                ))

    for edge in component_edges:
        if edge.get("edge_type") != "DEPENDS_ON":
            continue
        source = by_id.get(str(edge.get("from_id", "")))
        target = by_id.get(str(edge.get("to_id", "")))
        if source and target and source.get("historical_state") == "CURRENT" and target.get("historical_state") == "LEGACY":
            anomalies.append(_engine._anomaly(
                "LEGACY_RUNTIME_IMPORT",
                "BLOCKER",
                components=[str(source["component_id"]), str(target["component_id"])],
                programmes=source.get("owner_programme_ids", []),
                source_evidence=[str(source.get("path"))],
                denominator_name="component_dependencies",
                denominator_count=len(component_edges),
                recommendation="REMOVE_OR_EXPLICITLY_GOVERN_LEGACY_RUNTIME_IMPORT",
                detail="Current executable code imports a legacy component.",
            ))

    pg_g6_present = any(
        "PG_G6_OPERATOR_DECISION" in path and "READ_ONLY_ROUTE" in text and "DEFER" in text
        for path, text in content_by_path.items()
    )
    if pg_g6_present:
        for path, text in content_by_path.items():
            component = by_path.get(path)
            if not component or "PENDING_PG_G6" not in text:
                continue
            if "CONTROL_PLANE_ADAPTER_REGISTRY" in path:
                anomalies.append(_engine._anomaly(
                    "STALE_PROGRAMME_STATE",
                    "WARNING",
                    components=[str(component["component_id"])],
                    programmes=component.get("owner_programme_ids", []),
                    source_evidence=[path],
                    denominator_name="programme_state_or_registry_components",
                    denominator_count=sum(1 for row in components if row["component_type"] in {"PROGRAMME_STATE", "REGISTRY"}),
                    recommendation="SUPERSEDE_LABEL_NON_DESTRUCTIVELY_IF_SEPARATELY_AUTHORISED",
                    detail="Status label still says PENDING_PG_G6 although accepted PG-G6 already decided route/enforcement DEFER; disabled booleans remain unchanged.",
                ))
            elif component["component_type"] == "DOCUMENT":
                anomalies.append(_engine._anomaly(
                    "STALE_DOCUMENTATION",
                    "INFO",
                    components=[str(component["component_id"])],
                    programmes=component.get("owner_programme_ids", []),
                    source_evidence=[path],
                    denominator_name="document_components",
                    denominator_count=sum(1 for row in components if row["component_type"] == "DOCUMENT"),
                    recommendation="REVIEW_DOCUMENTATION_FRESHNESS",
                    detail="Documentation still carries a pre-PG-G6 pending label after the accepted PG-G6 decision.",
                ))

    for path, text in content_by_path.items():
        component = by_path.get(path)
        if not component:
            continue
        upper = text.upper()
        if "TOPOLOGY_CONFLICT" in upper and path.startswith("docs/releases/genesis-repository-topology"):
            anomalies.append(_engine._anomaly(
                "GENESIS_TOPOLOGY_CONFLICT",
                "WARNING",
                components=[str(component["component_id"])],
                programmes=component.get("owner_programme_ids", []),
                source_evidence=[path],
                denominator_name="components",
                denominator_count=component_count,
                recommendation="REQUIRE_OPERATOR_SOURCE_PRECEDENCE_REVIEW",
                detail="A topology conflict is explicitly recorded; no automatic resolution is allowed.",
            ))
        if component.get("historical_state") in {"SUPERSEDED", "LEGACY"} and "ACTIVE" in upper and component["component_type"] in _engine._IMPLEMENTATION_TYPES:
            anomalies.append(_engine._anomaly(
                "IMPLEMENTATION_STATE_MISMATCH",
                "WARNING",
                components=[str(component["component_id"])],
                programmes=component.get("owner_programme_ids", []),
                source_evidence=[path],
                denominator_name="implementation_components",
                denominator_count=implementation_count,
                recommendation="REVIEW_IMPLEMENTATION_LIFECYCLE_STATE",
                detail="Historical/superseded implementation contains an ACTIVE marker; topology does not reinterpret it.",
            ))
        if component["component_type"] == "REGISTRY" and "SHADOW" in upper and '"ACTIVE"' in upper:
            anomalies.append(_engine._anomaly(
                "SHADOW_ACTIVE_MISMATCH",
                "INFO",
                components=[str(component["component_id"])],
                programmes=component.get("owner_programme_ids", []),
                source_evidence=[path],
                denominator_name="registry_components",
                denominator_count=sum(1 for row in components if row["component_type"] == "REGISTRY"),
                recommendation="REVIEW_SHADOW_ACTIVE_SEMANTICS",
                detail="Registry contains both SHADOW and ACTIVE markers; no authority interpretation is inferred.",
            ))

    return sorted(anomalies, key=lambda row: (row["severity"], row["anomaly_code"], row["anomaly_id"]))


# Patch only the internal WP6 anomaly builder; all scanner, ownership, identity,
# dependency and read-model logic remains the frozen engine implementation.
_engine._build_anomalies = _build_anomalies_fixed

build_topology_from_inventory = _engine.build_topology_from_inventory
build_repository_topology = _engine.build_repository_topology
compact_topology_summary = _engine.compact_topology_summary


__all__ = [
    "TopologyError",
    "DEFAULT_SCAN_ROOTS",
    "COMPONENT_TYPES",
    "EDGE_TYPES",
    "EVIDENCE_CLASSES",
    "ANOMALY_CODES",
    "canonical_json_bytes",
    "canonical_sha256",
    "resolve_commit",
    "tracked_inventory",
    "classify_component",
    "build_topology_from_inventory",
    "build_repository_topology",
    "compact_topology_summary",
]
