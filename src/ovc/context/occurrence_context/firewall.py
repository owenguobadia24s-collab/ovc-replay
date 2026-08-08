from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .serialization import logical_hash

FORBIDDEN_KEYS = {
    "outcome",
    "future_return",
    "mfe",
    "mae",
    "probability",
    "edge",
    "risk",
    "exposure",
    "trade",
    "execution",
    "validation_occurrence_payload",
}


def _walk(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                raise ValueError(f"OC_DEP_FORBIDDEN_FIELD:{key}")
            _walk(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            _walk(child)


def assert_no_forbidden_fields(value: Any) -> None:
    _walk(value)


def upstream_fingerprint(value: Any) -> str:
    return logical_hash(value)


def assert_upstream_unchanged(before_fingerprint: str, value_after: Any) -> None:
    if upstream_fingerprint(value_after) != before_fingerprint:
        raise ValueError("OC_ID_ANCHOR_MUTATION")
