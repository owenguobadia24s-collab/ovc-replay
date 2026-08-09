from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Mapping

from .topology import canonical_sha256


class TopologyDiffError(ValueError):
    pass


_ORPHAN_CODES = {
    "ORPHAN_CONTRACT", "ORPHAN_SCHEMA", "ORPHAN_REGISTRY", "ORPHAN_FIXTURE",
    "ORPHAN_TEST", "ORPHAN_WORKFLOW",
}


def _require_model(value: Mapping[str, Any], label: str) -> None:
    if value.get("schema") != "ovc-genesis-repository-topology-read-model/v1":
        raise TopologyDiffError(f"{label} topology schema is unsupported")
    if value.get("authority_effect") != "NONE_DERIVED_REPLACEABLE_READ_MODEL":
        raise TopologyDiffError(f"{label} topology is authority-bearing")
    commit = str(value.get("portfolio", {}).get("source_commit", ""))
    if len(commit) != 40:
        raise TopologyDiffError(f"{label} source commit is not pinned")


def _components(model: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("path")): dict(row) for row in model.get("components", [])}


def _programmes(model: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("programme_id")): dict(row) for row in model.get("programmes", [])}


def _endpoint_key(endpoint: str, id_to_path: Mapping[str, str]) -> str:
    if endpoint.startswith("programme:"):
        return endpoint
    return id_to_path.get(endpoint, f"unresolved-component:{endpoint}")


