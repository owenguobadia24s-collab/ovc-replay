from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence

from .canonical import canonical_bytes
from .chronology import parse_utc_z
from .events import ASSERTION_EVENT_TYPES, event_record_hash, validate_event_record
from .ledger import CanonicalEventLedger


SNAPSHOT_SCHEMA = "c2p-object-snapshot/v0.2"
PROJECTION_SCHEMA_VERSION = "v0.2"

LIFECYCLE_STATES = frozenset({"ACTIVE", "DORMANT", "RETIRED", "SUPERSEDED"})
OBSERVABILITY_STATES = frozenset({"OBSERVED", "NOT_OBSERVED", "CENSORED", "SOURCE_UNAVAILABLE"})
EVALUATION_STATES = frozenset({
    "AVAILABLE",
    "ABSENT",
    "MISSING",
    "NOT_EVALUABLE",
    "AMBIGUOUS",
    "CONFLICT",
    "QUARANTINED",
})


class ProjectionError(ValueError):
    pass


class ProjectionIntegrityError(ProjectionError):
    pass


def _hash(payload: Any) -> str:
    return sha256(canonical_bytes(payload)).hexdigest()


def snapshot_identity(
    *,
    projection_schema_version: str,
    object_assertion_id: str,
    event_frontier_hash: str,
    event_frontier_sequence: int,
    snapshot_fields: Mapping[str, Any],
) -> str:
    return _hash({
        "schema": "c2p-object-snapshot-identity/v0.2",
        "projection_schema_version": projection_schema_version,
        "object_assertion_id": object_assertion_id,
        "event_frontier_hash": event_frontier_hash,
        "event_frontier_sequence": event_frontier_sequence,
        "snapshot_fields": deepcopy(dict(snapshot_fields)),
    })


def _validate_axis(value: str, allowed: frozenset[str], field: str) -> str:
    if value not in allowed:
        raise ProjectionError(f"C2P_SNAPSHOT_AXIS_INVALID:{field}:{value}")
    return value


def _later_time(left: str, right: str) -> str:
    return right if parse_utc_z(right) > parse_utc_z(left) else left


