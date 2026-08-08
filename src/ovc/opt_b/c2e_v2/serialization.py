"""Deterministic serialization helpers for the C2E v0.2 handoff.

WP1 permits JSON-compatible source values only.  Identity-bearing numeric
canonicalisation is tightened further by C2E2-WP2; this module deliberately
contains no machine/path/time dependent inputs.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


class C2ESerializationError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise C2ESerializationError("NON_CANONICAL_JSON_VALUE") from exc


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest(prefix: str, value: Any, length: int = 24) -> str:
    return f"{prefix}.{sha256_hex(value)[:length]}"
