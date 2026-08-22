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


class PostActivationError(ValueError):
    pass


def _git_sha(value: str, field: str) -> str:
    if type(value) is not str or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise PostActivationError(f"{field} must be an exact lowercase git SHA")
    return value


def _p2cti_id(value: str, prefix: str, field: str) -> str:
    if type(value) is not str or not value.startswith(prefix):
        raise PostActivationError(f"{field} is invalid")
    digest = value.rsplit(":", 1)[1]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise PostActivationError(f"{field} digest is invalid")
    return value


def build_operational_observation(
    *,
    repository_commit: str,
    repository_tree: str,
    generation_id: str,
    source_frontier_id: str,
    currentness_state: str,
    reference_optimized_equivalent: bool,
    protected_source_leak_count: int,
    activation_receipt_ref: str,
    index_integrity_ok: bool = True,
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    _git_sha(repository_commit, "repository_commit")
    _git_sha(repository_tree, "repository_tree")
    _p2cti_id(generation_id, "p2cti:generation:", "generation_id")
    _p2cti_id(source_frontier_id, "p2cti:frontier:", "source_frontier_id")
    if currentness_state not in {"CURRENT", "STALE", "UNRESOLVED"}:
        raise PostActivationError("currentness_state is invalid")
    if type(reference_optimized_equivalent) is not bool or type(index_integrity_ok) is not bool:
        raise PostActivationError("equivalence and index integrity must be boolean")
    if type(protected_source_leak_count) is not int or protected_source_leak_count < 0:
        raise PostActivationError("protected_source_leak_count must be non-negative integer")
    if type(activation_receipt_ref) is not str or "P2CTII_G_OBSERVABILITY_ACTIVATE_ACTIVATION_RECEIPT" not in activation_receipt_ref:
        raise PostActivationError("activation_receipt_ref is invalid")
    warning_list = sorted(set(warnings))
    if len(warning_list) != len(warnings) or any(type(value) is not str or not value for value in warning_list):
        raise PostActivationError("warnings must be unique non-empty strings")
    body = {
        "schema": "ovc-p2ctii-post-activation-observation/v0.1",
        "repository_commit": repository_commit,
        "repository_tree": repository_tree,
        "generation_id": generation_id,
        "source_frontier_id": source_frontier_id,
        "currentness_state": currentness_state,
        "reference_optimized_equivalent": reference_optimized_equivalent,
        "protected_source_leak_count": protected_source_leak_count,
        "index_integrity_ok": index_integrity_ok,
        "activation_receipt_ref": activation_receipt_ref,
        "operational_reliance": True,
        "read_only": True,
        "durable_write_effect": False,
        "warnings": warning_list,
        "authority_effect": "NONE",
    }
    return {**body, "observation_sha256": canonical_sha256(body)}


def evaluate_operational_incidents(observation: Mapping[str, Any]) -> dict[str, Any]:
    expected = canonical_sha256({key: value for key, value in observation.items() if key != "observation_sha256"})
    if observation.get("observation_sha256") != expected:
        raise PostActivationError("observation integrity failure")
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
    body = {
        "schema": "ovc-p2ctii-post-activation-evaluation/v0.1",
        "observation_sha256": observation["observation_sha256"],
        "incident_classes": incidents,
        "status": "PASS_OPERATIONAL_STABLE" if not incidents else "REQUALIFICATION_REQUIRED",
        "required_action": "NONE" if not incidents else "DISABLE_RELIANCE_AND_REQUALIFY",
        "continue_operational_reliance": not incidents,
        "automatic_authority_expansion": False,
        "durable_write_effect": False,
        "authority_effect": "NONE",
    }
    return {**body, "evaluation_sha256": canonical_sha256(body)}


def build_operational_monitoring_ledger(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for observation in observations:
        evaluation = evaluate_operational_incidents(observation)
        rows.append({
            "observation_sha256": observation["observation_sha256"],
            "repository_commit": observation["repository_commit"],
            "repository_tree": observation["repository_tree"],
            "evaluation": evaluation,
        })
    rows.sort(key=lambda row: (row["repository_commit"], row["observation_sha256"]))
    body = {
        "schema": "ovc-p2ctii-post-activation-monitoring-ledger/v0.1",
        "rows": rows,
        "all_stable": all(row["evaluation"]["status"] == "PASS_OPERATIONAL_STABLE" for row in rows),
        "operational_reliance_scope": "READ_ONLY_CURRENT_PROJECTION_ONLY",
        "durable_write_effect": False,
        "next_reserved_gate": "P2CTII-G-CONTINUOUS-INTAKE",
        "authority_effect": "NONE",
    }
    return {**body, "ledger_sha256": canonical_sha256(body)}


def rehearse_isolated_write(
    records: Sequence[Mapping[str, Any]],
    *,
    durable_target: str | None = None,
) -> dict[str, Any]:
    if durable_target is not None:
        raise PostActivationError("durable targets are forbidden before P2CTII-G-CONTINUOUS-INTAKE")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping) or record.get("schema_family") != "P2CTI_CONTROL":
            raise PostActivationError("rehearsal accepts P2CTI_CONTROL records only")
        expected = canonical_sha256({key: value for key, value in record.items() if key != "content_sha256"})
        if record.get("content_sha256") != expected:
            raise PostActivationError("record content hash mismatch")
        record_id = record.get("record_id")
        if type(record_id) is not str or not record_id or record_id in seen:
            raise PostActivationError("record identity is missing or duplicated")
        payload = record.get("payload")
        if not isinstance(payload, Mapping) or payload.get("write_activation") is not False:
            raise PostActivationError("record is not synthetic/non-write")
        if record.get("authority_effect") != "NONE":
            raise PostActivationError("record carries authority effect")
        seen.add(record_id)
        normalized.append({
            "record_id": record_id,
            "content_sha256": record["content_sha256"],
            "object_type": record["object_type"],
        })
    normalized.sort(key=lambda row: row["record_id"])
    ephemeral_image = canonical_sha256(normalized)
    body = {
        "schema": "ovc-p2ctii-isolated-write-rehearsal/v0.1",
        "storage_scope": "EPHEMERAL_IN_MEMORY_ONLY",
        "record_count": len(normalized),
        "records": normalized,
        "ephemeral_image_sha256": ephemeral_image,
        "replay_equal": True,
        "durable_target": None,
        "durable_write_attempted": False,
        "durable_write_performed": False,
        "write_activation": False,
        "scientific_effect": "NONE",
        "candidate_effect": "NONE",
        "execution_authority": "NONE",
        "next_reserved_gate": "P2CTII-G-CONTINUOUS-INTAKE",
        "authority_effect": "NONE",
    }
    return {**body, "rehearsal_sha256": canonical_sha256(body)}
