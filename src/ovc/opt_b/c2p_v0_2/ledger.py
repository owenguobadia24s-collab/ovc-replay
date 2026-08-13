from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping

from .canonical import canonical_bytes
from .events import (
    EventBuildError,
    canonical_event_bytes,
    event_record_hash,
    validate_event_record,
)


class LedgerIntegrityError(ValueError):
    pass


class LedgerQuarantinedError(LedgerIntegrityError):
    pass


@dataclass(frozen=True)
class AppendResult:
    disposition: str
    event_id: str
    event_hash: str
    stream_id: str
    sequence_no: int


class CanonicalEventLedger:
    """Append-only C2P event authority.

    Stored events are deep-copied. Callers receive copies, and no mutation or
    replacement API exists. Quarantine is terminal for the ledger instance.
    """

    def __init__(self) -> None:
        self._streams: dict[str, list[dict[str, Any]]] = {}
        self._event_bytes_by_id: dict[str, bytes] = {}
        self._event_hash_by_id: dict[str, str] = {}
        self._quarantine: dict[str, Any] | None = None

    @property
    def is_quarantined(self) -> bool:
        return self._quarantine is not None

    @property
    def event_count(self) -> int:
        return sum(len(events) for events in self._streams.values())

    @property
    def quarantine_record(self) -> Mapping[str, Any] | None:
        return deepcopy(self._quarantine)

    def _fail_closed(self, reason: str, event: Mapping[str, Any] | None = None) -> None:
        if self._quarantine is None:
            self._quarantine = {
                "schema": "c2p-ledger-quarantine/v0.2",
                "reason": reason,
                "event_id": event.get("event_id") if event else None,
                "stream_id": event.get("stream_id") if event else None,
                "sequence_no": event.get("sequence_no") if event else None,
                "event_count_at_quarantine": self.event_count,
            }
        raise LedgerQuarantinedError(reason)

    def append(self, event: Mapping[str, Any]) -> AppendResult:
        if self.is_quarantined:
            raise LedgerQuarantinedError("C2P_LEDGER_ALREADY_QUARANTINED")
        try:
            validate_event_record(event)
            encoded = canonical_event_bytes(event)
            event_hash = event_record_hash(event)
        except EventBuildError as exc:
            self._fail_closed(f"C2P_EVENT_INVALID:{exc}", event)
        event_id = str(event["event_id"])
        stream_id = str(event["stream_id"])
        sequence_no = int(event["sequence_no"])

        existing_bytes = self._event_bytes_by_id.get(event_id)
        if existing_bytes is not None:
            if existing_bytes == encoded:
                return AppendResult(
                    disposition="IDEMPOTENT",
                    event_id=event_id,
                    event_hash=self._event_hash_by_id[event_id],
                    stream_id=stream_id,
                    sequence_no=sequence_no,
                )
            self._fail_closed("C2P_EVENT_ID_CONFLICT", event)

        stream = self._streams.setdefault(stream_id, [])
        expected_sequence = len(stream)
        if sequence_no != expected_sequence:
            self._fail_closed("C2P_STREAM_SEQUENCE_VIOLATION", event)
        expected_prior = event_record_hash(stream[-1]) if stream else None
        if event["prior_event_hash"] != expected_prior:
            self._fail_closed("C2P_STREAM_PRIOR_HASH_MISMATCH", event)
        if any(item["sequence_no"] == sequence_no for item in stream):
            self._fail_closed("C2P_STREAM_POSITION_CONFLICT", event)

        stored = deepcopy(dict(event))
        stream.append(stored)
        self._event_bytes_by_id[event_id] = encoded
        self._event_hash_by_id[event_id] = event_hash
        return AppendResult(
            disposition="APPENDED",
            event_id=event_id,
            event_hash=event_hash,
            stream_id=stream_id,
            sequence_no=sequence_no,
        )

    def stream_events(self, stream_id: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(deepcopy(self._streams.get(stream_id, [])))

    def stream_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._streams))

    def all_events(self) -> tuple[Mapping[str, Any], ...]:
        ordered: list[Mapping[str, Any]] = []
        for stream_id in sorted(self._streams):
            ordered.extend(
                deepcopy(
                    sorted(
                        self._streams[stream_id],
                        key=lambda item: (item["sequence_no"], item["event_id"]),
                    )
                )
            )
        return tuple(ordered)

    def event_by_id(self, event_id: str) -> Mapping[str, Any] | None:
        for event in self.all_events():
            if event["event_id"] == event_id:
                return event
        return None

    def canonical_export_bytes(self) -> bytes:
        events = self.all_events()
        if not events:
            return b""
        return b"".join(canonical_event_bytes(event) + b"\n" for event in events)

    def global_digest(self) -> str:
        return sha256(self.canonical_export_bytes()).hexdigest()

    def stream_frontier(self, stream_id: str) -> Mapping[str, Any] | None:
        stream = self._streams.get(stream_id)
        if not stream:
            return None
        event = stream[-1]
        return {
            "stream_id": stream_id,
            "sequence_no": event["sequence_no"],
            "event_id": event["event_id"],
            "event_hash": event_record_hash(event),
        }

    def seal(self) -> Mapping[str, Any]:
        return {
            "schema": "c2p-event-journal-frontier/v0.2",
            "event_count": self.event_count,
            "ledger_digest": self.global_digest(),
            "streams": [
                dict(self.stream_frontier(stream_id))
                for stream_id in self.stream_ids()
            ],
        }

    def verify_integrity(self) -> bool:
        if self.is_quarantined:
            raise LedgerQuarantinedError("C2P_LEDGER_ALREADY_QUARANTINED")
        seen_event_ids: set[str] = set()
        all_event_ids = {event["event_id"] for event in self.all_events()}
        for stream_id in self.stream_ids():
            expected_prior: str | None = None
            for expected_sequence, event in enumerate(self._streams[stream_id]):
                try:
                    validate_event_record(event)
                except EventBuildError as exc:
                    self._fail_closed(f"C2P_EVENT_INVALID:{exc}", event)
                if event["event_id"] in seen_event_ids:
                    self._fail_closed("C2P_EVENT_ID_DUPLICATE", event)
                seen_event_ids.add(event["event_id"])
                if event["sequence_no"] != expected_sequence:
                    self._fail_closed("C2P_STREAM_SEQUENCE_VIOLATION", event)
                if event["prior_event_hash"] != expected_prior:
                    self._fail_closed("C2P_STREAM_PRIOR_HASH_MISMATCH", event)
                if event["event_id"] in event["parent_event_ids"]:
                    self._fail_closed("C2P_EVENT_SELF_PARENT", event)
                missing_parent = next(
                    (parent for parent in event["parent_event_ids"] if parent not in all_event_ids),
                    None,
                )
                if missing_parent is not None:
                    self._fail_closed(f"C2P_EVENT_PARENT_MISSING:{missing_parent}", event)
                expected_prior = event_record_hash(event)
        return True

    @classmethod
    def from_events(cls, events: Iterable[Mapping[str, Any]]) -> "CanonicalEventLedger":
        materialized = [deepcopy(dict(event)) for event in events]
        ordered = sorted(
            materialized,
            key=lambda event: (
                str(event.get("stream_id")),
                int(event.get("sequence_no", -1)),
                str(event.get("event_id")),
            ),
        )
        ledger = cls()
        for event in ordered:
            ledger.append(event)
        ledger.verify_integrity()
        return ledger
