from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

INCIDENT_CLASSES = frozenset({
    "FALSE_CURRENTNESS",
    "PROTECTED_SOURCE_LEAK",
    "REFERENCE_OPTIMIZED_DIVERGENCE",
    "SOURCE_FRONTIER_UNRESOLVED",
    "INDEX_CORRUPTION",
})


class StabilizationError(ValueError):
    pass


def _git_sha(value: str, field: str) -> str:
    if type(value) is not str or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise StabilizationError(f"{field} must be an exact lowercase git SHA")
    return value


def build_shadow_observation(
    *,
    repository_commit: str,
    repository_tree: str,
    generation_id: str,
    source_frontier_id: str,
    currentness_state: str,
    reference_optimized_equivalent: bool,
    protected_source_leak_count: int,
    index_integrity_ok: bool = True,
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    _git_sha(repository_commit, "repository_commit")
    _git_sha(repository_tree, "repository_tree")
    if type(generation_id) is not str or not generation_id.startswith("p2cti:generation:"):
        raise StabilizationError("generation_id is invalid")
    if type(source_frontier_id) is not str or not source_frontier_id.startswith("p2cti:frontier:"):
        raise StabilizationError("source_frontier_id is invalid")
    if type(reference_optimized_equivalent) is not bool:
        raise StabilizationError("reference_optimized_equivalent must be boolean")
    if type(index_integrity_ok) is not bool:
        raise StabilizationError("index_integrity_ok must be boolean")
    if type(protected_source_leak_count) is not int or protected_source_leak_count < 0:
        raise StabilizationError("protected_source_leak_count must be non-negative integer")
    warning_list = sorted(set(warnings))
    if len(warning_list) != len(warnings) or any(type(value) is not str or not value for value in warning_list):
        raise StabilizationError("warnings must be unique non-empty strings")
    body = {
        "schema": "ovc-p2ctii-live-shadow-observation/v0.1",
        "repository_commit": repository_commit,
        "repository_tree": repository_tree,
        "generation_id": generation_id,
        "source_frontier_id": source_frontier_id,
        "currentness_state": currentness_state,
        "reference_optimized_equivalent": reference_optimized_equivalent,
        "protected_source_leak_count": protected_source_leak_count,
        "index_integrity_ok": index_integrity_ok,
        "warnings": warning_list,
        "read_only_shadow": True,
        "operational_reliance": False,
        "authority_effect": "NONE",
    }
    return {**body, "observation_sha256": canonical_sha256(body)}


def evaluate_incidents(observation: Mapping[str, Any]) -> dict[str, Any]:
    incidents: list[str] = []
    if observation.get("currentness_state") != "CURRENT":
        incidents.append("FALSE_CURRENTNESS" if observation.get("currentness_state") == "STALE" else "SOURCE_FRONTIER_UNRESOLVED")
    if observation.get("protected_source_leak_count", 0) != 0:
        incidents.append("PROTECTED_SOURCE_LEAK")
    if observation.get("reference_optimized_equivalent") is not True:
        incidents.append("REFERENCE_OPTIMIZED_DIVERGENCE")
    if observation.get("index_integrity_ok") is not True:
        incidents.append("INDEX_CORRUPTION")
    incidents = sorted(set(incidents))
    if set(incidents) - INCIDENT_CLASSES:
        raise StabilizationError("unknown incident class")
    body = {
        "schema": "ovc-p2ctii-stabilization-evaluation/v0.1",
        "observation_sha256": observation.get("observation_sha256"),
        "incident_classes": incidents,
        "status": "PASS_SHADOW_STABLE" if not incidents else "REQUALIFICATION_REQUIRED",
        "operational_reliance": False,
        "automatic_activation": False,
        "authority_effect": "NONE",
    }
    return {**body, "evaluation_sha256": canonical_sha256(body)}


def build_stabilization_ledger(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for observation in observations:
        expected = canonical_sha256({key: value for key, value in observation.items() if key != "observation_sha256"})
        if observation.get("observation_sha256") != expected:
            raise StabilizationError("observation integrity failure")
        rows.append({
            "observation_sha256": observation["observation_sha256"],
            "repository_commit": observation["repository_commit"],
            "repository_tree": observation["repository_tree"],
            "evaluation": evaluate_incidents(observation),
        })
    rows.sort(key=lambda row: (row["repository_commit"], row["observation_sha256"]))
    body = {
        "schema": "ovc-p2ctii-stabilization-ledger/v0.1",
        "rows": rows,
        "all_stable": all(row["evaluation"]["status"] == "PASS_SHADOW_STABLE" for row in rows),
        "read_only_shadow": True,
        "operational_reliance": False,
        "activation_gate": "P2CTII-G-OBSERVABILITY-ACTIVATE",
        "authority_effect": "NONE",
    }
    return {**body, "ledger_sha256": canonical_sha256(body)}
