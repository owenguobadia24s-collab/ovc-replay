from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Iterable

from .models import ProspectiveBar, SourceBar, canonical_hash, parse_utc


_CLOCK_MINUTES = {"15M": 15, "2H_A_L": 120, "H1_M1_DERIVED": 60}


def aggregate_m1(
    bars: Iterable[SourceBar],
    *,
    clock: str,
    side: str,
    admissible_cutoff_utc: str,
) -> list[ProspectiveBar]:
    if clock not in _CLOCK_MINUTES:
        raise ValueError(f"unsupported clock: {clock}")
    expected = _CLOCK_MINUTES[clock]
    cutoff = parse_utc(admissible_cutoff_utc)
    ordered = sorted((bar for bar in bars if bar.side == side), key=lambda bar: parse_utc(bar.timestamp_utc))
    if any(parse_utc(bar.timestamp_utc) >= cutoff for bar in ordered):
        raise ValueError("future source object exceeds admissible cutoff")
    if not ordered:
        return []

    buckets: dict[str, list[SourceBar]] = {}
    for bar in ordered:
        timestamp = parse_utc(bar.timestamp_utc)
        minute_of_day = timestamp.hour * 60 + timestamp.minute
        bucket_minute = (minute_of_day // expected) * expected
        start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=bucket_minute)
        buckets.setdefault(start.isoformat().replace("+00:00", "Z"), []).append(bar)

    result: list[ProspectiveBar] = []
    for start_text in sorted(buckets):
        parents = buckets[start_text]
        start = parse_utc(start_text)
        end = start + timedelta(minutes=expected)
        timestamps = [parse_utc(parent.timestamp_utc) for parent in parents]
        contiguous = (
            len(parents) == expected
            and len(set(timestamps)) == expected
            and timestamps == [start + timedelta(minutes=index) for index in range(expected)]
            and end <= cutoff
        )
        parent_ids = tuple(parent.object_id for parent in parents)
        identity = canonical_hash({"clock": clock, "side": side, "start": start_text, "parents": parent_ids})[:24]
        if not contiguous:
            result.append(
                ProspectiveBar(
                    bar_id=f"RPS.BAR.{identity}", clock=clock, side=side,
                    start_utc=start_text, end_utc=end.isoformat().replace("+00:00", "Z"),
                    open=None, high=None, low=None, close=None, volume=None,
                    parent_source_object_ids=parent_ids, quality_state="QUARANTINED_INCOMPLETE_PARENT_SET",
                )
            )
            continue
        result.append(
            ProspectiveBar(
                bar_id=f"RPS.BAR.{identity}", clock=clock, side=side,
                start_utc=start_text, end_utc=end.isoformat().replace("+00:00", "Z"),
                open=str(parents[0].open), high=str(max(parent.high for parent in parents)),
                low=str(min(parent.low for parent in parents)), close=str(parents[-1].close),
                volume=str(sum((parent.volume for parent in parents), Decimal("0"))),
                parent_source_object_ids=parent_ids, quality_state="COMPLETE",
            )
        )
    return result
