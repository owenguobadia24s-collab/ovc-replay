from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from typing import Iterable


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    return sha256(payload).hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class SourceBar:
    object_id: str
    timestamp_utc: str
    side: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def logical_dict(self) -> dict[str, object]:
        value = asdict(self)
        return {key: str(item) if isinstance(item, Decimal) else item for key, item in value.items()}


@dataclass(frozen=True)
class ProspectiveBar:
    bar_id: str
    clock: str
    side: str
    start_utc: str
    end_utc: str
    open: str | None
    high: str | None
    low: str | None
    close: str | None
    volume: str | None
    parent_source_object_ids: tuple[str, ...]
    quality_state: str

    def logical_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["parent_source_object_ids"] = list(self.parent_source_object_ids)
        return value


@dataclass(frozen=True)
class ProspectiveCursor:
    cursor_id: str
    source_slice_id: str
    last_source_interval_end_utc: str
    last_transition_id: str | None
    sequence: int
    state_hash: str


def manifest_hash(items: Iterable[object]) -> str:
    normalized = [item.logical_dict() if hasattr(item, "logical_dict") else item for item in items]
    return canonical_hash(normalized)
