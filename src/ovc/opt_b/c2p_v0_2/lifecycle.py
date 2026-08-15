from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence

from .events import build_event, event_record_hash
from .projection import project_assertion_stream


class LifecycleError(ValueError):
    pass


def _ordered(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    materialized = [deepcopy(dict(event)) for event in events]
    if not materialized:
        raise LifecycleError("C2P_LIFECYCLE_STREAM_REQUIRED")
    return sorted(materialized, key=lambda event: (event["sequence_no"], event["event_id"]))


def _frontier(events: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return events[-1]


def _same_pack(snapshot: Mapping[str, Any], frontier: Mapping[str, Any], object_pack: Mapping[str, Any]) -> None:
    if frontier.get("object_pack_id") != object_pack.get("object_pack_id"):
        raise LifecycleError("C2P_LIFECYCLE_OBJECT_PACK_MISMATCH")
    if snapshot.get("object_assertion_id") != frontier.get("stream_id"):
        raise LifecycleError("C2P_LIFECYCLE_ASSERTION_STREAM_MISMATCH")


def _append_lifecycle_event(
    events: Iterable[Mapping[str, Any]],
    object_pack: Mapping[str, Any],
    *,
    event_type: str,
    market_effective_start: str,
    market_effective_end: str | None,
    first_valid_time: str,
    evaluation_cutoff: str,
    decision_id: str,
    source_hashes: Iterable[str],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    ordered = _ordered(events)
    snapshot = project_assertion_stream(ordered)
    frontier = _frontier(ordered)
    _same_pack(snapshot, frontier, object_pack)
    return build_event(
        stream_id=snapshot["object_assertion_id"],
        sequence_no=frontier["sequence_no"] + 1,
        event_type=event_type,
        object_pack=object_pack,
        market_effective_start=market_effective_start,
        market_effective_end=market_effective_end,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        decision_id=decision_id,
        parent_event_ids=[frontier["event_id"]],
        source_hashes=source_hashes,
        payload=payload,
        prior_event_hash=event_record_hash(frontier),
    )


def enter_dormant(
    events: Iterable[Mapping[str, Any]],
    object_pack: Mapping[str, Any],
    *,
    market_effective_start: str,
    first_valid_time: str,
    evaluation_cutoff: str,
    decision_id: str,
    source_hashes: Iterable[str],
    reason: str,
) -> dict[str, Any]:
    ordered = _ordered(events)
    snapshot = project_assertion_stream(ordered)
    if snapshot["lifecycle_state"] != "ACTIVE":
        raise LifecycleError("C2P_DORMANCY_REQUIRES_ACTIVE")
    return _append_lifecycle_event(
        ordered,
        object_pack,
        event_type="ENTER_DORMANT",
        market_effective_start=market_effective_start,
        market_effective_end=None,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        decision_id=decision_id,
        source_hashes=source_hashes,
        payload={"reason": reason},
    )


def reappear(
    events: Iterable[Mapping[str, Any]],
    object_pack: Mapping[str, Any],
    *,
    fixture_structure_key: str,
    market_effective_start: str,
    first_valid_time: str,
    evaluation_cutoff: str,
    decision_id: str,
    source_hashes: Iterable[str],
) -> dict[str, Any]:
    ordered = _ordered(events)
    snapshot = project_assertion_stream(ordered)
    if snapshot["lifecycle_state"] != "DORMANT":
        raise LifecycleError("C2P_REAPPEARANCE_REQUIRES_DORMANT")
    expected_key = snapshot.get("state_payload", {}).get("fixture_structure_key")
    if expected_key is None or fixture_structure_key != expected_key:
        raise LifecycleError("C2P_REAPPEARANCE_CONTINUITY_KEY_MISMATCH")
    return _append_lifecycle_event(
        ordered,
        object_pack,
        event_type="REAPPEARED",
        market_effective_start=market_effective_start,
        market_effective_end=None,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        decision_id=decision_id,
        source_hashes=source_hashes,
        payload={"fixture_structure_key": fixture_structure_key},
    )


def retire(
    events: Iterable[Mapping[str, Any]],
    object_pack: Mapping[str, Any],
    *,
    market_effective_start: str,
    market_effective_end: str,
    first_valid_time: str,
    evaluation_cutoff: str,
    decision_id: str,
    source_hashes: Iterable[str],
    reason: str,
) -> dict[str, Any]:
    ordered = _ordered(events)
    snapshot = project_assertion_stream(ordered)
    if snapshot["lifecycle_state"] not in {"ACTIVE", "DORMANT"}:
        raise LifecycleError("C2P_RETIREMENT_FROM_TERMINAL_STATE")
    return _append_lifecycle_event(
        ordered,
        object_pack,
        event_type="RETIRED",
        market_effective_start=market_effective_start,
        market_effective_end=market_effective_end,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        decision_id=decision_id,
        source_hashes=source_hashes,
        payload={"reason": reason},
    )


def supersede(
    events: Iterable[Mapping[str, Any]],
    object_pack: Mapping[str, Any],
    *,
    market_effective_start: str,
    market_effective_end: str,
    first_valid_time: str,
    evaluation_cutoff: str,
    decision_id: str,
    source_hashes: Iterable[str],
    successor_assertion_id: str,
) -> dict[str, Any]:
    ordered = _ordered(events)
    snapshot = project_assertion_stream(ordered)
    if snapshot["lifecycle_state"] not in {"ACTIVE", "DORMANT"}:
        raise LifecycleError("C2P_SUPERSESSION_FROM_TERMINAL_STATE")
    if successor_assertion_id == snapshot["object_assertion_id"]:
        raise LifecycleError("C2P_SUPERSESSION_SELF_REFERENCE")
    return _append_lifecycle_event(
        ordered,
        object_pack,
        event_type="SUPERSEDED",
        market_effective_start=market_effective_start,
        market_effective_end=market_effective_end,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        decision_id=decision_id,
        source_hashes=source_hashes,
        payload={"successor_assertion_id": successor_assertion_id},
    )
