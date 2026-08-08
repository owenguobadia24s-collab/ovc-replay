from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .builder import OccurrenceContextError
from .chronology import parse_rfc3339

SESSION_REGISTRY_ID = "OC.CALENDAR_SESSION_BINDINGS.v0.1"


def calendar_context_for_interval(start: str, source_quality: Mapping[str, Any] | None = None) -> dict[str, Any]:
    timestamp = parse_rfc3339(start)
    return {
        "calendar_year": timestamp.year,
        "calendar_month": timestamp.month,
        "calendar_quarter": ((timestamp.month - 1) // 3) + 1,
        "era_partition_ids": [],
        "calendar_quality_context": dict(source_quality or {"status": "AVAILABLE"}),
    }


def session_context_for_interval(start: str) -> dict[str, Any]:
    parse_rfc3339(start)
    # The governed registry deliberately contains no active session/A-L boundary definitions.
    return {
        "session_membership_ids": [],
        "a_l_block_id": None,
        "registry_id": SESSION_REGISTRY_ID,
        "status": "UNAVAILABLE",
        "reason_codes": ["OC_SESSION_UNRESOLVED"],
    }


def assert_session_not_guessed(session_context: Mapping[str, Any]) -> None:
    if session_context.get("session_membership_ids") or session_context.get("a_l_block_id") is not None:
        raise OccurrenceContextError("OC_SESSION_UNRESOLVED", "session/A-L membership requires a governed registry")
