from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class OwnerSourceReference:
    """Exact reference to a separately owned scientific/authority object.

    P2CTI uses references rather than copying owner scientific payloads.
    """

    owner_programme: str
    object_type: str
    object_id: str
    semantic_generation: str
    source_path: str
    content_sha256: str
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "owner_programme",
            "object_type",
            "object_id",
            "semantic_generation",
            "source_path",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")
        if not _HASH_RE.fullmatch(self.content_sha256):
            raise ValueError("content_sha256 must be a lowercase SHA-256 hex digest")
        if len(set(self.authority_refs)) != len(self.authority_refs):
            raise ValueError("authority_refs must be unique")

    def as_reference(self) -> dict[str, Any]:
        return {
            "owner_programme": self.owner_programme,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "semantic_generation": self.semantic_generation,
            "source_path": self.source_path,
            "content_sha256": self.content_sha256,
            "authority_refs": list(self.authority_refs),
            "scientific_payload_copied": False,
        }


def require_reference_only(payload: dict[str, Any]) -> None:
    """Fail closed if an adapter tries to embed owner scientific payload."""

    forbidden = {"scientific_payload", "proposition", "falsifiers", "observable_implications"}
    found = sorted(forbidden.intersection(payload))
    if found:
        raise ValueError(f"owner scientific payload must remain owner-local: {found}")
    ref = payload.get("source_object_ref")
    if not isinstance(ref, dict) or ref.get("scientific_payload_copied") is not False:
        raise ValueError("source_object_ref with scientific_payload_copied=false is required")
