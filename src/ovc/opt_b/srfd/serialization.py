from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
import math
from typing import Any, Mapping

NON_IDENTITY_DIAGNOSTIC_KEYS = frozenset({
    "created_at",
    "executed_at",
    "start_time",
    "end_time",
    "runtime_seconds",
    "hostname",
    "host",
    "worker_id",
    "worker_name",
    "local_path",
    "external_artifact_root",
})


def _canonical(value: Any) -> Any:
    if is_dataclass(value):
        return _canonical(asdict(value))
    if isinstance(value, Enum):
        return _canonical(value.value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal is not canonical")
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("naive datetime is not canonical")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float is not canonical")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical mappings require string keys")
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported canonical type: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def logical_sha256(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def identity_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    """Drop runtime/machine diagnostics recursively before identity hashing."""
    def strip(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {
                key: strip(val)
                for key, val in item.items()
                if key not in NON_IDENTITY_DIAGNOSTIC_KEYS
            }
        if isinstance(item, (list, tuple)):
            return [strip(val) for val in item]
        return item
    return strip(value)


def stable_id(prefix: str, value: Mapping[str, Any]) -> str:
    if not prefix or not prefix.endswith("."):
        raise ValueError("prefix must be non-empty and end with '.'")
    return prefix + logical_sha256(identity_payload(value))
