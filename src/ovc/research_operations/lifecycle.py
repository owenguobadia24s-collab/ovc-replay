from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import canonical_sha256
from .identity import deterministic_record_id
from .validation import RecordValidationError, validate_record


class FrozenRecordMutationError(ValueError):
    def __init__(self, record_id: str):
        self.record_id = record_id
        self.incident = {
            "incident_code": "FROZEN_MUTATION",
            "severity": "BLOCKING",
            "target_id": record_id,
            "description": "Frozen canonical bytes no longer match the recorded identity.",
            "blocking_effect": ["RECORD_USE", "RO_G1"],
        }
        super().__init__(f"frozen record mutation detected: {record_id}")


def _content_material(record: dict[str, Any]) -> dict[str, Any]:
    material = deepcopy(record)
    material.pop("content_sha256", None)
    return material


def freeze_record(record: dict[str, Any], *, frozen_at: str) -> dict[str, Any]:
    if record.get("lifecycle_state") != "DRAFT":
        raise RecordValidationError("INVALID_FREEZE_STATE", str(record.get("lifecycle_state")))
    frozen = deepcopy(record)
    frozen["lifecycle_state"] = "FROZEN"
    frozen["authority_state"] = "FROZEN"
    frozen["frozen_at"] = frozen_at
    frozen.setdefault("model_refs", [])
    frozen["record_id"] = deterministic_record_id(frozen)
    frozen["content_sha256"] = canonical_sha256(_content_material(frozen))
    validate_record(frozen)
    return frozen


def verify_frozen_record(record: dict[str, Any]) -> None:
    if record.get("lifecycle_state") not in {"FROZEN", "ADJUDICATED", "SUPERSEDED"}:
        raise RecordValidationError("NOT_FROZEN", str(record.get("lifecycle_state")))
    expected_hash = canonical_sha256(_content_material(record))
    expected_id = deterministic_record_id(record)
    if record.get("content_sha256") != expected_hash or record.get("record_id") != expected_id:
        raise FrozenRecordMutationError(str(record.get("record_id")))
    validate_record(record)


def supersede_record(original: dict[str, Any], replacement: dict[str, Any], *, frozen_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    verify_frozen_record(original)
    if replacement.get("lifecycle_state") != "DRAFT":
        raise RecordValidationError("REPLACEMENT_NOT_DRAFT", str(replacement.get("lifecycle_state")))
    successor = deepcopy(replacement)
    successor["lineage"]["supersedes"] = original["record_id"]
    return deepcopy(original), freeze_record(successor, frozen_at=frozen_at)
