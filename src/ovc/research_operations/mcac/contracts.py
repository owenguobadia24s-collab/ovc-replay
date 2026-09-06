from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from ovc.research_orchestration.serialization import logical_sha256, stable_id

PROTECTED_NON_EQUIVALENCE = frozenset({frozenset({"TV120_NATIVE", "2H_A_L"})})
EVALUATION_STATES = frozenset({"EVALUABLE", "RETROSPECTIVE_ONLY", "NOT_EVALUABLE", "NOT_COMPARABLE"})


class MCACContractError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise MCACContractError("MCAC_TIME_NOT_UTC_Z", field)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise MCACContractError("MCAC_TIME_INVALID", field) from exc
    if parsed.tzinfo != timezone.utc:
        raise MCACContractError("MCAC_TIME_NOT_UTC", field)
    return parsed


def ensure_not_alias(left: str, right: str) -> None:
    if frozenset({left, right}) in PROTECTED_NON_EQUIVALENCE:
        raise MCACContractError("MCAC_PROTECTED_CLOCK_ALIAS_REJECTED", f"{left}!={right}")


@dataclass(frozen=True)
class ClockCoordinateIdentity:
    producer_owner: str
    clock_id: str
    generation_id: str
    clock_family: str
    nominal_duration_seconds: int | None
    chronology_basis: str
    first_valid_time_semantics: str
    timezone_basis: str
    session_basis: str
    calendar_basis: str
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("producer_owner", "clock_id", "generation_id", "clock_family", "chronology_basis", "first_valid_time_semantics", "timezone_basis", "session_basis", "calendar_basis"):
            if not str(getattr(self, name)).strip():
                raise MCACContractError("MCAC_CLOCK_FIELD_REQUIRED", name)
        if self.nominal_duration_seconds is not None and self.nominal_duration_seconds <= 0:
            raise MCACContractError("MCAC_CLOCK_DURATION_INVALID", self.clock_id)
        if not self.provenance_refs or any(not value.strip() for value in self.provenance_refs):
            raise MCACContractError("MCAC_CLOCK_PROVENANCE_REQUIRED", self.clock_id)

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "producer_owner": self.producer_owner, "clock_id": self.clock_id,
            "generation_id": self.generation_id, "clock_family": self.clock_family,
            "nominal_duration_seconds": self.nominal_duration_seconds,
            "chronology_basis": self.chronology_basis,
            "first_valid_time_semantics": self.first_valid_time_semantics,
            "timezone_basis": self.timezone_basis, "session_basis": self.session_basis,
            "calendar_basis": self.calendar_basis, "provenance_refs": list(self.provenance_refs),
        }

    @property
    def coordinate_id(self) -> str:
        return stable_id("MCAC.CLOCK.", self.semantic_dict())


@dataclass(frozen=True)
class ClockRegistryEntry:
    coordinate: ClockCoordinateIdentity
    source_authority_ref: str
    comparability_status: str
    registry_revision: str
    effective_fvt: str
    provenance_refs: tuple[str, ...]
    execution_authority_effect: str = "NONE_FROM_REGISTRY"

    def __post_init__(self) -> None:
        if self.execution_authority_effect != "NONE_FROM_REGISTRY":
            raise MCACContractError("MCAC_REGISTRY_AUTHORITY_EFFECT_FORBIDDEN", self.coordinate.clock_id)
        parse_utc(self.effective_fvt, "effective_fvt")
        for name in ("source_authority_ref", "comparability_status", "registry_revision"):
            if not str(getattr(self, name)).strip():
                raise MCACContractError("MCAC_REGISTRY_FIELD_REQUIRED", name)

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "coordinate_id": self.coordinate.coordinate_id,
            "source_authority_ref": self.source_authority_ref,
            "comparability_status": self.comparability_status,
            "registry_revision": self.registry_revision, "effective_fvt": self.effective_fvt,
            "provenance_refs": list(self.provenance_refs),
            "execution_authority_effect": self.execution_authority_effect,
        }

    @property
    def registry_entry_id(self) -> str:
        return stable_id("MCAC.REGISTRY.", self.semantic_dict())


