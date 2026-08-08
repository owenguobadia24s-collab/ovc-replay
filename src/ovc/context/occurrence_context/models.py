from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class OccurrenceAnchorRef:
    anchor_kind: str
    anchor_id: str
    anchor_schema_id: str
    anchor_logical_hash: str
    anchor_first_valid_time: str
    source_release_id: str | None = None
    structural_anchor_ref: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor_kind": self.anchor_kind,
            "anchor_id": self.anchor_id,
            "anchor_schema_id": self.anchor_schema_id,
            "anchor_logical_hash": self.anchor_logical_hash,
            "anchor_first_valid_time": self.anchor_first_valid_time,
            "source_release_id": self.source_release_id,
            "structural_anchor_ref": dict(self.structural_anchor_ref) if self.structural_anchor_ref is not None else None,
        }


@dataclass(frozen=True)
class ContextDependencyRef:
    dependency_kind: str
    record_id: str
    schema_id: str
    logical_hash: str
    first_valid_time: str
    dependency_role: str
    required: bool
    source_release_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependency_kind": self.dependency_kind,
            "record_id": self.record_id,
            "schema_id": self.schema_id,
            "logical_hash": self.logical_hash,
            "first_valid_time": self.first_valid_time,
            "dependency_role": self.dependency_role,
            "source_release_id": self.source_release_id,
            "required": self.required,
        }


@dataclass(frozen=True)
class BuildRequest:
    anchor_ref: OccurrenceAnchorRef
    source_context: Mapping[str, Any]
    research_role: str
    occurrence_interval: Mapping[str, Any]
    calendar_context: Mapping[str, Any]
    session_context: Mapping[str, Any]
    clock_scale_context: Mapping[str, Any]
    confirmation_time: str
    context_pack_id: str = "OC.BASE.NONSTRUCTURAL.v0.1"
    context_pack_version: str = "0.1"
    context_role_map_id: str = "OC.ROLE_MAP.v0.1"
    parent_context_refs: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    market_condition_context: Mapping[str, Any] | None = None
    episode_relative_context: Mapping[str, Any] | None = None
    auxiliary_refs: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    dependency_refs: Sequence[ContextDependencyRef] = field(default_factory=tuple)
    registry_bindings: Mapping[str, Any] = field(default_factory=dict)
    registry_first_valid_times: Sequence[str] = field(default_factory=tuple)
    availability_status: str = "AVAILABLE"
    reason_codes: Sequence[str] = field(default_factory=tuple)
    authority_state: str = "SHADOW"
    lineage: Mapping[str, Any] = field(default_factory=dict)
