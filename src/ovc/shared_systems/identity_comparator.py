"""Independent comparator for the frozen canonical JSON/NFC identity profile.

This implementation deliberately does not import ``shared_systems.identity`` so
golden-vector agreement is not self-comparison.
"""

from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import math
from typing import Any, Mapping
import unicodedata


class ComparatorError(ValueError):
    pass


def _number(value: int | float | Decimal) -> str:
    if isinstance(value, float) and not math.isfinite(value):
        raise ComparatorError("NON_FINITE_NUMBER")
    decimal = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
    if decimal.is_zero() and decimal.is_signed():
        raise ComparatorError("NEGATIVE_ZERO_REJECTED")
    if decimal.is_zero():
        return "0"
    text = format(decimal, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _string(value: str) -> str:
    if unicodedata.normalize("NFC", value) != value:
        raise ComparatorError("UNICODE_NOT_NFC")
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, (int, float, Decimal)):
        return _number(value)
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ComparatorError("OBJECT_KEY_NOT_STRING")
        return "{" + ",".join(f"{_string(key)}:{_encode(value[key])}" for key in sorted(value)) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    raise ComparatorError("UNSUPPORTED_TYPE")


def canonical_bytes(value: Any) -> bytes:
    return _encode(value).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
