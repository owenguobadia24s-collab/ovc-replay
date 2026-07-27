from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .models import C2Snapshot, PatternDiscoveryError, SourceBindingError, parse_utc
from .triggers import build_trigger_event


EVALUATOR_VERSION = "PD.TRIGGER_EVALUATOR.v0.1"

BOUNDARY_VALUES = {
    "UPPER_REGION",
    "LOWER_REGION",
    "NEAR_UPPER_BOUNDARY",
    "NEAR_LOWER_BOUNDARY",
    "AT_UPPER_BOUNDARY",
    "AT_LOWER_BOUNDARY",
}
BREACH_VALUES = {"BREACH", "BREACH_ACTIVE", "CROSSING"}
RETURN_INSIDE_VALUES = {"INSIDE", "RETURNED_INSIDE", "RECLAIMED_INSIDE"}
COMPRESSION_VALUES = {"COMPRESSION", "COMPRESSED", "COMPRESSING"}
DISPLACEMENT_VALUES = {"DISPLACEMENT", "UP_DISPLACEMENT", "DOWN_DISPLACEMENT", "UP_PROGRESS", "DOWN_PROGRESS"}
UP_VALUES = {"UPPER_REGION", "NEAR_UPPER_BOUNDARY", "AT_UPPER_BOUNDARY", "UP_PROGRESS", "UP_DISPLACEMENT"}
DOWN_VALUES = {"LOWER_REGION", "NEAR_LOWER_BOUNDARY", "AT_LOWER_BOUNDARY", "DOWN_PROGRESS", "DOWN_DISPLACEMENT"}

TRIGGER_META = {
    "TR-LOC-001": ("STRUCTURAL_TRANSITION", "BOUNDARY_ZONE_ENTRY", "CP-BOUNDARY-RESOLUTION", "BOUNDARY_INTERACTION"),
    "TR-INT-001": ("STRUCTURAL_TRANSITION", "BREACH_ACTIVE", "CP-BOUNDARY-RESOLUTION", "BOUNDARY_INTERACTION"),
    "TR-INT-002": ("STRUCTURAL_TRANSITION", "RETURN_INSIDE", "CP-STABLE-RESOLUTION", "BOUNDARY_INTERACTION"),
    "TR-ORG-001": ("STRUCTURAL_TRANSITION", "COMPRESSION_TO_DISPLACEMENT", "CP-STABLE-RESOLUTION", "ORGANISATION_MOTION"),
    "TR-XSC-001": ("CROSS_SCALE_CONFLICT", "LOCAL_PARENT_CONFLICT", "CP-CROSS-SCALE-RESOLUTION", "CROSS_SCALE"),
    "TR-XSC-002": ("CROSS_SCALE_CONFLICT", "ALIGNMENT_GAINED", "CP-STABLE-RESOLUTION", "CROSS_SCALE"),
    "TR-PER-001": ("PERSISTENCE_OR_INSTABILITY", "LONG_PERSISTENCE", "CP-RETURN_OR-MAX-DURATION", "PERSISTENCE"),
    "TR-INS-001": ("PERSISTENCE_OR_INSTABILITY", "REPEATED_SWITCHING", "CP-STABLE-RESOLUTION", "INSTABILITY"),
}


@dataclass(frozen=True)
class TriggerEvaluation:
    trigger_id: str
    family: str
    reason_code: str
    status: str
    first_valid_at: str
    source_transition_ids: tuple[str, ...]
    closure_profile_id: str
    rate_limit_group: str
    evaluator_version: str = EVALUATOR_VERSION
    not_evaluable_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "family": self.family,
            "reason_code": self.reason_code,
            "status": self.status,
            "first_valid_at": self.first_valid_at,
            "source_transition_ids": list(self.source_transition_ids),
            "closure_profile_id": self.closure_profile_id,
            "rate_limit_group": self.rate_limit_group,
            "evaluator_version": self.evaluator_version,
            "not_evaluable_reason": self.not_evaluable_reason,
        }


