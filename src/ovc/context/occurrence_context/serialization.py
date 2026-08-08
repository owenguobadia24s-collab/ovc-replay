from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def _validate(value: Any) -> None:
    if isinstance(value, float):
        raise TypeError("binary float is forbidden in canonical OccurrenceContext serialization")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical mapping keys must be strings")
            _validate(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            _validate(child)


def canonical_json(value: Any) -> str:
    _validate(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_payload(namespace: str, value: Any) -> str:
    encoded = (namespace + "\0" + canonical_json(value)).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def logical_hash(value: Any) -> str:
    return sha256_payload("OVC.LOGICAL", value)
