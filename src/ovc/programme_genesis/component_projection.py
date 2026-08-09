from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def programme_dossier(read_model: Mapping[str, Any], programme_id: str) -> dict[str, Any] | None:
    """Return one derived programme/component dossier without changing source authority."""
    for row in read_model.get("programme_component_crosswalk", []):
        if row.get("programme_id") == programme_id:
            return deepcopy(dict(row))
    return None


def component_dossier(read_model: Mapping[str, Any], component_id: str) -> dict[str, Any] | None:
    """Return a component with its derived producers/consumers and anomaly references."""
    component = next((dict(row) for row in read_model.get("components", []) if row.get("component_id") == component_id), None)
    if component is None:
        return None
    incoming = []
    outgoing = []
    for edge in read_model.get("component_dependencies", []):
        if edge.get("to_id") == component_id:
            incoming.append(dict(edge))
        if edge.get("from_id") == component_id:
            outgoing.append(dict(edge))
    anomalies = [
        dict(row) for row in read_model.get("anomalies", []) if component_id in row.get("affected_component_ids", [])
    ]
    return {
        "component": deepcopy(component),
        "incoming": sorted(incoming, key=lambda row: row["edge_id"]),
        "outgoing": sorted(outgoing, key=lambda row: row["edge_id"]),
        "anomalies": sorted(anomalies, key=lambda row: row["anomaly_id"]),
        "authority_effect": "NONE_READ_ONLY_PROJECTION",
    }


def portfolio_projection(read_model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "portfolio": deepcopy(dict(read_model.get("portfolio", {}))),
        "health_summary": deepcopy(dict(read_model.get("health_summary", {}))),
        "topology_sha256": read_model.get("topology_sha256"),
        "authority_effect": "NONE_READ_ONLY_PROJECTION",
    }