def _axis_value(snapshot: C2Snapshot, axis: str) -> str | None:
    payload = snapshot.axes[axis]
    if payload.get("status") != "EVALUATED":
        return None
    value = payload.get("value")
    return None if value is None else str(value)


def _transition_ids(transitions: Iterable[Mapping[str, Any]], domains: Iterable[str]) -> tuple[str, ...]:
    wanted = set(domains)
    ids = sorted(
        str(item["transition_id"])
        for item in transitions
        if str(item.get("axis_or_relation")) in wanted and item.get("transition_id")
    )
    return tuple(ids)


def _result(trigger_id: str, status: str, first_valid_at: str, transition_ids: tuple[str, ...], *, reason: str | None = None) -> TriggerEvaluation:
    family, reason_code, closure, rate_group = TRIGGER_META[trigger_id]
    return TriggerEvaluation(
        trigger_id=trigger_id,
        family=family,
        reason_code=reason_code,
        status=status,
        first_valid_at=first_valid_at,
        source_transition_ids=transition_ids,
        closure_profile_id=closure,
        rate_limit_group=rate_group,
        not_evaluable_reason=reason,
    )


def evaluate_transition_triggers(
    previous_record: Mapping[str, Any] | C2Snapshot,
    current_record: Mapping[str, Any] | C2Snapshot,
    transitions: Sequence[Mapping[str, Any]],
) -> list[TriggerEvaluation]:
    previous = previous_record if isinstance(previous_record, C2Snapshot) else C2Snapshot.from_mapping(previous_record)
    current = current_record if isinstance(current_record, C2Snapshot) else C2Snapshot.from_mapping(current_record)
    if previous.binding_key != current.binding_key:
        raise SourceBindingError("trigger evaluation requires one exact C2 source binding")
    if parse_utc(current.first_valid_time) <= parse_utc(previous.first_valid_time):
        raise PatternDiscoveryError("trigger evaluation requires increasing first-valid chronology")

    location_ids = _transition_ids(transitions, {"AXIS.LOCATION", "RELATION_SET", "BOUNDARY_OR_RELATION"})
    interaction_ids = _transition_ids(transitions, {"AXIS.INTERACTION", "RELATION_SET", "BOUNDARY_OR_RELATION"})
    organisation_ids = _transition_ids(transitions, {"AXIS.ORGANISATION", "AXIS.MOTION"})

    previous_location = _axis_value(previous, "LOCATION")
    current_location = _axis_value(current, "LOCATION")
    previous_interaction = _axis_value(previous, "INTERACTION")
    current_interaction = _axis_value(current, "INTERACTION")
    previous_organisation = _axis_value(previous, "ORGANISATION")
    current_motion = _axis_value(current, "MOTION")

    results: list[TriggerEvaluation] = []
    if previous_location is None or current_location is None:
        results.append(_result("TR-LOC-001", "NOT_EVALUABLE", current.first_valid_time, location_ids, reason="LOCATION_NOT_EVALUABLE"))
    else:
        fired = current_location in BOUNDARY_VALUES and previous_location not in BOUNDARY_VALUES and bool(location_ids)
        results.append(_result("TR-LOC-001", "FIRED" if fired else "NOT_FIRED", current.first_valid_time, location_ids))

    if previous_interaction is None or current_interaction is None:
        results.append(_result("TR-INT-001", "NOT_EVALUABLE", current.first_valid_time, interaction_ids, reason="INTERACTION_NOT_EVALUABLE"))
        results.append(_result("TR-INT-002", "NOT_EVALUABLE", current.first_valid_time, interaction_ids, reason="INTERACTION_NOT_EVALUABLE"))
    else:
        breach = current_interaction in BREACH_VALUES and previous_interaction not in BREACH_VALUES and bool(interaction_ids)
        returned = previous_interaction in BREACH_VALUES and current_interaction in RETURN_INSIDE_VALUES and bool(interaction_ids)
        results.append(_result("TR-INT-001", "FIRED" if breach else "NOT_FIRED", current.first_valid_time, interaction_ids))
        results.append(_result("TR-INT-002", "FIRED" if returned else "NOT_FIRED", current.first_valid_time, interaction_ids))

    if previous_organisation is None or current_motion is None:
        results.append(_result("TR-ORG-001", "NOT_EVALUABLE", current.first_valid_time, organisation_ids, reason="ORGANISATION_OR_MOTION_NOT_EVALUABLE"))
    else:
        fired = previous_organisation in COMPRESSION_VALUES and current_motion in DISPLACEMENT_VALUES and bool(organisation_ids)
        results.append(_result("TR-ORG-001", "FIRED" if fired else "NOT_FIRED", current.first_valid_time, organisation_ids))

    return results


