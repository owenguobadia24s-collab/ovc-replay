from __future__ import annotations

import hashlib
import json


def canonical_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def record_id(identity_payload: dict) -> str:
    return f"c1:{canonical_hash(identity_payload)}"
