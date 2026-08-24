from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

INCIDENT_CLASSES = frozenset({
    "CANDIDATE_AUTHORITY_BYPASS",
    "CAPACITY_EXCEEDED",
    "FALSE_CURRENTNESS",
    "INDEX_CORRUPTION",
    "MODE_LEAK",
    "OWNER_SEMANTIC_CONFLICT",
    "REFERENCE_OPTIMIZED_DIVERGENCE",
    "SOURCE_FRONTIER_UNRESOLVED",
    "SOURCE_IDENTITY_DRIFT",
    "VALIDATION_LEAK",
})


class StabilizationError(ValueError):
    pass


def _git_sha(value: str, field: str) -> str:
    if type(value) is not str or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise StabilizationError(f"{field} must be an exact lowercase git SHA")
    return value


def _sha256(value: str, field: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise StabilizationError(f"{field} must be an exact lowercase SHA-256")
    return value


def _count(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise StabilizationError(f"{field} must be a non-negative integer")
    return value


def build_shadow_observation(
    *,
    repository_commit: str,
    repository_tree: str,
    source_census_id: str,
    source_census_sha256: str,
    source_completeness_manifest_id: str,
    source_completeness_sha256: str,
    expected_subject_count: int,
    reconciled_subject_count: int,
    currentness_state: str,
    reference_optimized_equivalent: bool,
    protected_source_leak_count: int,
    validation_leak_count: int,
    candidate_authority_survivor_count: int,
    source_identity_drift: bool,
    owner_semantic_conflict: bool,
    index_integrity_ok: bool,
    capacity_complete: bool,
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    _git_sha(repository_commit, "repository_commit")
    _git_sha(repository_tree, "repository_tree")
    if type(source_census_id) is not str or not source_census_id.startswith("P1CDI-G0-SOURCE-CENSUS:"):
        raise StabilizationError("source_census_id is invalid")
    _sha256(source_census_sha256, "source_census_sha256")
    if type(source_completeness_manifest_id) is not str or not source_completeness_manifest_id.startswith(
        "P1CDI-G0-SOURCE-COMPLETENESS:"
    ):
        raise StabilizationError("source_completeness_manifest_id is invalid")
    _sha256(source_completeness_sha256, "source_completeness_sha256")
    _count(expected_subject_count, "expected_subject_count")
    _count(reconciled_subject_count, "reconciled_subject_count")
    if currentness_state not in {"CURRENT", "STALE", "UNRESOLVED"}:
        raise StabilizationError("currentness_state is invalid")
    for field, value in (
        ("reference_optimized_equivalent", reference_optimized_equivalent),
        ("source_identity_drift", source_identity_drift),
        ("owner_semantic_conflict", owner_semantic_conflict),
        ("index_integrity_ok", index_integrity_ok),
        ("capacity_complete", capacity_complete),
    ):
        if type(value) is not bool:
            raise StabilizationError(f"{field} must be boolean")
    _count(protected_source_leak_count, "protected_source_leak_count")
    _count(validation_leak_count, "validation_leak_count")
    _count(candidate_authority_survivor_count, "candidate_authority_survivor_count")
    warning_list = sorted(set(warnings))
    if len(warning_list) != len(warnings) or any(type(value) is not str or not value for value in warning_list):
        raise StabilizationError("warnings must be unique non-empty strings")

    body = {
        "schema": "ovc-p1cdii-live-shadow-observation/v0.1",
        "repository_commit": repository_commit,
        "repository_tree": repository_tree,
        "source_census_id": source_census_id,
        "source_census_sha256": source_census_sha256,
        "source_completeness_manifest_id": source_completeness_manifest_id,
        "source_completeness_sha256": source_completeness_sha256,
        "expected_subject_count": expected_subject_count,
        "reconciled_subject_count": reconciled_subject_count,
        "currentness_state": currentness_state,
        "reference_optimized_equivalent": reference_optimized_equivalent,
        "protected_source_leak_count": protected_source_leak_count,
        "validation_leak_count": validation_leak_count,
        "candidate_authority_survivor_count": candidate_authority_survivor_count,
        "source_identity_drift": source_identity_drift,
        "owner_semantic_conflict": owner_semantic_conflict,
        "index_integrity_ok": index_integrity_ok,
        "capacity_complete": capacity_complete,
        "warnings": warning_list,
        "read_only_shadow": True,
        "operational_reliance": False,
        "automatic_activation": False,
        "authority_effect": "NONE",
    }
    return {**body, "observation_sha256": canonical_sha256(body)}


def evaluate_incidents(observation: Mapping[str, Any]) -> dict[str, Any]:
    incidents: list[str] = []
    currentness = observation.get("currentness_state")
    if currentness != "CURRENT":
        incidents.append("FALSE_CURRENTNESS" if currentness == "STALE" else "SOURCE_FRONTIER_UNRESOLVED")
    if observation.get("expected_subject_count") != observation.get("reconciled_subject_count"):
        incidents.append("SOURCE_FRONTIER_UNRESOLVED")
    if observation.get("source_identity_drift") is not False:
        incidents.append("SOURCE_IDENTITY_DRIFT")
    if observation.get("owner_semantic_conflict") is not False:
        incidents.append("OWNER_SEMANTIC_CONFLICT")
    if observation.get("reference_optimized_equivalent") is not True:
        incidents.append("REFERENCE_OPTIMIZED_DIVERGENCE")
    if observation.get("protected_source_leak_count", 0) != 0:
        incidents.append("MODE_LEAK")
    if observation.get("validation_leak_count", 0) != 0:
        incidents.append("VALIDATION_LEAK")
    if observation.get("candidate_authority_survivor_count", 0) != 0:
        incidents.append("CANDIDATE_AUTHORITY_BYPASS")
    if observation.get("index_integrity_ok") is not True:
        incidents.append("INDEX_CORRUPTION")
    if observation.get("capacity_complete") is not True:
        incidents.append("CAPACITY_EXCEEDED")
    incidents = sorted(set(incidents))
    if set(incidents) - INCIDENT_CLASSES:
        raise StabilizationError("unknown incident class")
    body = {
        "schema": "ovc-p1cdii-stabilization-evaluation/v0.1",
        "observation_sha256": observation.get("observation_sha256"),
        "incident_classes": incidents,
        "status": "PASS_SHADOW_STABLE" if not incidents else "REQUALIFICATION_REQUIRED",
        "operational_reliance": False,
        "automatic_activation": False,
        "authority_effect": "NONE",
    }
    return {**body, "evaluation_sha256": canonical_sha256(body)}


def build_stabilization_ledger(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not observations:
        raise StabilizationError("at least one shadow observation is required")
    rows: list[dict[str, Any]] = []
    for observation in observations:
        expected = canonical_sha256({key: value for key, value in observation.items() if key != "observation_sha256"})
        if observation.get("observation_sha256") != expected:
            raise StabilizationError("observation integrity failure")
        rows.append({
            "observation_sha256": observation["observation_sha256"],
            "repository_commit": observation["repository_commit"],
            "repository_tree": observation["repository_tree"],
            "source_census_id": observation["source_census_id"],
            "evaluation": evaluate_incidents(observation),
        })
    rows.sort(key=lambda row: (row["repository_commit"], row["observation_sha256"]))
    body = {
        "schema": "ovc-p1cdii-stabilization-ledger/v0.1",
        "rows": rows,
        "all_stable": all(row["evaluation"]["status"] == "PASS_SHADOW_STABLE" for row in rows),
        "read_only_shadow": True,
        "operational_reliance": False,
        "activation_gate": "P1CDII-G-OBSERVABILITY-ACTIVATE",
        "automatic_activation": False,
        "authority_effect": "NONE",
    }
    return {**body, "ledger_sha256": canonical_sha256(body)}