def _direction(snapshot: C2Snapshot) -> str | None:
    for axis in ("LOCATION", "MOTION"):
        value = _axis_value(snapshot, axis)
        if value in UP_VALUES:
            return "UP"
        if value in DOWN_VALUES:
            return "DOWN"
    return None


def evaluate_cross_scale_triggers(
    previous_local_record: Mapping[str, Any] | C2Snapshot,
    current_local_record: Mapping[str, Any] | C2Snapshot,
    previous_parent_record: Mapping[str, Any] | C2Snapshot,
    current_parent_record: Mapping[str, Any] | C2Snapshot,
    source_transitions: Sequence[Mapping[str, Any]],
) -> list[TriggerEvaluation]:
    previous_local = previous_local_record if isinstance(previous_local_record, C2Snapshot) else C2Snapshot.from_mapping(previous_local_record)
    current_local = current_local_record if isinstance(current_local_record, C2Snapshot) else C2Snapshot.from_mapping(current_local_record)
    previous_parent = previous_parent_record if isinstance(previous_parent_record, C2Snapshot) else C2Snapshot.from_mapping(previous_parent_record)
    current_parent = current_parent_record if isinstance(current_parent_record, C2Snapshot) else C2Snapshot.from_mapping(current_parent_record)
    if current_local.c2_release_id != current_parent.c2_release_id or current_local.side != current_parent.side:
        raise SourceBindingError("cross-scale evaluation requires the same release and price side")
    if current_local.parent_container_id == "UNRESOLVED" or current_parent.parent_container_id == "UNRESOLVED":
        ids = _transition_ids(source_transitions, {"AXIS.LOCATION", "AXIS.MOTION", "PARENT_CONTAINER", "RELATION_SET"})
        return [
            _result("TR-XSC-001", "NOT_EVALUABLE", current_local.first_valid_time, ids, reason="PARENT_CONTEXT_UNAVAILABLE"),
            _result("TR-XSC-002", "NOT_EVALUABLE", current_local.first_valid_time, ids, reason="PARENT_CONTEXT_UNAVAILABLE"),
        ]

    previous_local_direction = _direction(previous_local)
    previous_parent_direction = _direction(previous_parent)
    current_local_direction = _direction(current_local)
    current_parent_direction = _direction(current_parent)
    ids = _transition_ids(source_transitions, {"AXIS.LOCATION", "AXIS.MOTION", "PARENT_CONTAINER", "RELATION_SET"})
    if current_local_direction is None or current_parent_direction is None:
        return [
            _result("TR-XSC-001", "NOT_EVALUABLE", current_local.first_valid_time, ids, reason="CROSS_SCALE_DIRECTION_NOT_EVALUABLE"),
            _result("TR-XSC-002", "NOT_EVALUABLE", current_local.first_valid_time, ids, reason="CROSS_SCALE_DIRECTION_NOT_EVALUABLE"),
        ]
    previous_conflict = (
        previous_local_direction is not None
        and previous_parent_direction is not None
        and previous_local_direction != previous_parent_direction
    )
    current_conflict = current_local_direction != current_parent_direction
    return [
        _result("TR-XSC-001", "FIRED" if current_conflict and not previous_conflict else "NOT_FIRED", current_local.first_valid_time, ids),
        _result("TR-XSC-002", "FIRED" if previous_conflict and not current_conflict else "NOT_FIRED", current_local.first_valid_time, ids),
    ]


