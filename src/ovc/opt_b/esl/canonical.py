from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal
from typing import Any, Mapping, Sequence


class CanonicalizationError(ValueError):
    pass


_FIXED_DIMENSION_ORDER = {
    "LOCATION": 0,
    "MOTION": 1,
    "ORGANISATION": 2,
    "INTERACTION": 3,
}

_LEXICAL_ARRAY_FIELDS = {
    "development_refs",
    "missing_ref_ids",
    "optional_ref_ids",
    "persistence_refs",
    "reason_codes",
    "required_ref_ids",
    "source_generation_ids",
    "source_ref_ids",
}

_OBJECT_ID_ARRAY_FIELDS = {"dependency_refs": "ref_id"}
_IDENTITY_EXCLUDED_TOP_LEVEL = frozenset({"occurrence_record_id", "logical_hash"})


def _number_text(value: int | float | Decimal) -> str:
    if isinstance(value, bool):
        raise CanonicalizationError("ESL_CANONICAL_BOOL_AS_NUMBER")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError("ESL_CANONICAL_NONFINITE_NUMBER")
        if value == 0.0 and math.copysign(1.0, value) < 0:
            raise CanonicalizationError("ESL_CANONICAL_NEGATIVE_ZERO")
        decimal_value = Decimal(str(value))
    elif isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError("ESL_CANONICAL_NONFINITE_NUMBER")
        if value.is_zero() and value.is_signed():
            raise CanonicalizationError("ESL_CANONICAL_NEGATIVE_ZERO")
        decimal_value = value
    else:
        raise CanonicalizationError("ESL_CANONICAL_UNSUPPORTED_NUMBER")

    if decimal_value.is_zero():
        return "0"
    normalized = decimal_value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text == "-0":
        raise CanonicalizationError("ESL_CANONICAL_NEGATIVE_ZERO")
    return text


def _string_text(value: str) -> str:
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError("ESL_CANONICAL_INVALID_UTF8_STRING") from exc
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _ordered_array(values: Sequence[Any], path: tuple[str, ...]) -> list[Any]:
    field = path[-1] if path else ""
    items = list(values)
    if field == "facets":
        try:
            return sorted(items, key=lambda item: _FIXED_DIMENSION_ORDER[item["dimension"]])
        except (KeyError, TypeError) as exc:
            raise CanonicalizationError("ESL_CANONICAL_FACET_ORDER_UNRESOLVED") from exc
    if field in _LEXICAL_ARRAY_FIELDS:
        if not all(isinstance(item, str) for item in items):
            raise CanonicalizationError("ESL_CANONICAL_LEXICAL_ARRAY_NONSTRING:" + field)
        return sorted(items)
    if field in _OBJECT_ID_ARRAY_FIELDS:
        key = _OBJECT_ID_ARRAY_FIELDS[field]
        try:
            return sorted(items, key=lambda item: item[key])
        except (KeyError, TypeError) as exc:
            raise CanonicalizationError("ESL_CANONICAL_OBJECT_ARRAY_KEY_MISSING:" + field) from exc
    return items


def _emit(value: Any, path: tuple[str, ...]) -> str:
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
            raise CanonicalizationError("ESL_CANONICAL_OBJECT_KEY_NOT_STRING")
        parts = []
        for key in sorted(keys):
            parts.append(_string_text(key) + ":" + _emit(value[key], path + (key,)))
        return "{" + ",".join(parts) + "}"
    if isinstance(value, (list, tuple)):
        ordered = _ordered_array(value, path)
        return "[" + ",".join(_emit(item, path + ("[]",)) for item in ordered) + "]"
    raise CanonicalizationError("ESL_CANONICAL_UNSUPPORTED_TYPE:" + type(value).__name__)


def canonical_json_v1_bytes(value: Any) -> bytes:
    """Return canonical-json-v1 UTF-8 bytes for a schema-valid JSON-like value."""
    return _emit(value, ()).encode("utf-8")


def canonical_json_v1_text(value: Any) -> str:
    return canonical_json_v1_bytes(value).decode("utf-8")


def sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_json_v1_bytes(value)).hexdigest()


def identity_projection(
    payload: Mapping[str, Any],
    *,
    excluded_top_level_fields: frozenset[str] = _IDENTITY_EXCLUDED_TOP_LEVEL,
) -> dict[str, Any]:
    """Remove only the record's own top-level identifier/hash fields."""
    return {key: value for key, value in payload.items() if key not in excluded_top_level_fields}


def occurrence_logical_hash(payload: Mapping[str, Any]) -> str:
    return sha256_canonical(identity_projection(payload))


def occurrence_record_id(payload: Mapping[str, Any]) -> str:
    return "so1:" + occurrence_logical_hash(payload)


def evidence_frontier_logical_hash(payload: Mapping[str, Any]) -> str:
    return sha256_canonical(
        identity_projection(
            payload,
            excluded_top_level_fields=frozenset({"evidence_frontier_id", "logical_hash"}),
        )
    )