def _ordered_stream(events: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    ordered = sorted(
        (deepcopy(dict(event)) for event in events),
        key=lambda event: (event["sequence_no"], event["event_id"]),
    )
    if not ordered:
        raise ProjectionError("C2P_SNAPSHOT_EMPTY_STREAM")
    stream_ids = {event["stream_id"] for event in ordered}
    if len(stream_ids) != 1:
        raise ProjectionError("C2P_SNAPSHOT_MULTI_STREAM")
    for expected, event in enumerate(ordered):
        validate_event_record(event)
        if event["sequence_no"] != expected:
            raise ProjectionError("C2P_SNAPSHOT_SEQUENCE_GAP")
        expected_prior = event_record_hash(ordered[expected - 1]) if expected else None
        if event["prior_event_hash"] != expected_prior:
            raise ProjectionError("C2P_SNAPSHOT_PRIOR_HASH_MISMATCH")
    return ordered


def project_assertion_stream(
    events: Iterable[Mapping[str, Any]],
    *,
    projection_schema_version: str = PROJECTION_SCHEMA_VERSION,
) -> dict[str, Any]:
    if projection_schema_version != PROJECTION_SCHEMA_VERSION:
        raise ProjectionError("C2P_PROJECTION_SCHEMA_NOT_REGISTERED")
    ordered = _ordered_stream(events)
    first = ordered[0]
    if first["event_type"] != "ASSERTION_GENESIS":
        raise ProjectionError("C2P_SNAPSHOT_GENESIS_REQUIRED")
    payload = first["payload"]
    assertion_id = payload.get("object_assertion_id")
    if assertion_id != first["stream_id"]:
        raise ProjectionError("C2P_SNAPSHOT_ASSERTION_STREAM_MISMATCH")

    geometry = deepcopy(dict(payload.get("geometry", {})))
    state_payload = deepcopy(dict(payload.get("state_payload", {})))
    lifecycle = _validate_axis(payload.get("lifecycle_state", "ACTIVE"), LIFECYCLE_STATES, "lifecycle_state")
    observability = _validate_axis(payload.get("observability_state", "OBSERVED"), OBSERVABILITY_STATES, "observability_state")
    evaluation = _validate_axis(payload.get("evaluation_state", "AVAILABLE"), EVALUATION_STATES, "evaluation_state")
    market_effective_start = first["market_effective_start"]
    market_effective_end = first["market_effective_end"]
    first_valid_time = first["first_valid_time"]
    evaluation_cutoff = first["evaluation_cutoff"]

    for event in ordered[1:]:
        event_type = event["event_type"]
        if event_type not in ASSERTION_EVENT_TYPES and event_type not in {
            "SPLIT", "MERGE", "RECURRENCE_LINKED"
        }:
            raise ProjectionError(f"C2P_SNAPSHOT_EVENT_TYPE_INVALID:{event_type}")
        event_payload = event["payload"]
        if event_type == "ASSERTION_GENESIS":
            raise ProjectionError("C2P_SNAPSHOT_DUPLICATE_GENESIS")
        if event_type == "ASSERTION_UPDATED":
            if "lifecycle_state" in event_payload:
                raise ProjectionError("C2P_UPDATE_CANNOT_SET_LIFECYCLE")
            if "geometry" in event_payload:
                geometry = deepcopy(dict(event_payload["geometry"]))
            if "state_payload" in event_payload:
                state_payload = deepcopy(dict(event_payload["state_payload"]))
            if "observability_state" in event_payload:
                observability = _validate_axis(event_payload["observability_state"], OBSERVABILITY_STATES, "observability_state")
            if "evaluation_state" in event_payload:
                evaluation = _validate_axis(event_payload["evaluation_state"], EVALUATION_STATES, "evaluation_state")
            market_effective_start = event["market_effective_start"]
            market_effective_end = event["market_effective_end"]
        elif event_type == "CENSORED_AT_RUN_END":
            if "lifecycle_state" in event_payload:
                raise ProjectionError("C2P_CENSORING_CANNOT_MUTATE_LIFECYCLE")
            observability = "CENSORED"
            if "evaluation_state" in event_payload:
                evaluation = _validate_axis(event_payload["evaluation_state"], EVALUATION_STATES, "evaluation_state")
            # Censoring is an observation boundary, not a structural terminal time.
        elif event_type == "ENTER_DORMANT":
            if lifecycle != "ACTIVE":
                raise ProjectionError("C2P_ENTER_DORMANT_ILLEGAL")
            lifecycle = "DORMANT"
        elif event_type == "REAPPEARED":
            if lifecycle != "DORMANT":
                raise ProjectionError("C2P_REAPPEARANCE_ILLEGAL")
            lifecycle = "ACTIVE"
        elif event_type == "RETIRED":
            if lifecycle not in {"ACTIVE", "DORMANT"}:
                raise ProjectionError("C2P_RETIREMENT_ILLEGAL")
            lifecycle = "RETIRED"
            market_effective_end = event["market_effective_end"]
        elif event_type == "SUPERSEDED":
            if lifecycle not in {"ACTIVE", "DORMANT"}:
                raise ProjectionError("C2P_SUPERSESSION_ILLEGAL")
            lifecycle = "SUPERSEDED"
            market_effective_end = event["market_effective_end"]
        else:
            genealogy = list(state_payload.get("genealogy_event_ids", []))
            genealogy.append(event["event_id"])
            state_payload["genealogy_event_ids"] = sorted(set(genealogy))
        first_valid_time = _later_time(first_valid_time, event["first_valid_time"])
        evaluation_cutoff = _later_time(evaluation_cutoff, event["evaluation_cutoff"])

    frontier = ordered[-1]
    frontier_hash = event_record_hash(frontier)
    snapshot_fields = {
        "geometry": geometry,
        "state_payload": state_payload,
        "lifecycle_state": lifecycle,
        "observability_state": observability,
        "evaluation_state": evaluation,
        "market_effective_start": market_effective_start,
        "market_effective_end": market_effective_end,
        "first_valid_time": first_valid_time,
        "evaluation_cutoff": evaluation_cutoff,
    }
    snapshot_id = snapshot_identity(
        projection_schema_version=projection_schema_version,
        object_assertion_id=assertion_id,
        event_frontier_hash=frontier_hash,
        event_frontier_sequence=frontier["sequence_no"],
        snapshot_fields=snapshot_fields,
    )
    return {
        "schema": SNAPSHOT_SCHEMA,
        "snapshot_id": snapshot_id,
        "projection_schema_version": projection_schema_version,
        "object_assertion_id": assertion_id,
        "event_frontier_hash": frontier_hash,
        "event_frontier_sequence": frontier["sequence_no"],
        **snapshot_fields,
    }


def rebuild_snapshots(ledger: CanonicalEventLedger) -> tuple[Mapping[str, Any], ...]:
    ledger.verify_integrity()
    snapshots: list[Mapping[str, Any]] = []
    for stream_id in ledger.stream_ids():
        events = ledger.stream_events(stream_id)
        if events and events[0]["event_type"] == "ASSERTION_GENESIS":
            snapshots.append(project_assertion_stream(events))
    return tuple(sorted(snapshots, key=lambda item: item["object_assertion_id"]))


def projection_digest(snapshots: Sequence[Mapping[str, Any]]) -> str:
    ordered = sorted((deepcopy(dict(item)) for item in snapshots), key=lambda item: item["snapshot_id"])
    return _hash(ordered)


def verify_snapshot(snapshot: Mapping[str, Any], events: Iterable[Mapping[str, Any]]) -> bool:
    rebuilt = project_assertion_stream(events)
    if canonical_bytes(dict(snapshot)) != canonical_bytes(rebuilt):
        raise ProjectionIntegrityError("C2P_SNAPSHOT_FRONTIER_MISMATCH")
    return True
