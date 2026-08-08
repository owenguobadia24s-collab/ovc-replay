from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal
from typing import Any, Iterable, Mapping


class SFCSerializationError(ValueError):
    pass


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise SFCSerializationError("SFC_NONFINITE_NUMBER")
        if value == 0:
            return "0"
        return format(value.normalize(), "f")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SFCSerializationError("SFC_NONFINITE_NUMBER")
        if value == 0.0:
            value = 0.0
        return json.loads(json.dumps(value, allow_nan=False))
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, set):
        return sorted((_canonical(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True, separators=(",", ":")))
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise SFCSerializationError(f"SFC_UNSUPPORTED_CANONICAL_TYPE:{type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Return path/worker/runtime independent UTF-8 canonical JSON bytes."""
    normalized = _canonical(value)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def logical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def assert_allowed_keys(record: Mapping[str, Any], *, allowed: Iterable[str], forbidden: Iterable[str] = ()) -> None:
    allowed_set = set(allowed)
    forbidden_set = set(forbidden)
    explicit = sorted(k for k in record if k in forbidden_set)
    if explicit:
        raise SFCSerializationError("SFC_FORBIDDEN_FIELD:" + ",".join(explicit))
    extras = sorted(set(record) - allowed_set)
    if extras:
        raise SFCSerializationError("SFC_UNDECLARED_FIELD:" + ",".join(extras))


def with_logical_hash(record: Mapping[str, Any], hash_field: str = "logical_hash") -> dict[str, Any]:
    payload = dict(record)
    payload.pop(hash_field, None)
    payload[hash_field] = logical_hash(payload)
    return payload
