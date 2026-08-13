from __future__ import annotations

from datetime import datetime, timezone


class ChronologyError(ValueError):
    pass


def parse_utc_z(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ChronologyError("C2P_TIME_NOT_UTC_Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ChronologyError("C2P_TIME_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ChronologyError("C2P_TIME_NOT_UTC_Z")
    return parsed


def validate_causal_times(
    *,
    market_effective_start: str,
    market_effective_end: str | None,
    first_valid_time: str,
    evaluation_cutoff: str,
) -> None:
    start = parse_utc_z(market_effective_start)
    end = parse_utc_z(market_effective_end) if market_effective_end is not None else None
    fvt = parse_utc_z(first_valid_time)
    cutoff = parse_utc_z(evaluation_cutoff)
    if end is not None and end < start:
        raise ChronologyError("C2P_EFFECTIVE_END_BEFORE_START")
    if fvt > cutoff:
        raise ChronologyError("C2P_FVT_AFTER_CUTOFF")
