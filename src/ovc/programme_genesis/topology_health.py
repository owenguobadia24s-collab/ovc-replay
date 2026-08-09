from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Iterable, Mapping


def anomaly_summary(anomalies: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in anomalies]
    return {
        "anomaly_count": len(rows),
        "severity_counts": dict(sorted(Counter(str(row.get("severity", "UNRESOLVED")) for row in rows).items())),
        "anomaly_code_counts": dict(sorted(Counter(str(row.get("anomaly_code", "UNRESOLVED")) for row in rows).items())),
        "opaque_score": None,
        "authority_effect": "NONE_HEALTH_ONLY",
    }


def anomalies_for_programme(read_model: Mapping[str, Any], programme_id: str) -> list[dict[str, Any]]:
    return sorted(
        [deepcopy(dict(row)) for row in read_model.get("anomalies", []) if programme_id in row.get("affected_programme_ids", [])],
        key=lambda row: (row.get("severity", ""), row.get("anomaly_code", ""), row.get("anomaly_id", "")),
    )


def anomalies_for_component(read_model: Mapping[str, Any], component_id: str) -> list[dict[str, Any]]:
    return sorted(
        [deepcopy(dict(row)) for row in read_model.get("anomalies", []) if component_id in row.get("affected_component_ids", [])],
        key=lambda row: (row.get("severity", ""), row.get("anomaly_code", ""), row.get("anomaly_id", "")),
    )
