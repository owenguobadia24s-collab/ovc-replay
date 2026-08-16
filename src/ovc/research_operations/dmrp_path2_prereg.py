from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .canonical import canonical_sha256

SCHEMA_FAMILY = "DMRP_PATH2_PREREG"
SCHEMA_VERSION = "0.1"
RECORD_TYPES = frozenset({"THEORY_RECORD", "RESEARCH_PROTOCOL", "EXPERIMENT_RECORD"})
_PREFIX = {
    "THEORY_RECORD": "theory",
    "RESEARCH_PROTOCOL": "protocol",
    "EXPERIMENT_RECORD": "experiment",
}


class Path2PreregValidationError(ValueError):
    pass


def _scientific_projection(record_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if record_type not in RECORD_TYPES:
        raise Path2PreregValidationError(f"unsupported record_type: {record_type}")
    return {"record_type": record_type, "scientific_payload": deepcopy(dict(payload))}


def semantic_sha256(record_type: str, payload: Mapping[str, Any]) -> str:
    return canonical_sha256(_scientific_projection(record_type, payload))


def _record_material(record: Mapping[str, Any]) -> dict[str, Any]:
    material = deepcopy(dict(record))
    material.pop("record_id", None)
    material.pop("record_sha256", None)
    return material


def make_path2_prereg_record(
    record_type: str,
    scientific_payload: Mapping[str, Any],
    *,
    physical_attempt_id: str | None = None,
    artifact_refs: tuple[Mapping[str, Any], ...] = (),
) -> dict[str, Any]:
    payload = deepcopy(dict(scientific_payload))
    sem_hash = semantic_sha256(record_type, payload)
    record: dict[str, Any] = {
        "schema_family": SCHEMA_FAMILY,
        "schema_version": SCHEMA_VERSION,
        "record_type": record_type,
        "scientific_payload": payload,
        "semantic_sha256": sem_hash,
        "authority_effect": "NONE",
        "physical_attempt_id": physical_attempt_id,
        "artifact_refs": [deepcopy(dict(item)) for item in artifact_refs],
    }
    rec_hash = canonical_sha256(_record_material(record))
    record["record_sha256"] = rec_hash
    record["record_id"] = f"ro:p2:{_PREFIX[record_type]}:{rec_hash}"
    verify_path2_prereg_record(record)
    return record


def _required(record_type: str) -> frozenset[str]:
    if record_type == "THEORY_RECORD":
        return frozenset({
            "theory_id", "title", "origin_class", "evidence_state", "proposition", "scope",
            "observable_implications", "falsifiers", "measurement_consequences",
            "research_conduct_consequences", "path1_influence",
        })
    if record_type == "RESEARCH_PROTOCOL":
        return frozenset({
            "protocol_id", "theory_id", "title", "question", "lawful_unit", "population", "inputs",
            "metrics", "baselines", "decision_rule", "leakage_controls", "qa_checks",
            "method_parameter_pack_id", "method_parameter_sha256", "protocol_state",
        })
    return frozenset({
        "experiment_id", "protocol_id", "theory_id", "preregistration_state", "preregistered_at",
        "data_release_ids", "code_commit", "config_hash", "sample_binding", "exclusions", "qa_plan",
        "method_parameter_pack_id", "method_parameter_sha256", "dependency_state", "result_artifacts",
        "candidate_formation", "validation",
    })


def verify_path2_prereg_record(record: Mapping[str, Any]) -> None:
    if record.get("schema_family") != SCHEMA_FAMILY or record.get("schema_version") != SCHEMA_VERSION:
        raise Path2PreregValidationError("Path-2 prereg schema family/version mismatch")
    record_type = str(record.get("record_type", ""))
    if record_type not in RECORD_TYPES:
        raise Path2PreregValidationError(f"unsupported record_type: {record_type}")
    if record.get("authority_effect") != "NONE":
        raise Path2PreregValidationError("Path-2 prereg records cannot grant authority")
    payload = record.get("scientific_payload")
    if not isinstance(payload, Mapping):
        raise Path2PreregValidationError("scientific_payload must be an object")
    missing = _required(record_type) - set(payload)
    if missing:
        raise Path2PreregValidationError(f"missing scientific payload fields: {','.join(sorted(missing))}")
    if payload.get("path1_influence") not in (None, "FORBIDDEN_AS_SEED_FILTER_REPAIR_OR_PROMOTION_CRITERION"):
        raise Path2PreregValidationError("Path-1 influence must remain forbidden")
    if record_type == "THEORY_RECORD" and payload.get("evidence_state") != "UNTESTED":
        raise Path2PreregValidationError("external Path-2 theory remains UNTESTED before evidence")
    if record_type == "EXPERIMENT_RECORD":
        state = payload.get("preregistration_state")
        if state not in {"PREREGISTRATION_SHELL_NOT_EFFECTIVE", "NATIVE_BOUND_NOT_EFFECTIVE", "PREREGISTERED_EFFECTIVE"}:
            raise Path2PreregValidationError("invalid preregistration_state")
        if payload.get("result_artifacts"):
            raise Path2PreregValidationError("result_artifacts forbidden before real-source evidentiary authority")
        if payload.get("candidate_formation") != "NOT_EXECUTED":
            raise Path2PreregValidationError("P2-6 candidate formation is not authorized")
        if payload.get("validation") != "LOCKED_UNCONSUMED":
            raise Path2PreregValidationError("Validation must remain locked/unconsumed")
        if state == "PREREGISTERED_EFFECTIVE":
            required_bound = ("preregistered_at", "code_commit", "config_hash", "sample_binding", "qa_plan")
            if any(payload.get(key) in (None, "", "UNBOUND", "PENDING") for key in required_bound):
                raise Path2PreregValidationError("effective preregistration requires exact frozen bindings")
            if not payload.get("data_release_ids"):
                raise Path2PreregValidationError("effective preregistration requires exact data release IDs")
            if payload.get("dependency_state") != "BOUND":
                raise Path2PreregValidationError("effective preregistration requires BOUND dependencies")
    expected_sem = semantic_sha256(record_type, payload)
    if record.get("semantic_sha256") != expected_sem:
        raise Path2PreregValidationError("semantic_sha256 mismatch")
    expected_record = canonical_sha256(_record_material(record))
    if record.get("record_sha256") != expected_record:
        raise Path2PreregValidationError("record_sha256 mismatch")
    expected_id = f"ro:p2:{_PREFIX[record_type]}:{expected_record}"
    if record.get("record_id") != expected_id:
        raise Path2PreregValidationError("record_id mismatch")


def preregistration_effective(payload: Mapping[str, Any]) -> bool:
    return payload.get("preregistration_state") == "PREREGISTERED_EFFECTIVE"
