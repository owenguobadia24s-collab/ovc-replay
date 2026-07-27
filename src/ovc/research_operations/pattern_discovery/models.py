from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
CLOCKS = {"15M", "2H_A_L"}
PRICE_SIDES = {"BID", "ASK"}
OPERATION_MODES = {"LIVE_PROSPECTIVE", "TIME_GATED_REPLAY", "NON_EVIDENTIARY_REPLAY"}


class PatternDiscoveryError(ValueError):
    """Base fail-closed Pattern Discovery validation error."""


class ChronologyError(PatternDiscoveryError):
    """Raised when first-valid chronology is not strictly increasing."""


class SourceBindingError(PatternDiscoveryError):
    """Raised when records from incompatible source bindings are combined."""


class DuplicateDerivedRecordError(PatternDiscoveryError):
    """Raised when an append-only derived ledger sees an existing identity."""


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ChronologyError("timestamp must be an ISO-8601 UTC string ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ChronologyError(f"invalid UTC timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ChronologyError("timestamp must resolve to UTC")
    return parsed


def _required_text(source: Mapping[str, Any], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PatternDiscoveryError(f"{key} must be a non-empty string")
    return value


@dataclass(frozen=True)
class C2Snapshot:
    c2_state_id: str
    c2_release_id: str
    c2_manifest_id: str
    first_valid_time: str
    clock: str
    side: str
    evaluation_scope_id: str
    parameter_pack_id: str
    axes: Mapping[str, Mapping[str, Any]]
    relation_set_id: str
    level_ids: tuple[str, ...]
    container_ids: tuple[str, ...]
    parent_container_id: str
    boundary_or_relation_id: str
    authority_state: str
    selector_id: str
    gap_before: bool

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any]) -> "C2Snapshot":
        clock = _required_text(source, "clock")
        side = _required_text(source, "side")
        if clock not in CLOCKS:
            raise PatternDiscoveryError(f"unsupported clock: {clock}")
        if side not in PRICE_SIDES:
            raise PatternDiscoveryError(f"unsupported price side: {side}")
        first_valid_time = _required_text(source, "first_valid_time")
        parse_utc(first_valid_time)
        axes = source.get("axes")
        if not isinstance(axes, Mapping):
            raise PatternDiscoveryError("axes must be an object")
        missing_axes = [axis for axis in AXES if axis not in axes]
        if missing_axes:
            raise PatternDiscoveryError(f"missing C2 axes: {missing_axes}")
        normalized_axes: dict[str, Mapping[str, Any]] = {}
        for axis in AXES:
            payload = axes[axis]
            if not isinstance(payload, Mapping):
                raise PatternDiscoveryError(f"axis {axis} must be an object")
            status = payload.get("status")
            if not isinstance(status, str) or not status:
                raise PatternDiscoveryError(f"axis {axis} requires status")
            normalized_axes[axis] = dict(payload)
        level_ids = tuple(sorted(str(item) for item in source.get("level_ids", ())))
        container_ids = tuple(sorted(str(item) for item in source.get("container_ids", ())))
        return cls(
            c2_state_id=_required_text(source, "c2_state_id"),
            c2_release_id=_required_text(source, "c2_release_id"),
            c2_manifest_id=_required_text(source, "c2_manifest_id"),
            first_valid_time=first_valid_time,
            clock=clock,
            side=side,
            evaluation_scope_id=_required_text(source, "evaluation_scope_id"),
            parameter_pack_id=_required_text(source, "parameter_pack_id"),
            axes=normalized_axes,
            relation_set_id=_required_text(source, "relation_set_id"),
            level_ids=level_ids,
            container_ids=container_ids,
            parent_container_id=str(source.get("parent_container_id") or "UNRESOLVED"),
            boundary_or_relation_id=str(source.get("boundary_or_relation_id") or source.get("relation_set_id")),
            authority_state=str(source.get("authority_state") or "FIXTURE"),
            selector_id=str(source.get("selector_id") or "FIXTURE_SELECTOR"),
            gap_before=bool(source.get("gap_before", False)),
        )

    @property
    def source_ref(self) -> dict[str, str]:
        return {
            "release_id": self.c2_release_id,
            "manifest_id": self.c2_manifest_id,
            "record_id": self.c2_state_id,
        }

    @property
    def binding_key(self) -> tuple[str, ...]:
        return (
            self.c2_release_id,
            self.c2_manifest_id,
            self.clock,
            self.side,
            self.evaluation_scope_id,
            self.parameter_pack_id,
            self.selector_id,
        )

    @property
    def quality_state(self) -> str:
        payload = self.axes["QUALITY"]
        value = payload.get("value")
        return str(value if value is not None else payload.get("status"))
