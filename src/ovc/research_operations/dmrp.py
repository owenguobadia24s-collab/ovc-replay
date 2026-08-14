from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .canonical import canonical_sha256

DMRP_SCHEMA_VERSION = "0.2"
DMRP_RECORD_TYPES = frozenset({
    "DMRP_STUDY",
    "EVIDENCE_CYCLE_GENERATION",
    "RESEARCH_QUESTION_RECORD",
    "PRIOR_RESEARCH_EXPOSURE_DISCLOSURE",
    "UPSTREAM_DESIGN_EXPOSURE_RECORD",
})
RESEARCH_MODES = frozenset({"PATH_1_EMPIRICAL", "PATH_2_THEORY_FORMALISATION"})
RESEARCH_ROLES = frozenset({"DISCOVERY", "DEVELOPMENT", "VALIDATION"})
DEPENDENCY_ROLES = frozenset({"REQUIRED", "OPTIONAL", "CONDITIONAL_REQUIRED", "STRATIFIER", "FILTER", "DISPLAY_ONLY", "PROVENANCE_ONLY", "FORBIDDEN"})
POPULATION_STATES = frozenset({"ADMITTED", "NOT_EVALUABLE", "NOT_COMPARABLE", "CENSORED", "QUARANTINED", "EXCLUDED_BY_FROZEN_RULE"})
DISPOSITIONS = frozenset({"FREEZE_CANDIDATE", "REFINE_WITHIN_DISCOVERY", "REPLICATE_DISCOVERY", "DESCRIPTIVE_INVENTORY_ONLY", "METHOD_DEPENDENT", "REPRESENTATION_DEPENDENT", "CONTEXT_DEPENDENT", "INSUFFICIENT_RECURRENCE", "INSUFFICIENT_SEPARATION", "NO_STABLE_STRUCTURE", "CAPACITY_INCOMPLETE", "QUARANTINED", "REJECT", "UNRESOLVED"})
GENERATION_RELATIONS = frozenset({"INITIAL", "SEMANTIC_SUCCESSOR", "EXECUTION_EQUIVALENT", "SUPERSEDES", "CORRESPONDS_TO"})

_NON_SCIENTIFIC_ENVELOPE_FIELDS = frozenset({
    "record_id", "record_sha256", "created_at", "frozen_at", "operator_id",
    "artifact_refs", "physical_attempt_id", "host", "worker_id", "local_path",
    "restart_id", "irof_semantic_run_id",
})


class FrozenScientificRecordMutationError(ValueError):
    pass


class DMRPRecordValidationError(ValueError):
    pass


