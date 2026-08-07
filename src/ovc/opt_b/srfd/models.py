from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .schema import validate_document
from .serialization import logical_sha256, stable_id


@dataclass(frozen=True)
class SRFDRecord:
    object_type: str
    payload: Mapping[str, Any]
    schema_version: str = "0.1"
    authority_state: str = "FIXTURE_ONLY"
    qa_state: str = "NOT_EVALUATED"

    def to_dict(self) -> dict[str, Any]:
        document = {
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "authority_state": self.authority_state,
            "qa_state": self.qa_state,
            **dict(self.payload),
        }
        validate_document(document)
        return document

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.to_dict())

    def identified(self, prefix: str) -> dict[str, Any]:
        document = self.to_dict()
        return {**document, "object_id": stable_id(prefix, document)}


@dataclass(frozen=True)
class SRFDRegistryEntry:
    registry_id: str
    entry_id: str
    version: str
    status: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    @property
    def logical_hash(self) -> str:
        return logical_sha256({
            "registry_id": self.registry_id,
            "entry_id": self.entry_id,
            "version": self.version,
            "status": self.status,
            "payload": dict(self.payload),
        })
