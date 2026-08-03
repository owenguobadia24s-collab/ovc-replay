from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


class LedgerError(ValueError):
    """Raised when a portfolio event violates the append-only ledger contract."""


def canonical_event_bytes(event: Mapping[str, Any]) -> bytes:
    """Return path- and runtime-independent canonical JSON bytes."""
    return json.dumps(
        event,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def event_digest(event: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_event_bytes(event)).hexdigest()


def validate_event(event: Mapping[str, Any], allowed_event_types: set[str] | None = None) -> None:
    required = {
        "record_type",
        "schema_version",
        "event_id",
        "programme_id",
        "event_type",
        "observed_at",
        "first_valid_at",
        "actor_class",
        "source_refs",
        "authority_effect",
        "payload",
        "supersedes",
        "rollback",
    }
    missing = sorted(required.difference(event))
    if missing:
        raise LedgerError(f"missing required event fields: {missing}")
    if event["record_type"] != "PROGRAMME_EVENT" or event["schema_version"] != "0.1":
        raise LedgerError("unsupported event record_type or schema_version")
    if not str(event["event_id"]).startswith("PGE."):
        raise LedgerError("event_id must start with PGE.")
    if not event["source_refs"]:
        raise LedgerError("source_refs must not be empty")
    if event["authority_effect"] != "NONE" and not any(
        ref.get("source_type") == "OPERATOR_DECISION" and ref.get("authority_role") == "AUTHORITATIVE"
        for ref in event["source_refs"]
    ):
        raise LedgerError("authority effect requires an authoritative operator decision source")
    if allowed_event_types is not None and event["event_type"] not in allowed_event_types:
        raise LedgerError(f"unregistered event_type: {event['event_type']}")


class AppendOnlyLedger:
    """A compact JSONL ledger that exposes append and read operations only."""

    def __init__(self, path: Path | str, allowed_event_types: Iterable[str] | None = None) -> None:
        self.path = Path(path)
        self.allowed_event_types = set(allowed_event_types) if allowed_event_types is not None else None

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        seen: set[str] = set()
        with self.path.open("r", encoding="utf-8", newline="") as handle:
            for line_number, raw in enumerate(handle, start=1):
                if not raw.endswith("\n"):
                    raise LedgerError(f"line {line_number} is not newline terminated")
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise LedgerError(f"invalid JSON at line {line_number}") from exc
                validate_event(event, self.allowed_event_types)
                event_id = event["event_id"]
                if event_id in seen:
                    raise LedgerError(f"duplicate event_id in ledger: {event_id}")
                seen.add(event_id)
                events.append(event)
        return events

    def append(self, event: Mapping[str, Any]) -> str:
        validate_event(event, self.allowed_event_types)
        existing_ids = {item["event_id"] for item in self.read_all()}
        if event["event_id"] in existing_ids:
            raise LedgerError(f"duplicate event_id: {event['event_id']}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_event_bytes(event) + b"\n"
        with self.path.open("ab") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return event_digest(event)

    def inventory(self) -> dict[str, Any]:
        events = self.read_all()
        ledger_bytes = self.path.read_bytes() if self.path.exists() else b""
        return {
            "event_count": len(events),
            "event_ids": [event["event_id"] for event in events],
            "ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(),
            "event_digests": {event["event_id"]: event_digest(event) for event in events},
        }
