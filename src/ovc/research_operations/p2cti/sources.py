from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_RESOLUTION_STATES = frozenset({"RESOLVED", "UNRESOLVED", "CONFLICT", "UNAVAILABLE"})
_EVIDENCE_FIELDS = frozenset(
    {
        "object_type",
        "predicate",
        "owner_programme",
        "source_ref",
        "semantic_generation",
        "source_sha256",
        "authority_refs",
        "resolution_state",
    }
)


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


def _owner_policy(
    registry: Mapping[str, Any], object_type: str, predicate: str
) -> str:
    if registry.get("schema") != "ovc-p2cti-owner-source-registry/v0.1":
        raise ValueError("P2CTI owner-source registry schema is required")
    matches = [
        item
        for item in registry.get("owners", [])
        if isinstance(item, Mapping)
        and item.get("object_type") == object_type
        and predicate in item.get("high_risk_predicates", [])
    ]
    if len(matches) != 1:
        raise ValueError(f"exactly one declared owner is required for {object_type}:{predicate}")
    owner = str(matches[0].get("owner", ""))
    if not owner:
        raise ValueError(f"declared owner is missing for {object_type}:{predicate}")
    return owner


def _normalized_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if set(evidence) != _EVIDENCE_FIELDS:
        raise ValueError("owner evidence must use the exact closed field set")
    state = str(evidence["resolution_state"])
    if state not in _RESOLUTION_STATES:
        raise ValueError(f"invalid owner resolution_state: {state}")
    digest = str(evidence["source_sha256"])
    if not _HASH_RE.fullmatch(digest):
        raise ValueError("source_sha256 must be a lowercase SHA-256 hex digest")
    authority_refs = evidence["authority_refs"]
    if not isinstance(authority_refs, Sequence) or isinstance(authority_refs, (str, bytes)):
        raise ValueError("authority_refs must be a sequence")
    refs = sorted(str(value) for value in authority_refs)
    if len(refs) != len(set(refs)):
        raise ValueError("authority_refs must be unique")
    normalized = {name: evidence[name] for name in sorted(_EVIDENCE_FIELDS)}
    normalized["authority_refs"] = refs
    for name in ("object_type", "predicate", "owner_programme", "source_ref", "semantic_generation"):
        if not str(normalized[name]):
            raise ValueError(f"{name} must be non-empty")
    return normalized


def resolve_owner_predicate(
    *,
    object_type: str,
    predicate: str,
    evidence: Sequence[Mapping[str, Any]],
    owner_registry: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve a high-risk predicate from its declared owner without fallback.

    Recency, title, path and convenience fields are rejected by the closed
    evidence shape. Missing, mixed or competing owner evidence fails closed.
    The result is advisory until the independent P2CTII-G2-ALG review passes.
    """

    declared_owner = _owner_policy(owner_registry, object_type, predicate)
    rows = [
        _normalized_evidence(item)
        for item in evidence
        if item.get("object_type") == object_type and item.get("predicate") == predicate
    ]
    controlling_owner = declared_owner
    if declared_owner == "DECLARED_AUTHORITY_OWNER" and rows:
        observed_owners = {str(item["owner_programme"]) for item in rows}
        if len(observed_owners) == 1:
            controlling_owner = next(iter(observed_owners))
    wrong_owner = [
        item
        for item in rows
        if declared_owner != "DECLARED_AUTHORITY_OWNER"
        and item["owner_programme"] != declared_owner
    ]
    observed_owners = {str(item["owner_programme"]) for item in rows}
    if wrong_owner or (declared_owner == "DECLARED_AUTHORITY_OWNER" and len(observed_owners) > 1):
        return _resolution(
            object_type, predicate, controlling_owner, "CONFLICT", None,
            ["STATE_OWNER_CONFLICT"]
        )
    if not rows:
        return _resolution(
            object_type, predicate, controlling_owner, "UNRESOLVED", None,
            ["OWNER_SOURCE_MISSING"]
        )
    if any(item["resolution_state"] == "CONFLICT" for item in rows):
        return _resolution(
            object_type, predicate, controlling_owner, "CONFLICT", None,
            ["STATE_OWNER_CONFLICT"]
        )
    if any(item["resolution_state"] != "RESOLVED" for item in rows):
        return _resolution(
            object_type, predicate, controlling_owner, "UNRESOLVED", None,
            ["CURRENTNESS_UNRESOLVED"]
        )
    identities = {
        (
            str(item["source_ref"]),
            str(item["semantic_generation"]),
            str(item["source_sha256"]),
            tuple(item["authority_refs"]),
        )
        for item in rows
    }
    if len(identities) != 1:
        return _resolution(
            object_type, predicate, controlling_owner, "CONFLICT", None,
            ["STATE_OWNER_CONFLICT"]
        )
    selected = sorted(
        rows,
        key=lambda item: (
            str(item["source_ref"]),
            str(item["semantic_generation"]),
            str(item["source_sha256"]),
        ),
    )[0]
    return _resolution(
        object_type, predicate, controlling_owner, "RESOLVED", selected, []
    )


def _resolution(
    object_type: str,
    predicate: str,
    controlling_owner: str,
    state: str,
    source: Mapping[str, Any] | None,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "object_type": object_type,
        "predicate": predicate,
        "controlling_owner": controlling_owner,
        "resolution_state": state,
        "resolved_source": dict(source) if source is not None else None,
        "semantic_generation": (
            str(source["semantic_generation"]) if source is not None else None
        ),
        "visibility_state": "REFERENCE_ONLY",
        "completeness_state": "COMPLETE" if state == "RESOLVED" else "UNRESOLVED",
        "warnings": warnings,
        "decision_bearing": False,
        "authority_effect": "NONE",
    }
