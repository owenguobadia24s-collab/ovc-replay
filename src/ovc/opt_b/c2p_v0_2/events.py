from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re
import unicodedata
from typing import Any, Iterable, Mapping

from .canonical import canonical_bytes
from .chronology import ChronologyError, validate_causal_times


HASH_VERSION = "sha256-canonical-json-v1"
EVENT_SCHEMA = "c2p-event/v0.2"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

TRACKLET_EVENT_TYPES = frozenset({
    "TRACKLET_OPENED",
    "TRACKLET_UPDATED",
    "TRACKLET_AMBIGUOUS",
    "TRACKLET_EXPIRED",
    "TRACKLET_PROMOTED",
})
ASSERTION_EVENT_TYPES = frozenset({
    "ASSERTION_GENESIS",
    "ASSERTION_UPDATED",
    "ENTER_DORMANT",
    "REAPPEARED",
    "RETIRED",
    "SUPERSEDED",
    "CENSORED_AT_RUN_END",
})
GENEALOGY_EVENT_TYPES = frozenset({
    "SPLIT",
    "MERGE",
    "RECURRENCE_LINKED",
})
OPERATIONS_EVENT_TYPES = frozenset({
    "CHECKPOINT_SEALED",
    "REPLAY_RECONCILED",
    "QUARANTINED_INTEGRITY_FAILURE",
})
SUPPORTED_EVENT_TYPES = (
    TRACKLET_EVENT_TYPES
    | ASSERTION_EVENT_TYPES
    | GENEALOGY_EVENT_TYPES
    | OPERATIONS_EVENT_TYPES
)
EVENT_FIELDS = frozenset({
    "schema",
    "event_id",
    "hash_version",
    "stream_id",
    "sequence_no",
    "event_type",
    "object_pack_id",
    "market_effective_start",
    "market_effective_end",
    "first_valid_time",
    "evaluation_cutoff",
    "decision_id",
    "parent_event_ids",
    "source_hashes",
    "payload",
    "prior_event_hash",
})


class EventBuildError(ValueError):
    pass


def _hash(payload: Any) -> str:
    return sha256(canonical_bytes(payload)).hexdigest()


