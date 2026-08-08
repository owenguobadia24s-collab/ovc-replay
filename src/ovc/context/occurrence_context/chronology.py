from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


def parse_rfc3339(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("OccurrenceContext timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def format_rfc3339(value: datetime) -> str:
    value = value.astimezone(timezone.utc)
    if value.microsecond:
        return value.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def compute_first_valid_time(
    anchor_first_valid_time: str,
    dependency_first_valid_times: Iterable[str],
    registry_first_valid_times: Iterable[str],
    confirmation_time: str,
) -> str:
    values = [parse_rfc3339(anchor_first_valid_time), parse_rfc3339(confirmation_time)]
    values.extend(parse_rfc3339(item) for item in dependency_first_valid_times)
    values.extend(parse_rfc3339(item) for item in registry_first_valid_times)
    return format_rfc3339(max(values))


def assert_not_backdated(proposed: str, required_times: Iterable[str]) -> None:
    candidate = parse_rfc3339(proposed)
    if any(parse_rfc3339(item) > candidate for item in required_times):
        raise ValueError("OC_TIME_BACKDATE_DENIED")
