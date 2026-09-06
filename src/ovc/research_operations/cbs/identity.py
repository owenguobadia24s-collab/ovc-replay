from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


class CBSContractError(ValueError):
    """Fail-closed CBS contract violation carrying a stable reason code."""


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise CBSContractError("CBS_NON_FINITE_CANONICAL_VALUE")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CBSContractError("CBS_CANONICAL_KEY_NOT_STRING")
            _reject_non_finite(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_non_finite(child)


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    _reject_non_finite(value)
    return json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def canonical_id(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def seal_object(payload: Mapping[str, Any], *, id_field: str) -> dict[str, Any]:
    if id_field in payload:
        raise CBSContractError("CBS_ID_FIELD_ALREADY_PRESENT")
    body = dict(payload)
    return {**body, id_field: canonical_id(body)}


def verify_object(value: Mapping[str, Any], *, id_field: str) -> None:
    claimed = str(value.get(id_field, ""))
    body = {key: child for key, child in value.items() if key != id_field}
    if len(claimed) != 64 or canonical_id(body) != claimed:
        raise CBSContractError("CBS_CANONICAL_ID_MISMATCH")
