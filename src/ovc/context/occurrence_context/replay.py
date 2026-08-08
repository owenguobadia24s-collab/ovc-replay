from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .builder import build_context
from .models import BuildRequest
from .serialization import logical_hash


def replay_contexts(requests: Iterable[BuildRequest]) -> dict[str, Any]:
    records = [build_context(request) for request in requests]
    records.sort(key=lambda item: item["occurrence_context_id"])
    ids = [item["occurrence_context_id"] for item in records]
    if len(ids) != len(set(ids)):
        raise ValueError("OC_ID_LOGICAL_HASH_MISMATCH")
    payload = {"schema": "occurrence_context_replay/v0_1", "records": records}
    return {**payload, "logical_hash": logical_hash(payload)}