def evaluate_persistence_trigger(
    history_records: Sequence[Mapping[str, Any] | C2Snapshot],
    source_transitions: Sequence[Mapping[str, Any]],
    *,
    axis: str = "MOTION",
    threshold: int = 4,
) -> TriggerEvaluation:
    if threshold < 2:
        raise ValueError("persistence threshold must be at least two")
    snapshots = [item if isinstance(item, C2Snapshot) else C2Snapshot.from_mapping(item) for item in history_records]
    if not snapshots:
        raise PatternDiscoveryError("persistence evaluation requires history")
    current = snapshots[-1]
    values = [_axis_value(item, axis) for item in snapshots]
    if values[-1] is None:
        return _result("TR-PER-001", "NOT_EVALUABLE", current.first_valid_time, _transition_ids(source_transitions, {f"AXIS.{axis}"}), reason=f"{axis}_NOT_EVALUABLE")
    run = 0
    for value in reversed(values):
        if value == values[-1]:
            run += 1
        else:
            break
    previous_run = max(run - 1, 0)
    fired = run >= threshold and previous_run < threshold
    return _result("TR-PER-001", "FIRED" if fired else "NOT_FIRED", current.first_valid_time, _transition_ids(source_transitions, {f"AXIS.{axis}"}))


def evaluate_switching_trigger(
    history_records: Sequence[Mapping[str, Any] | C2Snapshot],
    source_transitions: Sequence[Mapping[str, Any]],
    *,
    axis: str = "MOTION",
    lookback: int = 6,
    switch_threshold: int = 3,
) -> TriggerEvaluation:
    if lookback < 2 or switch_threshold < 1:
        raise ValueError("invalid switching configuration")
    snapshots = [item if isinstance(item, C2Snapshot) else C2Snapshot.from_mapping(item) for item in history_records]
    if not snapshots:
        raise PatternDiscoveryError("switching evaluation requires history")
    selected = snapshots[-lookback:]
    values = [_axis_value(item, axis) for item in selected]
    current = selected[-1]
    if any(value is None for value in values):
        return _result("TR-INS-001", "NOT_EVALUABLE", current.first_valid_time, _transition_ids(source_transitions, {f"AXIS.{axis}"}), reason=f"{axis}_HISTORY_NOT_EVALUABLE")
    switches = sum(1 for before, after in zip(values, values[1:]) if before != after)
    prior_switches = sum(1 for before, after in zip(values[:-1], values[1:-1]) if before != after)
    fired = switches >= switch_threshold and prior_switches < switch_threshold
    return _result("TR-INS-001", "FIRED" if fired else "NOT_FIRED", current.first_valid_time, _transition_ids(source_transitions, {f"AXIS.{axis}"}))


def materialize_fired_events(
    evaluations: Iterable[TriggerEvaluation],
    transitions: Sequence[Mapping[str, Any]],
    *,
    operation_mode: str,
) -> list[dict[str, Any]]:
    transition_map = {str(item.get("transition_id")): item for item in transitions}
    events: list[dict[str, Any]] = []
    for evaluation in evaluations:
        if evaluation.status != "FIRED":
            continue
        sources = [transition_map[item] for item in evaluation.source_transition_ids if item in transition_map]
        if not sources:
            raise PatternDiscoveryError(f"fired trigger {evaluation.trigger_id} has no resolvable source transition")
        events.append(
            build_trigger_event(
                trigger_id=evaluation.trigger_id,
                reason_code=evaluation.reason_code,
                source_transitions=sources,
                operation_mode=operation_mode,
                closure_profile_id=evaluation.closure_profile_id,
                rate_limit_group=evaluation.rate_limit_group,
                first_valid_at=evaluation.first_valid_at,
            )
        )
    return sorted(events, key=lambda item: (item["first_valid_at"], item["trigger_event_id"]))
