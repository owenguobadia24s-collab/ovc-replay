from __future__ import annotations

import hashlib
import json
from typing import Any


def _identity(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def compare_snapshots(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_hash = _identity(left)
    right_hash = _identity(right)
    left_keys = set(left)
    right_keys = set(right)
    changed = sorted(key for key in left_keys & right_keys if left[key] != right[key])
    return {
        "status": "IDENTICAL" if left_hash == right_hash else "DIFFERENT",
        "left_sha256": left_hash,
        "right_sha256": right_hash,
        "added_keys": sorted(right_keys - left_keys),
        "removed_keys": sorted(left_keys - right_keys),
        "changed_keys": changed,
        "writes": "NONE",
    }
