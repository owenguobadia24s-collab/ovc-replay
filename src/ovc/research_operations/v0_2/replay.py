from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def replay_to_cutoff(records: Iterable[dict[str, Any]], cutoff: str, role: str) -> dict[str, Any]:
    if role == "VALIDATION":
        raise PermissionError("VALIDATION_DENY_BEFORE_PATH_RESOLUTION")
    if role not in {"DISCOVERY", "DEVELOPMENT"}:
        raise ValueError(f"UNKNOWN_ROLE:{role}")
    limit = _parse(cutoff)
    accepted = []
    rejected = []
    for row in records:
        candidate = dict(row)
        timestamp = candidate.get("first_valid_at")
        if not timestamp or _parse(timestamp) > limit:
            rejected.append(candidate.get("source_object_id"))
        else:
            accepted.append(candidate)
    accepted.sort(key=lambda row: (row["first_valid_at"], row.get("source_object_id", "")))
    return {
        "role": role,
        "cutoff": cutoff,
        "accepted": accepted,
        "accepted_count": len(accepted),
        "post_cutoff_rejected": sorted(item for item in rejected if item is not None),
        "writes": "NONE",
    }
