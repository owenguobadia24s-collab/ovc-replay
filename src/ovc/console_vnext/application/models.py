from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping


class Availability(str, Enum):
    AVAILABLE = "AVAILABLE"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"
    AUTHORITY_DENIED = "AUTHORITY_DENIED"
    UPSTREAM_READ_MODEL_GAP = "UPSTREAM_READ_MODEL_GAP"
    SOURCE_IDENTITY_CONFLICT = "SOURCE_IDENTITY_CONFLICT"


@dataclass(frozen=True)
class SourceIdentity:
    commit: str
    release_id: str | None = None
    contract_ids: tuple[str, ...] = ()
    schema_ids: tuple[str, ...] = ()
    logical_hashes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Blocker:
    reason_code: str
    owner_programme: str | None = None
    decision_ref: str | None = None
    evidence_ref: str | None = None


@dataclass(frozen=True)
class ConsoleResource:
    resource_type: str
    availability: Availability
    authorised: bool
    active: bool
    authority_effect: str
    source_identity: SourceIdentity
    payload: Mapping[str, Any] | None = None
    blockers: tuple[Blocker, ...] = ()
    dependencies: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "availability": self.availability.value,
            "authorised": self.authorised,
            "active": self.active,
            "authority_effect": self.authority_effect,
            "source_identity": self.source_identity.to_dict(),
            "payload": dict(self.payload) if self.payload is not None else None,
            "blockers": [asdict(item) for item in self.blockers],
            "dependencies": list(self.dependencies),
        }