def _require_text(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise DMRPRecordValidationError(f"{name} required")
    return text


def scientific_projection(record_type: str, scientific_payload: Mapping[str, Any]) -> dict[str, Any]:
    record_type = _require_text("record_type", record_type)
    if record_type not in DMRP_RECORD_TYPES:
        raise DMRPRecordValidationError(f"unsupported DMRP record_type: {record_type}")
    return {"record_type": record_type, "scientific_payload": deepcopy(dict(scientific_payload))}


def semantic_sha256(record_type: str, scientific_payload: Mapping[str, Any]) -> str:
    return canonical_sha256(scientific_projection(record_type, scientific_payload))


def _record_material(record: Mapping[str, Any]) -> dict[str, Any]:
    material = deepcopy(dict(record))
    material.pop("record_id", None)
    material.pop("record_sha256", None)
    return material


def make_dmrp_record(
    record_type: str,
    scientific_payload: Mapping[str, Any],
    *,
    created_at: str,
    admissible_cutoff: str,
    lifecycle_state: str = "FROZEN",
    authority_effect: str = "NONE",
    authority_state: str = "NONE",
    lineage: Mapping[str, Any] | None = None,
    source_release_refs: tuple[Mapping[str, Any], ...] = (),
    artifact_refs: tuple[Mapping[str, Any], ...] = (),
    operator_id: str = "OVC_SYSTEM",
    physical_attempt_id: str | None = None,
    irof_semantic_run_id: str | None = None,
) -> dict[str, Any]:
    if authority_effect != "NONE" or authority_state != "NONE":
        raise DMRPRecordValidationError("record construction cannot grant authority")
    _require_text("created_at", created_at)
    _require_text("admissible_cutoff", admissible_cutoff)
    _require_text("operator_id", operator_id)
    payload = deepcopy(dict(scientific_payload))
    sem_hash = semantic_sha256(record_type, payload)
    record: dict[str, Any] = {
        "schema_version": DMRP_SCHEMA_VERSION,
        "record_type": record_type,
        "lifecycle_state": lifecycle_state,
        "created_at": created_at,
        "frozen_at": created_at if lifecycle_state == "FROZEN" else None,
        "operator_id": operator_id,
        "admissible_cutoff": admissible_cutoff,
        "source_release_refs": [deepcopy(dict(item)) for item in source_release_refs],
        "artifact_refs": [deepcopy(dict(item)) for item in artifact_refs],
        "missingness": [],
        "lineage": deepcopy(dict(lineage or {"parent": [], "derived_from": [], "supersedes": None, "adjudicates": []})),
        "authority_state": authority_state,
        "authority_effect": authority_effect,
        "reproducibility_state": "NOT_EVALUATED",
        "scientific_payload": payload,
        "semantic_sha256": sem_hash,
        "physical_attempt_id": physical_attempt_id,
        "irof_semantic_run_id": irof_semantic_run_id,
    }
    rec_hash = canonical_sha256(_record_material(record))
    record["record_sha256"] = rec_hash
    record["record_id"] = f"ro:{record_type.lower()}:{rec_hash}"
    return record


def verify_dmrp_record(record: Mapping[str, Any]) -> None:
    if record.get("schema_version") != DMRP_SCHEMA_VERSION:
        raise DMRPRecordValidationError("DMRP schema_version must be 0.2")
    record_type = _require_text("record_type", record.get("record_type"))
    payload = record.get("scientific_payload")
    if not isinstance(payload, Mapping):
        raise DMRPRecordValidationError("scientific_payload must be an object")
    expected_semantic = semantic_sha256(record_type, payload)
    if record.get("semantic_sha256") != expected_semantic:
        raise DMRPRecordValidationError("semantic_sha256 mismatch")
    expected_record = canonical_sha256(_record_material(record))
    if record.get("record_sha256") != expected_record:
        raise DMRPRecordValidationError("record_sha256 mismatch")
    if record.get("record_id") != f"ro:{record_type.lower()}:{expected_record}":
        raise DMRPRecordValidationError("record_id mismatch")
    if record.get("authority_effect") != "NONE" or record.get("authority_state") != "NONE":
        raise DMRPRecordValidationError("DMRP WP1 records carry no authority")


def scientific_identity_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return left.get("semantic_sha256") == right.get("semantic_sha256")


def assert_frozen_record_not_rewritten(existing: Mapping[str, Any], proposed: Mapping[str, Any]) -> None:
    if existing.get("lifecycle_state") == "FROZEN" and existing.get("semantic_sha256") != proposed.get("semantic_sha256"):
        raise FrozenScientificRecordMutationError("frozen scientific record cannot be rewritten; create a successor generation")


def superseding_record(existing: Mapping[str, Any], scientific_payload: Mapping[str, Any], *, created_at: str, admissible_cutoff: str) -> dict[str, Any]:
    lineage = deepcopy(dict(existing.get("lineage") or {}))
    lineage.setdefault("parent", [])
    lineage.setdefault("derived_from", [])
    lineage.setdefault("adjudicates", [])
    lineage["supersedes"] = existing.get("record_id")
    return make_dmrp_record(
        str(existing["record_type"]),
        scientific_payload,
        created_at=created_at,
        admissible_cutoff=admissible_cutoff,
        lineage=lineage,
    )


def identity_plane_manifest(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scientific_object_identity": record.get("semantic_sha256"),
        "research_operations_record_identity": record.get("record_id"),
        "irof_semantic_run_identity": record.get("irof_semantic_run_id"),
        "physical_attempt_or_artifact_identity": record.get("physical_attempt_id"),
    }


def non_scientific_envelope_fields() -> frozenset[str]:
    return _NON_SCIENTIFIC_ENVELOPE_FIELDS
