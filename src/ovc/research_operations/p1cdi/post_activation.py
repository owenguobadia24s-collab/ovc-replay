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

REHEARSAL_OPERATIONS = frozenset({
    "SOURCE_EXPLICIT_EXACT_INTAKE",
    "EXACT_DUPLICATE",
    "SAME_GENERATION_EVIDENCE_ATTACHMENT",
})


class PostActivationError(ValueError):
    pass


def _git_sha(value: str, field: str) -> str:
    if type(value) is not str or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise PostActivationError(f"{field} must be an exact lowercase git SHA")
    return value


def _sha256(value: str, field: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise PostActivationError(f"{field} must be an exact lowercase SHA-256")
    return value


def _count(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise PostActivationError(f"{field} must be a non-negative integer")
    return value


def build_operational_observation(
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
    activation_receipt_ref: str,
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    _git_sha(repository_commit, "repository_commit")
    _git_sha(repository_tree, "repository_tree")
    if type(source_census_id) is not str or not source_census_id.startswith("P1CDI-G0-SOURCE-CENSUS:"):
        raise PostActivationError("source_census_id is invalid")
    _sha256(source_census_sha256, "source_census_sha256")
    if type(source_completeness_manifest_id) is not str or not source_completeness_manifest_id.startswith(
        "P1CDI-G0-SOURCE-COMPLETENESS:"
    ):
        raise PostActivationError("source_completeness_manifest_id is invalid")
    _sha256(source_completeness_sha256, "source_completeness_sha256")
    _count(expected_subject_count, "expected_subject_count")
    _count(reconciled_subject_count, "reconciled_subject_count")
    if currentness_state not in {"CURRENT", "STALE", "UNRESOLVED"}:
        raise PostActivationError("currentness_state is invalid")
    for field, value in (
        ("reference_optimized_equivalent", reference_optimized_equivalent),
        ("source_identity_drift", source_identity_drift),
        ("owner_semantic_conflict", owner_semantic_conflict),
        ("index_integrity_ok", index_integrity_ok),
        ("capacity_complete", capacity_complete),
    ):
        if type(value) is not bool:
            raise PostActivationError(f"{field} must be boolean")
    _count(protected_source_leak_count, "protected_source_leak_count")
    _count(validation_leak_count, "validation_leak_count")
    _count(candidate_authority_survivor_count, "candidate_authority_survivor_count")
    if type(activation_receipt_ref) is not str or "P1CDII_G_OBSERVABILITY_ACTIVATE_ACTIVATION_RECEIPT" not in activation_receipt_ref:
        raise PostActivationError("activation_receipt_ref is invalid")
    warning_list = sorted(set(warnings))
    if len(warning_list) != len(warnings) or any(type(value) is not str or not value for value in warning_list):
        raise PostActivationError("warnings must be unique non-empty strings")
    body = {
        "schema": "ovc-p1cdii-post-activation-observation/v0.1",
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
        raise PostActivationError("unknown incident class")
    body = {
        "schema": "ovc-p1cdii-post-activation-evaluation/v0.1",
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
    if not observations:
        raise PostActivationError("at least one operational observation is required")
    rows: list[dict[str, Any]] = []
    for observation in observations:
        evaluation = evaluate_operational_incidents(observation)
        rows.append({
            "observation_sha256": observation["observation_sha256"],
            "repository_commit": observation["repository_commit"],
            "repository_tree": observation["repository_tree"],
            "source_census_id": observation["source_census_id"],
            "evaluation": evaluation,
        })
    rows.sort(key=lambda row: (row["repository_commit"], row["observation_sha256"]))
    body = {
        "schema": "ovc-p1cdii-post-activation-monitoring-ledger/v0.1",
        "rows": rows,
        "all_stable": all(row["evaluation"]["status"] == "PASS_OPERATIONAL_STABLE" for row in rows),
        "operational_reliance_scope": "READ_ONLY_CURRENT_PROJECTION_EXACT_SCOPE_ONLY",
        "durable_write_effect": False,
        "next_reserved_gate": "P1CDII-G-CONTINUOUS-INTAKE",
        "authority_effect": "NONE",
    }
    return {**body, "ledger_sha256": canonical_sha256(body)}


def build_rehearsal_record(
    *,
    operation: str,
    source_id: str,
    generation_id: str,
    subject_ref: str,
    evidence_sha256: str,
) -> dict[str, Any]:
    if operation not in REHEARSAL_OPERATIONS:
        raise PostActivationError("rehearsal operation is not authorised")
    for field, value in (("source_id", source_id), ("generation_id", generation_id), ("subject_ref", subject_ref)):
        if type(value) is not str or not value:
            raise PostActivationError(f"{field} is required")
    _sha256(evidence_sha256, "evidence_sha256")
    identity = {
        "operation": operation,
        "source_id": source_id,
        "generation_id": generation_id,
        "subject_ref": subject_ref,
        "evidence_sha256": evidence_sha256,
    }
    record_id = f"p1cdi:rehearsal:{canonical_sha256(identity)}"
    body = {
        "schema": "ovc-p1cdii-minimal-intake-rehearsal-record/v0.1",
        "record_id": record_id,
        **identity,
        "exact_dedupe_key": canonical_sha256({"source_id": source_id, "generation_id": generation_id, "subject_ref": subject_ref}),
        "source_explicit": True,
        "same_generation_only": True,
        "write_activation": False,
        "scientific_effect": "NONE",
        "candidate_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {**body, "content_sha256": canonical_sha256(body)}


def rehearse_minimal_exact_intake(
    records: Sequence[Mapping[str, Any]],
    *,
    durable_target: str | None = None,
) -> dict[str, Any]:
    if durable_target is not None:
        raise PostActivationError("durable targets are forbidden before P1CDII-G-CONTINUOUS-INTAKE")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise PostActivationError("rehearsal record must be an object")
        operation = record.get("operation")
        if operation not in REHEARSAL_OPERATIONS:
            raise PostActivationError("rehearsal operation is not authorised")
        expected = canonical_sha256({key: value for key, value in record.items() if key != "content_sha256"})
        if record.get("content_sha256") != expected:
            raise PostActivationError("record content hash mismatch")
        record_id = record.get("record_id")
        if type(record_id) is not str or not record_id or record_id in seen:
            raise PostActivationError("record identity is missing or duplicated")
        if record.get("source_explicit") is not True or record.get("same_generation_only") is not True:
            raise PostActivationError("rehearsal record is not source-explicit same-generation only")
        if record.get("write_activation") is not False:
            raise PostActivationError("write activation is forbidden before continuous-intake gate")
        if record.get("scientific_effect") != "NONE" or record.get("candidate_effect") != "NONE" or record.get("authority_effect") != "NONE":
            raise PostActivationError("rehearsal record carries forbidden authority or scientific effect")
        seen.add(record_id)
        normalized.append({
            "record_id": record_id,
            "operation": operation,
            "source_id": record["source_id"],
            "generation_id": record["generation_id"],
            "subject_ref": record["subject_ref"],
            "exact_dedupe_key": record["exact_dedupe_key"],
            "content_sha256": record["content_sha256"],
        })
    normalized.sort(key=lambda row: row["record_id"])
    body = {
        "schema": "ovc-p1cdii-minimal-exact-intake-rehearsal/v0.1",
        "storage_scope": "EPHEMERAL_IN_MEMORY_ONLY",
        "allowed_rehearsed_operations": sorted(REHEARSAL_OPERATIONS),
        "record_count": len(normalized),
        "records": normalized,
        "ephemeral_image_sha256": canonical_sha256(normalized),
        "replay_equal": True,
        "durable_target": None,
        "durable_write_attempted": False,
        "durable_write_performed": False,
        "write_activation": False,
        "scientific_effect": "NONE",
        "candidate_effect": "NONE",
        "execution_authority": "NONE",
        "next_reserved_gate": "P1CDII-G-CONTINUOUS-INTAKE",
        "authority_effect": "NONE",
    }
    return {**body, "rehearsal_sha256": canonical_sha256(body)}
