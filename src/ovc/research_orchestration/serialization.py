from __future__ import annotations

import dataclasses
import hashlib
import json
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping


class CanonicalizationError(ValueError):
    pass


def canonical_value(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        if hasattr(value, "to_dict"):
            return canonical_value(value.to_dict())
        return canonical_value(dataclasses.asdict(value))
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Mapping):
        return {str(key): canonical_value(value[key]) for key in sorted(value, key=lambda item: str(item))}
    if isinstance(value, (tuple, list)):
        return [canonical_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((canonical_value(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise CanonicalizationError("non-finite floats are forbidden")
        return value
    raise CanonicalizationError(f"unsupported canonical type: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(canonical_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def canonical_json(value: Any) -> str:
    """Return the canonical UTF-8 JSON payload as text.

    This is the text-form companion to ``canonical_json_bytes`` retained for
    existing orchestration adapters that compare canonical payloads directly.
    """
    return canonical_json_bytes(value).decode("utf-8")


def logical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}{logical_sha256(value)}"
