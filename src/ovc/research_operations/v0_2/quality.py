from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def project_quality(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = sorted((dict(row) for row in records), key=lambda row: (row.get("first_valid_at", ""), row.get("source_object_id", "")))
    ids = [row.get("source_object_id") for row in rows]
    duplicate_ids = sorted(key for key, count in Counter(ids).items() if key is not None and count > 1)
    missing_required = []
    required = ("source_object_id", "clock", "side", "first_valid_at", "schema_version")
    for index, row in enumerate(rows):
        missing = [field for field in required if row.get(field) in (None, "")]
        if missing:
            missing_required.append({"row": index, "fields": missing})
    status = "PASS" if not duplicate_ids and not missing_required else "DEGRADED"
    return {
        "status": status,
        "record_count": len(rows),
        "duplicate_source_object_ids": duplicate_ids,
        "missing_required_fields": missing_required,
        "writes": "NONE",
    }