def _edge_rows(model: Mapping[str, Any]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    id_to_path = {str(row.get("component_id")): str(row.get("path")) for row in model.get("components", [])}
    rows: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in model.get("component_dependencies", []):
        value = dict(row)
        key = (
            _endpoint_key(str(value.get("from_id", "")), id_to_path),
            _endpoint_key(str(value.get("to_id", "")), id_to_path),
            str(value.get("edge_type", "")),
            str(value.get("evidence_class", "")),
        )
        rows[key] = value
    return rows


def _anomaly_key(row: Mapping[str, Any], id_to_path: Mapping[str, str]) -> tuple[Any, ...]:
    affected_paths = tuple(sorted(id_to_path.get(str(cid), f"unresolved-component:{cid}") for cid in row.get("affected_component_ids", [])))
    affected_programmes = tuple(sorted(str(pid) for pid in row.get("affected_programme_ids", [])))
    return (
        str(row.get("anomaly_code", "")),
        str(row.get("severity", "")),
        affected_paths,
        affected_programmes,
        str(row.get("detail", "")),
    )


def _anomalies(model: Mapping[str, Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    id_to_path = {str(row.get("component_id")): str(row.get("path")) for row in model.get("components", [])}
    return {_anomaly_key(row, id_to_path): dict(row) for row in model.get("anomalies", [])}


def _change(change_type: str, stable_key: str, *, before: Any = None, after: Any = None, evidence: Any = None) -> dict[str, Any]:
    return {
        "change_type": change_type,
        "stable_key": stable_key,
        "before": deepcopy(before),
        "after": deepcopy(after),
        "evidence": deepcopy(evidence),
        "authority_effect": "NONE_ADVISORY_DIFF_ONLY",
    }


def build_topology_diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Compare two source-bound GRT read models without adopting or repairing anything."""
    _require_model(before, "before")
    _require_model(after, "after")

    before_components = _components(before)
    after_components = _components(after)
    changes: list[dict[str, Any]] = []

    before_paths = set(before_components)
    after_paths = set(after_components)
    for path in sorted(after_paths - before_paths):
        changes.append(_change("NEW_COMPONENT", path, after=after_components[path]))
    for path in sorted(before_paths - after_paths):
        changes.append(_change("REMOVED_COMPONENT", path, before=before_components[path]))

    for path in sorted(before_paths & after_paths):
        left = before_components[path]
        right = after_components[path]
        left_owners = sorted(str(v) for v in left.get("owner_programme_ids", []))
        right_owners = sorted(str(v) for v in right.get("owner_programme_ids", []))
        if left_owners != right_owners:
            changes.append(_change("CHANGED_OWNER", path, before=left_owners, after=right_owners))
        if left.get("authority_state") != right.get("authority_state"):
            changes.append(_change("CHANGED_AUTHORITY_REFERENCE", path, before=left.get("authority_state"), after=right.get("authority_state")))
        if left.get("implementation_state") != right.get("implementation_state"):
            changes.append(_change("IMPLEMENTATION_STATE_CHANGE", path, before=left.get("implementation_state"), after=right.get("implementation_state")))
        if left.get("historical_state") != right.get("historical_state"):
            changes.append(_change("SUPERSESSION_CHANGE", path, before=left.get("historical_state"), after=right.get("historical_state")))

    before_edges = _edge_rows(before)
    after_edges = _edge_rows(after)
    for key in sorted(set(after_edges) - set(before_edges)):
        changes.append(_change("NEW_DEPENDENCY", "|".join(key), after=after_edges[key]))
    for key in sorted(set(before_edges) - set(after_edges)):
        changes.append(_change("REMOVED_DEPENDENCY", "|".join(key), before=before_edges[key]))

    before_programmes = _programmes(before)
    after_programmes = _programmes(after)
    for programme_id in sorted(set(before_programmes) | set(after_programmes)):
        left = before_programmes.get(programme_id)
        right = after_programmes.get(programme_id)
        if left is None or right is None:
            changes.append(_change("PROGRAMME_STATE_REFERENCE_CHANGE", programme_id, before=left, after=right))
            continue
        left_ref = {
            "genesis_record_id": left.get("genesis_record_id"),
            "status": left.get("status"),
            "authority_state": left.get("authority_state"),
            "source_refs": sorted(str(v) for v in left.get("source_refs", [])),
        }
        right_ref = {
            "genesis_record_id": right.get("genesis_record_id"),
            "status": right.get("status"),
            "authority_state": right.get("authority_state"),
            "source_refs": sorted(str(v) for v in right.get("source_refs", [])),
        }
        if left_ref != right_ref:
            changes.append(_change("PROGRAMME_STATE_REFERENCE_CHANGE", programme_id, before=left_ref, after=right_ref))

    before_anomalies = _anomalies(before)
    after_anomalies = _anomalies(after)
    new_keys = set(after_anomalies) - set(before_anomalies)
    resolved_keys = set(before_anomalies) - set(after_anomalies)
    for key in sorted(new_keys, key=repr):
        row = after_anomalies[key]
        code = str(row.get("anomaly_code"))
        change_type = "NEW_ORPHAN" if code in _ORPHAN_CODES else "NEW_WARNING"
        changes.append(_change(change_type, repr(key), after=row))
    for key in sorted(resolved_keys, key=repr):
        row = before_anomalies[key]
        code = str(row.get("anomaly_code"))
        change_type = "RESOLVED_ORPHAN" if code in _ORPHAN_CODES else "RESOLVED_WARNING"
        changes.append(_change(change_type, repr(key), before=row))

    changes.sort(key=lambda row: (row["change_type"], row["stable_key"], canonical_sha256(row)))
    counts = dict(sorted(Counter(row["change_type"] for row in changes).items()))
    before_commit = str(before["portfolio"]["source_commit"])
    after_commit = str(after["portfolio"]["source_commit"])
    core = {
        "schema": "ovc-genesis-repository-topology-diff/v1",
        "programme_id": "OVC-GENESIS-REPOSITORY-TOPOLOGY-v0.1",
        "packet_id": "GRT-WP10",
        "before": {"source_commit": before_commit, "topology_sha256": str(before.get("topology_sha256", ""))},
        "after": {"source_commit": after_commit, "topology_sha256": str(after.get("topology_sha256", ""))},
        "change_count": len(changes),
        "change_type_counts": counts,
        "changes": changes,
        "incremental_projection": {
            "changed_component_paths": sorted({row["stable_key"] for row in changes if row["change_type"] in {"NEW_COMPONENT", "REMOVED_COMPONENT", "CHANGED_OWNER", "CHANGED_AUTHORITY_REFERENCE", "IMPLEMENTATION_STATE_CHANGE", "SUPERSESSION_CHANGE"}}),
            "requires_source_rebuild_for_authoritative_truth": True,
            "automatic_repair": False,
        },
        "authority_effect": "NONE_DERIVED_COMMIT_DIFF_ONLY",
        "programme_or_dependency_authority_changed": False,
        "validation_consumed": False,
    }
    core["diff_sha256"] = canonical_sha256(core)
    return core


def verify_topology_diff(diff: Mapping[str, Any]) -> None:
    if diff.get("schema") != "ovc-genesis-repository-topology-diff/v1":
        raise TopologyDiffError("unsupported diff schema")
    if diff.get("authority_effect") != "NONE_DERIVED_COMMIT_DIFF_ONLY":
        raise TopologyDiffError("authority-bearing diff is forbidden")
    supplied = str(diff.get("diff_sha256", ""))
    body = dict(diff)
    body.pop("diff_sha256", None)
    if supplied != canonical_sha256(body):
        raise TopologyDiffError("diff identity mismatch")


__all__ = ["TopologyDiffError", "build_topology_diff", "verify_topology_diff"]
