from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .canonical import canonical_sha256


class DuplicateRecordIdError(ValueError):
    pass


def _identity_material(record: dict[str, Any]) -> dict[str, Any]:
    material = deepcopy(record)
    material.pop("record_id", None)
    material.pop("content_sha256", None)
    return material


def deterministic_record_id(record: dict[str, Any]) -> str:
    record_type = str(record.get("record_type", "unknown")).lower()
    return f"ro:{record_type}:{canonical_sha256(_identity_material(record))}"


@dataclass
class RecordIdRegistry:
    _ids: set[str] = field(default_factory=set)

    def add(self, record_id: str) -> None:
        if record_id in self._ids:
            raise DuplicateRecordIdError(f"duplicate deterministic record id: {record_id}")
        self._ids.add(record_id)
