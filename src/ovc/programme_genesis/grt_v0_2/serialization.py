from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping


SERIALIZATION_ID = "canonical-json-v1"


class CanonicalJSONError(ValueError):
    """Raised when a value cannot be represented by canonical-json-v1."""


def _number_text(value: int | float | Decimal) -> str:
    if isinstance(value, bool):
        raise CanonicalJSONError("GRT_CANONICAL_BOOL_AS_NUMBER")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalJSONError("GRT_CANONICAL_NONFINITE_NUMBER")
        if value == 0.0 and math.copysign(1.0, value) < 0:
            raise CanonicalJSONError("GRT_CANONICAL_NEGATIVE_ZERO")
        value = Decimal(str(value))
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CanonicalJSONError("GRT_CANONICAL_UNSUPPORTED_NUMBER")
    if value.is_zero() and value.is_signed():
        raise CanonicalJSONError("GRT_CANONICAL_NEGATIVE_ZERO")
    if value.is_zero():
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text == "-0":
        raise CanonicalJSONError("GRT_CANONICAL_NEGATIVE_ZERO")
    return text


def _string_text(value: str) -> str:
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise CanonicalJSONError("GRT_CANONICAL_INVALID_UTF8_STRING") from exc
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _emit(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return _number_text(value)
    if isinstance(value, str):
        return _string_text(value)
    if isinstance(value, Mapping):
        keys = list(value.keys())
        if not all(isinstance(key, str) for key in keys):
            raise CanonicalJSONError("GRT_CANONICAL_OBJECT_KEY_NOT_STRING")
        return "{" + ",".join(
            _string_text(key) + ":" + _emit(value[key]) for key in sorted(keys)
        ) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_emit(item) for item in value) + "]"
    raise CanonicalJSONError(
        "GRT_CANONICAL_UNSUPPORTED_TYPE:" + type(value).__name__
    )


def canonical_json_v1_bytes(value: Any) -> bytes:
    """Return canonical-json-v1 UTF-8 bytes.

    Object keys are lexical; arrays preserve declared semantic order. Callers
    that own set-like arrays must sort them before hashing.
    """
    return _emit(value).encode("utf-8")


def canonical_json_v1_text(value: Any) -> str:
    return canonical_json_v1_bytes(value).decode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_v1_bytes(value)).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity_projection(
    payload: Mapping[str, Any],
    *,
    excluded_fields: frozenset[str],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in excluded_fields
    }
