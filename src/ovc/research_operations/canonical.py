from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(value: Any, *, trailing_newline: bool = True) -> bytes:
    text = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    if trailing_newline:
        text += "\n"
    return text.encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value, trailing_newline=False)).hexdigest()
