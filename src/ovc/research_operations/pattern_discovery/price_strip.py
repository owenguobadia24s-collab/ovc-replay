from __future__ import annotations

from typing import Any, Iterable, Mapping

from .models import PatternDiscoveryError, parse_utc


def build_price_strip(
    candidate: Mapping[str, Any],
    *,
    opt_a_bars: Iterable[Mapping[str, Any]],
    boundary_references: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    release_id = candidate.get("opt_a_release_id")
    clock = candidate.get("clock")
    start = candidate.get("window_start_utc")
    end = candidate.get("window_end_utc")
    trigger = candidate.get("trigger_first_valid_at")
    if not all(isinstance(value, str) and value for value in (release_id, clock, start, end, trigger)):
        return {"status": "NOT_AVAILABLE_SOURCE_UNRESOLVED"}
    start_dt, end_dt, trigger_dt = parse_utc(start), parse_utc(end), parse_utc(trigger)
    if trigger_dt < start_dt or trigger_dt > end_dt:
        raise PatternDiscoveryError("trigger marker must lie within the candidate window")
    rows: list[dict[str, Any]] = []
    for bar in opt_a_bars:
        if bar.get("release_id") != release_id or bar.get("clock") != clock:
            continue
        timestamp = str(bar.get("bar_end_utc") or "")
        try:
            timestamp_dt = parse_utc(timestamp)
        except PatternDiscoveryError:
            continue
        if start_dt <= timestamp_dt <= end_dt:
            rows.append({
                "bar_id": bar.get("bar_id"),
                "bar_end_utc": timestamp,
                "open": bar.get("open"),
                "high": bar.get("high"),
                "low": bar.get("low"),
                "close": bar.get("close"),
            })
    rows.sort(key=lambda item: (item["bar_end_utc"], str(item["bar_id"])))
    if not rows:
        return {"status": "NOT_AVAILABLE_SOURCE_UNRESOLVED"}
    if rows[-1]["bar_end_utc"] > str(candidate.get("represented_c2_time") or end):
        raise PatternDiscoveryError("price strip may not outrun represented C2 time")
    references = [
        {
            "reference_id": item.get("reference_id"),
            "value": item.get("value"),
            "reference_type": item.get("reference_type"),
            "source_c2_record_id": item.get("source_c2_record_id"),
        }
        for item in boundary_references
        if item.get("source_c2_record_id")
    ]
    return {
        "status": "AVAILABLE",
        "source_release_id": release_id,
        "clock": clock,
        "bars": rows,
        "markers": {
            "window_start_utc": start,
            "trigger_first_valid_at": trigger,
            "window_end_utc": end,
            "closure_reason": candidate.get("closure_reason"),
        },
        "boundary_references": references,
        "static_after_closure": candidate.get("status") in {"READY_FOR_REVIEW", "REVIEWED", "DISMISSED"},
    }
