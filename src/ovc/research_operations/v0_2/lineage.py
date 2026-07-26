from __future__ import annotations

from typing import Any, Iterable


def inspect_lineage(records: Iterable[dict[str, Any]], source_object_id: str) -> dict[str, Any]:
    matches = [dict(row) for row in records if row.get("source_object_id") == source_object_id]
    if not matches:
        return {"status": "NOT_FOUND", "source_object_id": source_object_id, "trace": [], "writes": "NONE"}
    if len(matches) > 1:
        return {"status": "AMBIGUOUS", "source_object_id": source_object_id, "trace": [], "writes": "NONE"}
    row = matches[0]
    trace = [{"kind": "OBSERVATION", "id": source_object_id}]
    for key in ("parent_object_id", "manifest_sha256", "release_id"):
        if row.get(key):
            trace.append({"kind": key.upper(), "id": row[key]})
    return {"status": "PASS", "source_object_id": source_object_id, "trace": trace, "writes": "NONE"}
