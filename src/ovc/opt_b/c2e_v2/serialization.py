"""Canonical logical serialization for C2E v0.2.

Identity-bearing decimals never use runtime ``repr(float)``.  Field/parameter
contracts declare decimal precision and callers must provide exact finite values
that already fit that precision.  This packet intentionally fails closed instead
of rounding identity semantics.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Mapping

_EXPONENT_RE = re.compile(r"[eE]")


class C2ESerializationError(ValueError):
    pass


def canonical_decimal(value: Any, precision: int, *, allow_exponent: bool = False) -> str:
    if isinstance(value, bool) or isinstance(value, float):
        raise C2ESerializationError("RUNTIME_FLOAT_IDENTITY_DENIED")
    if not isinstance(precision, int) or precision < 0:
        raise C2ESerializationError("DECIMAL_PRECISION_INVALID")
    text = str(value)
    if not allow_exponent and _EXPONENT_RE.search(text):
        raise C2ESerializationError("DECIMAL_EXPONENT_FORM_DENIED")
    try:
        dec = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise C2ESerializationError("DECIMAL_INVALID") from exc
    if not dec.is_finite():
        raise C2ESerializationError("DECIMAL_NONFINITE_DENIED")
    quantum = Decimal(1).scaleb(-precision)
    quantized = dec.quantize(quantum)
    if quantized != dec:
        raise C2ESerializationError("DECIMAL_PRECISION_MISMATCH")
    if quantized == 0:
        quantized = abs(quantized)
    return format(quantized, f".{precision}f")


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, set):
        return [_canonicalize(item) for item in sorted(value, key=lambda item: json.dumps(item, sort_keys=True, default=str))]
    if isinstance(value, Decimal):
        raise C2ESerializationError("DECIMAL_REQUIRES_FIELD_PRECISION_CONTRACT")
    if isinstance(value, float):
        raise C2ESerializationError("RUNTIME_FLOAT_IDENTITY_DENIED")
    return value


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        if isinstance(exc, C2ESerializationError):
            raise
        raise C2ESerializationError("NON_CANONICAL_JSON_VALUE") from exc


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest(prefix: str, value: Any, length: int = 24) -> str:
    return f"{prefix}.{sha256_hex(value)[:length]}"


def logical_record_hash(record: Mapping[str, Any], *, hash_field: str = "logical_hash") -> str:
    payload = {key: value for key, value in record.items() if key != hash_field}
    return sha256_hex(payload)


def logical_stream_hash(records: list[Mapping[str, Any]]) -> str:
    hasher = hashlib.sha256()
    for record in records:
        hasher.update(canonical_bytes(record))
        hasher.update(b"\n")
    return hasher.hexdigest()
