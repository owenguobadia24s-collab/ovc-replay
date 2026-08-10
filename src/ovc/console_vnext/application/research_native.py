from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping


class DegradedState(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"
    NULL_RESULT = "NULL_RESULT"
    LOCKED = "LOCKED"
    QUARANTINED = "QUARANTINED"
    STALE = "STALE"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    AMBIGUOUS = "AMBIGUOUS"
    CENSORED = "CENSORED"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


@dataclass(frozen=True)
class Identity:
    object_type: str
    object_id: str
    source_commit: str
    release_id: str | None = None


@dataclass(frozen=True)
class InvestigationContext:
    instrument: str | None
    clock: str | None
    cutoff: str | None
    selected_ids: tuple[str, ...]
    source_commit: str


@dataclass(frozen=True)
class EvidencePassport:
    identity: Identity
    authority: str
    first_valid_time: str | None
    availability: str
    missingness: tuple[str, ...] = ()
    qa: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityDependencyStatusV2:
    capability_id: str
    owner_programme: str
    implemented: bool
    materialized: bool
    available: bool
    authorised: bool
    active: bool
    canonical: bool
    validation_admissible: bool
    authority_effect: str
    source_path: str | None = None
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ValidationResolutionDenied(PermissionError):
    pass


def deny_validation_before_resolution(request: Mapping[str, Any]) -> None:
    """Reject protected Validation requests before resolving any locator metadata."""
    if str(request.get("role", "")).upper() == "VALIDATION" or bool(request.get("validation")):
        raise ValidationResolutionDenied("VALIDATION_DENIED_BEFORE_PROTECTED_RESOLUTION")


def degraded(reason: DegradedState, *, owner: str, capability_id: str) -> CapabilityDependencyStatusV2:
    return CapabilityDependencyStatusV2(
        capability_id=capability_id,
        owner_programme=owner,
        implemented=False,
        materialized=False,
        available=False,
        authorised=False,
        active=False,
        canonical=False,
        validation_admissible=False,
        authority_effect="NONE",
        reason_codes=(reason.value,),
    )