@dataclass(frozen=True)
class ClockIndexedOccurrenceRef:
    occurrence_ref_id: str
    owner_record_id: str
    clock_coordinate_id: str
    clock_registry_entry_id: str
    owner_generation_id: str
    source_authority_ref: str
    source_binding_id: str
    representation_ref: str
    representation_id: str
    representation_generation_id: str
    representation_first_valid_time: str
    representation_adapter_id: str
    interval_kind: str
    interval_start: str
    interval_end: str
    effective_time: str
    first_valid_time: str
    evaluation_cutoff: str
    continuity_segment_id: str | None
    source_gap_state: str = "NONE"
    censoring_state: str = "NONE"
    missingness_state: str = "NONE"
    owner_payload_ref: str = "OPAQUE_NOT_DEREFERENCEABLE"
    owner_payload_hash: str = "OPAQUE"
    validation_access_state: str = "LOCKED_UNCONSUMED"

    def __post_init__(self) -> None:
        for name in ("occurrence_ref_id", "owner_record_id", "clock_coordinate_id", "clock_registry_entry_id", "owner_generation_id", "source_authority_ref", "source_binding_id", "representation_ref", "representation_id", "representation_generation_id", "representation_adapter_id"):
            if not str(getattr(self, name)).strip():
                raise MCACContractError("MCAC_OCCURRENCE_FIELD_REQUIRED", name)
        if self.interval_kind not in {"POINT", "CLOSED_INTERVAL"}:
            raise MCACContractError("MCAC_INTERVAL_KIND_INVALID", self.interval_kind)
        start, end = parse_utc(self.interval_start, "interval_start"), parse_utc(self.interval_end, "interval_end")
        effective, fvt = parse_utc(self.effective_time, "effective_time"), parse_utc(self.first_valid_time, "first_valid_time")
        cutoff = parse_utc(self.evaluation_cutoff, "evaluation_cutoff")
        parse_utc(self.representation_first_valid_time, "representation_first_valid_time")
        if (self.interval_kind == "POINT" and start != end) or (self.interval_kind == "CLOSED_INTERVAL" and start >= end):
            raise MCACContractError("MCAC_INTERVAL_BOUNDS_INVALID", self.occurrence_ref_id)
        if effective > fvt or fvt > cutoff:
            raise MCACContractError("MCAC_OCCURRENCE_FVT_INVALID", self.occurrence_ref_id)
        if self.validation_access_state != "LOCKED_UNCONSUMED":
            raise MCACContractError("MCAC_VALIDATION_STATE_FORBIDDEN", self.validation_access_state)

    @property
    def start(self) -> datetime:
        return parse_utc(self.interval_start, "interval_start")

    @property
    def end(self) -> datetime:
        return parse_utc(self.interval_end, "interval_end")

    def semantic_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.semantic_dict())


@dataclass(frozen=True)
class ComparabilityContext:
    left_coordinate: ClockCoordinateIdentity
    right_coordinate: ClockCoordinateIdentity
    left_registry: ClockRegistryEntry
    right_registry: ClockRegistryEntry
    left_generation_id: str
    right_generation_id: str
    lawful_overlap_start: str
    lawful_overlap_end: str
    evaluation_cutoff: str
    representation_pair: tuple[str, str]
    representation_adapter_ids: tuple[str, str]
    correspondence_rule_id: str
    continuity_policy: str
    doctrine_id: str
    doctrine_hash: str
    dependency_fvts: Mapping[str, str]
    capacity_profile_id: str
    authority_resolved: bool = True

    def __post_init__(self) -> None:
        if not self.authority_resolved:
            raise MCACContractError("MCAC_AUTHORITY_MUST_RESOLVE_IN_IROF", self.correspondence_rule_id)
        ensure_not_alias(self.left_coordinate.clock_id, self.right_coordinate.clock_id)
        if self.left_registry.coordinate.coordinate_id != self.left_coordinate.coordinate_id or self.right_registry.coordinate.coordinate_id != self.right_coordinate.coordinate_id:
            raise MCACContractError("MCAC_REGISTRY_COORDINATE_MISMATCH", self.correspondence_rule_id)
        if self.left_generation_id != self.left_coordinate.generation_id or self.right_generation_id != self.right_coordinate.generation_id:
            raise MCACContractError("MCAC_CONTEXT_GENERATION_MISMATCH", self.correspondence_rule_id)
        if not self.dependency_fvts:
            raise MCACContractError("MCAC_DEPENDENCY_FVT_REQUIRED", self.correspondence_rule_id)
        if parse_utc(self.lawful_overlap_start, "lawful_overlap_start") > parse_utc(self.lawful_overlap_end, "lawful_overlap_end"):
            raise MCACContractError("MCAC_OVERLAP_INVALID", self.correspondence_rule_id)
        parse_utc(self.evaluation_cutoff, "evaluation_cutoff")
        for key, value in self.dependency_fvts.items():
            parse_utc(value, f"dependency_fvts.{key}")

    @property
    def derived_fvt(self) -> str:
        return max(self.dependency_fvts.values(), key=lambda value: parse_utc(value, "dependency_fvt"))

    @property
    def evaluation_state(self) -> str:
        return "EVALUABLE" if parse_utc(self.derived_fvt, "derived_fvt") <= parse_utc(self.evaluation_cutoff, "evaluation_cutoff") else "NOT_EVALUABLE"

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "left_coordinate_id": self.left_coordinate.coordinate_id,
            "right_coordinate_id": self.right_coordinate.coordinate_id,
            "left_registry_entry_id": self.left_registry.registry_entry_id,
            "right_registry_entry_id": self.right_registry.registry_entry_id,
            "left_generation_id": self.left_generation_id, "right_generation_id": self.right_generation_id,
            "lawful_overlap_start": self.lawful_overlap_start, "lawful_overlap_end": self.lawful_overlap_end,
            "evaluation_cutoff": self.evaluation_cutoff, "representation_pair": list(self.representation_pair),
            "representation_adapter_ids": list(self.representation_adapter_ids),
            "correspondence_rule_id": self.correspondence_rule_id, "continuity_policy": self.continuity_policy,
            "doctrine_id": self.doctrine_id, "doctrine_hash": self.doctrine_hash,
            "dependency_fvts": dict(self.dependency_fvts), "capacity_profile_id": self.capacity_profile_id,
        }

    @property
    def context_id(self) -> str:
        return stable_id("MCAC.CONTEXT.", self.semantic_dict())
