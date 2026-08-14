from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .canonical import CanonicalizationError, canonical_bytes
from .events import EventBuildError, canonical_event_bytes
from .ledger import (
    AppendResult,
    CanonicalEventLedger,
    LedgerIntegrityError,
    LedgerQuarantinedError,
)
from .projection import (
    ProjectionIntegrityError,
    projection_digest,
    rebuild_snapshots,
)


class PersistenceIntegrityError(ValueError):
    pass


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class EventJournal:
    """Append-only canonical JSONL event journal with a rebuildable frontier seal."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.seal_path = self.path.with_name(f"{self.path.name}.frontier.json")

    def raw_bytes(self) -> bytes:
        return self.path.read_bytes() if self.path.exists() else b""

    def _read_events(self) -> list[Mapping[str, Any]]:
        if not self.path.exists():
            return []
        raw = self.path.read_bytes()
        if not raw:
            return []
        lines = raw.splitlines(keepends=True)
        events: list[Mapping[str, Any]] = []
        for index, line in enumerate(lines):
            if not line.endswith(b"\n"):
                raise PersistenceIntegrityError(f"C2P_JOURNAL_TRUNCATED_LINE:{index}")
            payload = line[:-1]
            try:
                record = json.loads(payload.decode("utf-8"))
                expected = canonical_bytes(record)
            except (UnicodeDecodeError, json.JSONDecodeError, CanonicalizationError) as exc:
                raise PersistenceIntegrityError(f"C2P_JOURNAL_DECODE_OR_CANONICAL:{index}") from exc
            if payload != expected:
                raise PersistenceIntegrityError(f"C2P_JOURNAL_NONCANONICAL:{index}")
            events.append(record)
        return events

    def _read_seal(self) -> Mapping[str, Any] | None:
        if not self.seal_path.exists():
            return None
        raw = self.seal_path.read_bytes()
        try:
            record = json.loads(raw.decode("utf-8"))
            if raw != canonical_bytes(record):
                raise PersistenceIntegrityError("C2P_JOURNAL_SEAL_NONCANONICAL")
        except (UnicodeDecodeError, json.JSONDecodeError, CanonicalizationError) as exc:
            raise PersistenceIntegrityError("C2P_JOURNAL_SEAL_INVALID") from exc
        return record

    def load_ledger(self) -> CanonicalEventLedger:
        events = self._read_events()
        try:
            ledger = CanonicalEventLedger.from_events(events)
        except (EventBuildError, LedgerIntegrityError, LedgerQuarantinedError) as exc:
            raise PersistenceIntegrityError(f"C2P_JOURNAL_LEDGER_INTEGRITY:{exc}") from exc
        seal = self._read_seal()
        if events and seal is None:
            raise PersistenceIntegrityError("C2P_JOURNAL_SEAL_MISSING")
        if seal is not None and canonical_bytes(dict(seal)) != canonical_bytes(dict(ledger.seal())):
            raise PersistenceIntegrityError("C2P_JOURNAL_SEAL_MISMATCH")
        return ledger

    def append_event(self, event: Mapping[str, Any]) -> AppendResult:
        ledger = self.load_ledger()
        result = ledger.append(event)
        if result.disposition == "APPENDED":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("ab") as handle:
                handle.write(canonical_event_bytes(event) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        _atomic_write(self.seal_path, canonical_bytes(dict(ledger.seal())))
        return result


class SnapshotProjectionStore:
    """Replaceable projection store.

    It exposes no arbitrary snapshot upsert. Every persisted byte is rebuilt
    from a verified canonical event ledger.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _payload_for_ledger(self, ledger: CanonicalEventLedger) -> dict[str, Any]:
        snapshots = list(rebuild_snapshots(ledger))
        return {
            "schema": "c2p-snapshot-projection-set/v0.2",
            "ledger_digest": ledger.global_digest(),
            "projection_digest": projection_digest(snapshots),
            "snapshots": snapshots,
        }

    def rebuild_from_ledger(self, ledger: CanonicalEventLedger) -> Mapping[str, Any]:
        payload = self._payload_for_ledger(ledger)
        _atomic_write(self.path, canonical_bytes(payload))
        return deepcopy(payload)

    def read_verified(self, ledger: CanonicalEventLedger) -> Mapping[str, Any]:
        if not self.path.exists():
            raise ProjectionIntegrityError("C2P_SNAPSHOT_STORE_MISSING")
        raw = self.path.read_bytes()
        try:
            stored = json.loads(raw.decode("utf-8"))
            if raw != canonical_bytes(stored):
                raise ProjectionIntegrityError("C2P_SNAPSHOT_STORE_NONCANONICAL")
        except (UnicodeDecodeError, json.JSONDecodeError, CanonicalizationError) as exc:
            raise ProjectionIntegrityError("C2P_SNAPSHOT_STORE_INVALID") from exc
        expected = self._payload_for_ledger(ledger)
        if canonical_bytes(stored) != canonical_bytes(expected):
            raise ProjectionIntegrityError("C2P_SNAPSHOT_STORE_LEDGER_MISMATCH")
        return deepcopy(stored)
