from __future__ import annotations
import json, unicodedata
from decimal import Decimal

class CanonicalizationError(ValueError):
    pass

def _walk(value):
    if isinstance(value, str):
        if not unicodedata.is_normalized("NFC", value):
            raise CanonicalizationError("C2P_TEXT_NOT_NFC")
        return value
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise CanonicalizationError("binary floats forbidden")
    if isinstance(value, Decimal):
        if not value.is_finite() or value.is_zero() and value.is_signed():
            raise CanonicalizationError("nonfinite/negative zero forbidden")
        s = format(value, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s or "0"
    if isinstance(value, list):
        return [_walk(x) for x in value]
    if isinstance(value, dict):
        return {k: _walk(v) for k, v in value.items()}
    raise CanonicalizationError(f"unsupported type: {type(value).__name__}")

def canonical_bytes(value):
    normalized=_walk(value)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
