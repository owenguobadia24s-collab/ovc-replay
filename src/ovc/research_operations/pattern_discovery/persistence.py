from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ovc.research_operations.canonical import canonical_json_bytes

from .models import DuplicateDerivedRecordError, PatternDiscoveryError


class AppendOnlyJsonlStore:
    """Small append-only store for replaceable derived Pattern Discovery records."""

    def __init__(self, path: str | Path, *, identity_field: str) -> None:
        self.path = Path(path)
        self.identity_field = identity_field

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PatternDiscoveryError(f"invalid JSONL at {self.path}:{line_number}") from exc
            if not isinstance(value, dict):
                raise PatternDiscoveryError(f"JSONL row at {self.path}:{line_number} must be an object")
            records.append(value)
        return records

    def append(self, record: Mapping[str, Any]) -> None:
        identity = record.get(self.identity_field)
        if not isinstance(identity, str) or not identity:
            raise PatternDiscoveryError(f"record requires {self.identity_field}")
        existing = {item.get(self.identity_field) for item in self.read_all()}
        if identity in existing:
            raise DuplicateDerivedRecordError(f"duplicate derived record ID: {identity}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_json_bytes(dict(record), trailing_newline=True)
        with self.path.open("ab") as handle:
            handle.write(payload)

    def append_many(self, records: Iterable[Mapping[str, Any]]) -> None:
        for record in records:
            self.append(record)


class PatternDiscoveryEventLedger:
    def __init__(self, root: str | Path) -> None:
        root_path = Path(root)
        self.transitions = AppendOnlyJsonlStore(root_path / "transition_records.jsonl", identity_field="transition_id")
        self.triggers = AppendOnlyJsonlStore(root_path / "trigger_events.jsonl", identity_field="trigger_event_id")