def _require_hash(value: str | None, field: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise EventBuildError(f"C2P_EVENT_INVALID_HASH:{field}")


def _validate_nfc_tree(value: Any, path: str = "payload") -> None:
    if isinstance(value, str):
        if not unicodedata.is_normalized("NFC", value):
            raise EventBuildError(f"C2P_EVENT_TEXT_NOT_NFC:{path}")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise EventBuildError(f"C2P_EVENT_NON_STRING_KEY:{path}")
            if not unicodedata.is_normalized("NFC", key):
                raise EventBuildError(f"C2P_EVENT_TEXT_NOT_NFC:{path}.{key}")
            _validate_nfc_tree(child, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_nfc_tree(child, f"{path}[{index}]")


def _sorted_unique_hashes(values: Iterable[str], field: str) -> list[str]:
    materialized = list(values)
    for value in materialized:
        _require_hash(value, field)
    if len(materialized) != len(set(materialized)):
        raise EventBuildError(f"C2P_EVENT_DUPLICATE_HASH:{field}")
    return sorted(materialized)


def _generic_event_identity_payload(event_without_id: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "c2p-event-identity/v0.2",
        "event": deepcopy(dict(event_without_id)),
    }


def _genesis_event_reference_payload(event_without_id: Mapping[str, Any]) -> dict[str, Any]:
    payload = event_without_id.get("payload")
    if not isinstance(payload, Mapping):
        raise EventBuildError("C2P_ASSERTION_GENESIS_PAYLOAD_REQUIRED")
    object_assertion_id = payload.get("object_assertion_id")
    _require_hash(object_assertion_id, "payload.object_assertion_id")
    if event_without_id.get("stream_id") != object_assertion_id:
        raise EventBuildError("C2P_ASSERTION_GENESIS_STREAM_MISMATCH")
    decision_id = event_without_id.get("decision_id")
    _require_hash(decision_id, "decision_id")
    return {
        "schema": "c2p-assertion-genesis-event-reference/v0.2",
        "object_assertion_id": object_assertion_id,
        "object_pack_id": event_without_id["object_pack_id"],
        "genesis_match_decision_id": decision_id,
        "first_valid_identity_time": event_without_id["first_valid_time"],
    }


def logical_event_id(event_without_id: Mapping[str, Any]) -> str:
    if event_without_id.get("event_type") == "ASSERTION_GENESIS":
        return _hash(_genesis_event_reference_payload(event_without_id))
    return _hash(_generic_event_identity_payload(event_without_id))


def validate_event_record(event: Mapping[str, Any]) -> None:
    if set(event) != EVENT_FIELDS:
        missing = sorted(EVENT_FIELDS - set(event))
        extra = sorted(set(event) - EVENT_FIELDS)
        reason = missing[0] if missing else extra[0]
        raise EventBuildError(f"C2P_EVENT_FIELD_SURFACE:{reason}")
    if event.get("schema") != EVENT_SCHEMA:
        raise EventBuildError("C2P_EVENT_SCHEMA_MISMATCH")
    if event.get("hash_version") != HASH_VERSION:
        raise EventBuildError("C2P_EVENT_HASH_VERSION_MISMATCH")
    if not isinstance(event.get("stream_id"), str) or not event["stream_id"]:
        raise EventBuildError("C2P_EVENT_STREAM_REQUIRED")
    if event.get("event_type") not in SUPPORTED_EVENT_TYPES:
        raise EventBuildError("C2P_EVENT_TYPE_UNREGISTERED")
    if not isinstance(event.get("object_pack_id"), str) or not event["object_pack_id"]:
        raise EventBuildError("C2P_EVENT_OBJECT_PACK_REQUIRED")
    sequence_no = event.get("sequence_no")
    if isinstance(sequence_no, bool) or not isinstance(sequence_no, int) or sequence_no < 0:
        raise EventBuildError("C2P_EVENT_SEQUENCE_INVALID")
    prior = event.get("prior_event_hash")
    if sequence_no == 0 and prior is not None:
        raise EventBuildError("C2P_EVENT_GENESIS_PRIOR_FORBIDDEN")
    if sequence_no > 0:
        _require_hash(prior, "prior_event_hash")
    decision_id = event.get("decision_id")
    _require_hash(decision_id, "decision_id", nullable=True)
    if not isinstance(event.get("parent_event_ids"), list):
        raise EventBuildError("C2P_EVENT_PARENT_LIST_REQUIRED")
    if not isinstance(event.get("source_hashes"), list):
        raise EventBuildError("C2P_EVENT_SOURCE_HASH_LIST_REQUIRED")
    normalized_parents = _sorted_unique_hashes(event["parent_event_ids"], "parent_event_ids")
    normalized_sources = _sorted_unique_hashes(event["source_hashes"], "source_hashes")
    if event["parent_event_ids"] != normalized_parents:
        raise EventBuildError("C2P_EVENT_PARENT_ORDER_NONCANONICAL")
    if event["source_hashes"] != normalized_sources:
        raise EventBuildError("C2P_EVENT_SOURCE_ORDER_NONCANONICAL")
    if not isinstance(event.get("payload"), Mapping):
        raise EventBuildError("C2P_EVENT_PAYLOAD_OBJECT_REQUIRED")
    _validate_nfc_tree(event)
    try:
        validate_causal_times(
            market_effective_start=event["market_effective_start"],
            market_effective_end=event["market_effective_end"],
            first_valid_time=event["first_valid_time"],
            evaluation_cutoff=event["evaluation_cutoff"],
        )
    except (ChronologyError, KeyError) as exc:
        raise EventBuildError(f"C2P_EVENT_CHRONOLOGY:{exc}") from exc
    event_without_id = {key: deepcopy(value) for key, value in event.items() if key != "event_id"}
    expected_id = logical_event_id(event_without_id)
    if event.get("event_id") != expected_id:
        raise EventBuildError("C2P_EVENT_ID_MISMATCH")
    if event["event_type"] == "ASSERTION_GENESIS":
        if sequence_no != 0 or prior is not None:
            raise EventBuildError("C2P_ASSERTION_GENESIS_POSITION_INVALID")
        payload = event["payload"]
        if payload.get("lifecycle_state") != "ACTIVE":
            raise EventBuildError("C2P_ASSERTION_GENESIS_NOT_ACTIVE")
    if event["event_type"] == "CENSORED_AT_RUN_END" and "lifecycle_state" in event["payload"]:
        raise EventBuildError("C2P_CENSORING_CANNOT_MUTATE_LIFECYCLE")
    if event["event_type"] in ASSERTION_EVENT_TYPES and event["event_type"] != "ASSERTION_GENESIS":
        terminal = event["payload"].get("match_decision_terminal")
        if terminal in {"AMBIGUOUS", "NOT_EVALUABLE", "CONFLICT"}:
            raise EventBuildError(f"C2P_UNRESOLVED_DECISION_CANNOT_MUTATE:{terminal}")


def build_event(
    *,
    stream_id: str,
    sequence_no: int,
    event_type: str,
    object_pack: Mapping[str, Any],
    market_effective_start: str,
    market_effective_end: str | None,
    first_valid_time: str,
    evaluation_cutoff: str,
    decision_id: str | None,
    parent_event_ids: Iterable[str] = (),
    source_hashes: Iterable[str] = (),
    payload: Mapping[str, Any],
    prior_event_hash: str | None,
    expected_event_id: str | None = None,
) -> dict[str, Any]:
    if (
        object_pack.get("status") != "SYNTHETIC_ONLY_NONEMPIRICAL"
        or object_pack.get("activation_eligible") is not False
        or object_pack.get("real_source_forbidden") is not True
    ):
        raise EventBuildError("C2P_WP4_SYNTHETIC_PACK_REQUIRED")
    event_without_id = {
        "schema": EVENT_SCHEMA,
        "hash_version": HASH_VERSION,
        "stream_id": str(stream_id),
        "sequence_no": sequence_no,
        "event_type": event_type,
        "object_pack_id": object_pack.get("object_pack_id"),
        "market_effective_start": market_effective_start,
        "market_effective_end": market_effective_end,
        "first_valid_time": first_valid_time,
        "evaluation_cutoff": evaluation_cutoff,
        "decision_id": decision_id,
        "parent_event_ids": _sorted_unique_hashes(parent_event_ids, "parent_event_ids"),
        "source_hashes": _sorted_unique_hashes(source_hashes, "source_hashes"),
        "payload": deepcopy(dict(payload)),
        "prior_event_hash": prior_event_hash,
    }
    event_id = logical_event_id(event_without_id)
    if expected_event_id is not None and expected_event_id != event_id:
        raise EventBuildError("C2P_EXPECTED_EVENT_ID_MISMATCH")
    event = {"event_id": event_id, **event_without_id}
    validate_event_record(event)
    return event


def build_assertion_genesis_event(
    assertion: Mapping[str, Any],
    object_pack: Mapping[str, Any],
    *,
    market_effective_start: str,
    market_effective_end: str | None,
    evaluation_cutoff: str,
    geometry: Mapping[str, Any],
    state_payload: Mapping[str, Any],
    source_hashes: Iterable[str],
    parent_event_ids: Iterable[str] = (),
) -> dict[str, Any]:
    if assertion.get("object_pack_id") != object_pack.get("object_pack_id"):
        raise EventBuildError("C2P_ASSERTION_EVENT_OBJECT_PACK_MISMATCH")
    event = build_event(
        stream_id=assertion["object_assertion_id"],
        sequence_no=0,
        event_type="ASSERTION_GENESIS",
        object_pack=object_pack,
        market_effective_start=market_effective_start,
        market_effective_end=market_effective_end,
        first_valid_time=assertion["first_valid_identity_time"],
        evaluation_cutoff=evaluation_cutoff,
        decision_id=assertion["genesis_match_decision_id"],
        parent_event_ids=parent_event_ids,
        source_hashes=source_hashes,
        payload={
            "object_assertion_id": assertion["object_assertion_id"],
            "structural_role_id": assertion["structural_role_id"],
            "geometry_kind_id": assertion["geometry_kind_id"],
            "hard_scope": deepcopy(dict(assertion["hard_scope"])),
            "immutable_genesis_evidence_ids": list(assertion["immutable_genesis_evidence_ids"]),
            "geometry": deepcopy(dict(geometry)),
            "state_payload": deepcopy(dict(state_payload)),
            "lifecycle_state": "ACTIVE",
            "observability_state": "OBSERVED",
            "evaluation_state": "AVAILABLE",
        },
        prior_event_hash=None,
        expected_event_id=assertion["genesis_event_id"],
    )
    return event


def event_record_hash(event: Mapping[str, Any]) -> str:
    validate_event_record(event)
    return _hash(dict(event))


def canonical_event_bytes(event: Mapping[str, Any]) -> bytes:
    validate_event_record(event)
    return canonical_bytes(dict(event))
