from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Mapping


class TopologyConformanceError(ValueError):
    pass


def _require_read_model(read_model: Mapping[str, Any]) -> None:
    if read_model.get("schema") != "ovc-genesis-repository-topology-read-model/v1":
        raise TopologyConformanceError("unsupported topology read-model schema")
    if read_model.get("authority_effect") != "NONE_DERIVED_REPLACEABLE_READ_MODEL":
        raise TopologyConformanceError("authority-bearing topology input is forbidden")


def _component_index(read_model: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(row.get("component_id")): row for row in read_model.get("components", [])}


def _anomaly_rows(read_model: Mapping[str, Any], codes: set[str]) -> list[dict[str, Any]]:
    return [
        deepcopy(dict(row))
        for row in read_model.get("anomalies", [])
        if str(row.get("anomaly_code")) in codes
    ]


def build_repository_conformance_snapshot(read_model: Mapping[str, Any]) -> dict[str, Any]:
    """Build the GRT-WP9 repository-wide conformance dossier.

    The dossier is descriptive and source-linked only. It deliberately preserves
    unresolved ownership, lifecycle, lineage and authority findings and has no
    remediation or programme/dependency admission effect.
    """

    _require_read_model(read_model)
    components = [dict(row) for row in read_model.get("components", [])]
    crosswalk = [dict(row) for row in read_model.get("programme_component_crosswalk", [])]
    component_by_id = _component_index(read_model)

    coverage = {status: [] for status in ("COMPLETE", "PARTIAL", "NO_IMPLEMENTATION", "UNRESOLVED")}
    for row in crosswalk:
        coverage.setdefault(str(row.get("coverage_status", "UNRESOLVED")), []).append(str(row.get("programme_id")))
    for values in coverage.values():
        values.sort()

    unowned = [
        {
            "component_id": str(row.get("component_id")),
            "path": str(row.get("path")),
            "component_type": str(row.get("component_type")),
            "implementation_state": str(row.get("implementation_state")),
            "historical_state": str(row.get("historical_state")),
        }
        for row in components
        if not row.get("owner_programme_ids")
    ]
    unowned.sort(key=lambda row: (row["component_type"], row["path"], row["component_id"]))

    shared = [
        {
            "component_id": str(row.get("component_id")),
            "path": str(row.get("path")),
            "component_type": str(row.get("component_type")),
            "owner_programme_ids": sorted(str(value) for value in row.get("owner_programme_ids", [])),
        }
        for row in components
        if len(row.get("owner_programme_ids", [])) > 1
    ]
    shared.sort(key=lambda row: (row["component_type"], row["path"], row["component_id"]))

    historical = [
        {
            "component_id": str(row.get("component_id")),
            "path": str(row.get("path")),
            "component_type": str(row.get("component_type")),
            "historical_state": str(row.get("historical_state")),
            "owner_programme_ids": sorted(str(value) for value in row.get("owner_programme_ids", [])),
        }
        for row in components
        if str(row.get("historical_state", "CURRENT")) != "CURRENT"
    ]
    historical.sort(key=lambda row: (row["historical_state"], row["component_type"], row["path"]))

    stale_documentation = _anomaly_rows(read_model, {"STALE_DOCUMENTATION"})
    authority_mismatches = _anomaly_rows(
        read_model,
        {"AUTHORITY_MISMATCH", "GENESIS_TOPOLOGY_CONFLICT", "INFERRED_HARD_DEPENDENCY", "STALE_PROGRAMME_STATE"},
    )
    unresolved_relationships = _anomaly_rows(read_model, {"UNRESOLVED_DEPENDENCY"})

    blocker_rows = [deepcopy(dict(row)) for row in read_model.get("anomalies", []) if row.get("severity") == "BLOCKER"]
    warning_rows = [deepcopy(dict(row)) for row in read_model.get("anomalies", []) if row.get("severity") == "WARNING"]

    component_type_counts = dict(sorted(Counter(str(row.get("component_type")) for row in components).items()))
    coverage_counts = {status: len(values) for status, values in sorted(coverage.items())}

    return {
        "schema": "ovc-grt-repository-conformance-snapshot/v1",
        "programme_id": "OVC-GENESIS-REPOSITORY-TOPOLOGY-v0.1",
        "packet_id": "GRT-WP9",
        "source_commit": str(read_model.get("portfolio", {}).get("source_commit", "")),
        "topology_sha256": str(read_model.get("topology_sha256", "")),
        "authority_effect": "NONE_DERIVED_CONFORMANCE_AUDIT_ONLY",
        "programme_coverage": {
            "counts": coverage_counts,
            "complete": coverage.get("COMPLETE", []),
            "partial": coverage.get("PARTIAL", []),
            "no_implementation": coverage.get("NO_IMPLEMENTATION", []),
            "unresolved": coverage.get("UNRESOLVED", []),
        },
        "component_population": {
            "count": len(components),
            "type_counts": component_type_counts,
            "without_programme_owner_count": len(unowned),
            "without_programme_owner": unowned,
            "shared_component_count": len(shared),
            "shared_components": shared,
            "historical_or_legacy_count": len(historical),
            "historical_or_legacy": historical,
        },
        "findings": {
            "stale_documentation_count": len(stale_documentation),
            "stale_documentation": stale_documentation,
            "authority_mismatch_or_conflict_count": len(authority_mismatches),
            "authority_mismatches_or_conflicts": authority_mismatches,
            "unresolved_relationship_count": len(unresolved_relationships),
            "unresolved_relationships": unresolved_relationships,
            "warning_count": len(warning_rows),
            "blocker_count": len(blocker_rows),
            "blockers": blocker_rows,
        },
        "source_provenance": {
            "read_model_schema": str(read_model.get("schema")),
            "build_metadata": deepcopy(dict(read_model.get("build_metadata", {}))),
            "health_summary": deepcopy(dict(read_model.get("health_summary", {}))),
        },
        "repair_performed": False,
        "programme_or_dependency_authority_changed": False,
        "validation_consumed": False,
    }


__all__ = ["TopologyConformanceError", "build_repository_conformance_snapshot"]
