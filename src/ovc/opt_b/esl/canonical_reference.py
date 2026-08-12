from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal
from typing import Any, Mapping


class ReferenceCanonicalizationError(ValueError):
    pass


_DIMENSIONS = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")
_SET_ARRAYS = {
    "development_refs",
    "missing_ref_ids",
    "optional_ref_ids",
    "persistence_refs",
    "reason_codes",
    "required_ref_ids",
    "source_generation_ids",
    "source_ref_ids",
}


def _decimal_token(number: Any) -> str:
    if isinstance(number, bool):
        raise ReferenceCanonicalizationError("REFERENCE_BOOL_NUMBER")
    if isinstance(number, int):
        return f"{number:d}"
    if isinstance(number, float):
        if not math.isfinite(number):
            raise ReferenceCanonicalizationError("REFERENCE_NONFINITE")
        if number == 0.0 and math.copysign(1.0, number) < 0:
            raise ReferenceCanonicalizationError("REFERENCE_NEGATIVE_ZERO")
        d = Decimal(str(number))
    elif isinstance(number, Decimal):
        if not number.is_finite():
            raise ReferenceCanonicalizationError("REFERENCE_NONFINITE")
        if number.is_zero() and number.is_signed():
            raise ReferenceCanonicalizationError("REFERENCE_NEGATIVE_ZERO")
        d = number
    else:
        raise ReferenceCanonicalizationError("REFERENCE_BAD_NUMBER")
    if d == 0:
        return "0"
    token = format(d.normalize(), "f")
    if "." in token:
        token = token.rstrip("0").rstrip(".")
    if token == "-0":
        raise ReferenceCanonicalizationError("REFERENCE_NEGATIVE_ZERO")
    return token


def _quote(text: str) -> str:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ReferenceCanonicalizationError("REFERENCE_BAD_UTF8") from exc
    return json.dumps(text, ensure_ascii=False, separators=(",", ":"))


def _array_order(items: list[Any], field: str) -> list[Any]:
    if field == "facets":
        rank = {name: i for i, name in enumerate(_DIMENSIONS)}
        try:
            return sorted(items, key=lambda x: rank[x["dimension"]])
        except (KeyError, TypeError) as exc:
            raise ReferenceCanonicalizationError("REFERENCE_BAD_FACETS") from exc
    if field in _SET_ARRAYS:
        if not all(isinstance(item, str) for item in items):
            raise ReferenceCanonicalizationError("REFERENCE_NONSTRING_SET_ARRAY")
        return sorted(items)
    if field == "dependency_refs":
        try:
            return sorted(items, key=lambda x: x["ref_id"])
        except (KeyError, TypeError) as exc:
            raise ReferenceCanonicalizationError("REFERENCE_BAD_DEPENDENCY_REFS") from exc
    return items


def _walk(value: Any, field: str = "") -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return _decimal_token(value)
    if isinstance(value, str):
        return _quote(value)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ReferenceCanonicalizationError("REFERENCE_NONSTRING_KEY")
        return "{" + ",".join(
            _quote(key) + ":" + _walk(value[key], key)
            for key in sorted(value)
        ) + "}"
    if isinstance(value, (list, tuple)):
        ordered = _array_order(list(value), field)
        return "[" + ",".join(_walk(item, "") for item in ordered) + "]"
    raise ReferenceCanonicalizationError("REFERENCE_UNSUPPORTED:" + type(value).__name__)


def reference_canonical_json_v1_bytes(value: Any) -> bytes:
    return _walk(value).encode("utf-8")


def reference_sha256(value: Any) -> str:
    return hashlib.sha256(reference_canonical_json_v1_bytes(value)).hexdigest()
