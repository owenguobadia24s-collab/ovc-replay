from __future__ import annotations

from typing import Any, Mapping

from ovc.research_operations.canonical import canonical_sha256

from .models import AXES, C2Snapshot, ChronologyError, SourceBindingError, parse_utc


EXTRACTOR_VERSION = "PD.TRANSITIONS.v0.1"


def _axis_token(payload: Mapping[str, Any]) -> str:
    status = str(payload.get("status"))
    value = payload.get("value")
    reason = payload.get("reason_code")
    measurement = payload.get("measurement")
    return "|".join(
        [
            status,
            "NULL" if value is None else str(value),
            "" if reason is None else str(reason),
            "" if measurement is None else str(measurement),
        ]
    )


def _set_token(items: tuple[str, ...]) -> str:
    return ",".join(items)


def _transition(
    *,
    previous: C2Snapshot,
    current: C2Snapshot,
    axis_or_relation: str,
    previous_value: str | None,
    new_value: str | None,
    extractor_version: str,
) -> dict[str, Any]:
    identity = {
        "source_before": previous.source_ref,
        "source_after": current.source_ref,
        "first_valid_at": current.first_valid_time,
        "clock": current.clock,
        "price_side": current.side,
        "scope_id": current.evaluation_scope_id,
        "axis_or_relation": axis_or_relation,
        "previous_value": previous_value,
        "new_value": new_value,
        "extractor_version": extractor_version,
    }
    return {
        "record_type": "TransitionRecord",
        "transition_id": f"PDTR-{canonical_sha256(identity)[:32]}",
        "first_valid_at": current.first_valid_time,
        "clock": current.clock,
        "price_side": current.side,
        "scope_id": current.evaluation_scope_id,
        "axis_or_relation": axis_or_relation,
        "previous_value": previous_value,
        "new_value": new_value,
        "source_before": previous.source_ref,
        "source_after": current.source_ref,
        "extractor_version": extractor_version,
    }


def extract_transitions(
    previous_record: Mapping[str, Any] | C2Snapshot,
    current_record: Mapping[str, Any] | C2Snapshot,
    *,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[dict[str, Any]]:
    """Extract first-valid C2 axis and context transitions.

    The function is stateless and deterministic. It refuses mixed releases, manifests,
    clocks, sides, scopes, parameter packs or selectors and requires strictly increasing
    first-valid chronology.
    """

    previous = previous_record if isinstance(previous_record, C2Snapshot) else C2Snapshot.from_mapping(previous_record)
    current = current_record if isinstance(current_record, C2Snapshot) else C2Snapshot.from_mapping(current_record)
    if previous.binding_key != current.binding_key:
        raise SourceBindingError("C2 transition inputs must share the exact source binding")
    if parse_utc(current.first_valid_time) <= parse_utc(previous.first_valid_time):
        raise ChronologyError("current C2 state must be strictly later than previous state")

    transitions: list[dict[str, Any]] = []
    for axis in AXES:
        before = _axis_token(previous.axes[axis])
        after = _axis_token(current.axes[axis])
        if before != after:
            transitions.append(
                _transition(
                    previous=previous,
                    current=current,
                    axis_or_relation=f"AXIS.{axis}",
                    previous_value=before,
                    new_value=after,
                    extractor_version=extractor_version,
                )
            )

    context_pairs = (
        ("RELATION_SET", previous.relation_set_id, current.relation_set_id),
        ("LEVEL_SET", _set_token(previous.level_ids), _set_token(current.level_ids)),
        ("CONTAINER_SET", _set_token(previous.container_ids), _set_token(current.container_ids)),
        ("PARENT_CONTAINER", previous.parent_container_id, current.parent_container_id),
        ("BOUNDARY_OR_RELATION", previous.boundary_or_relation_id, current.boundary_or_relation_id),
    )
    for name, before, after in context_pairs:
        if before != after:
            transitions.append(
                _transition(
                    previous=previous,
                    current=current,
                    axis_or_relation=name,
                    previous_value=before,
                    new_value=after,
                    extractor_version=extractor_version,
                )
            )

    return sorted(transitions, key=lambda item: (item["axis_or_relation"], item["transition_id"]))
