from __future__ import annotations

from typing import Any, Iterable

from .models import ProspectiveBar, canonical_hash


def build_c1_records(bars: Iterable[ProspectiveBar]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    previous_close: dict[tuple[str, str], str] = {}
    for bar in sorted(bars, key=lambda item: (item.end_utc, item.clock, item.side)):
        key = (bar.clock, bar.side)
        prior = previous_close.get(key)
        evaluable = bar.quality_state == "COMPLETE" and bar.close is not None
        payload = {
            "prospective_bar_id": bar.bar_id,
            "clock": bar.clock,
            "side": bar.side,
            "bar_end_utc": bar.end_utc,
            "quality_state": bar.quality_state,
            "close": bar.close if evaluable else None,
            "prior_close": prior if evaluable else None,
            "direction": (
                "UP" if evaluable and prior is not None and float(bar.close) > float(prior)
                else "DOWN" if evaluable and prior is not None and float(bar.close) < float(prior)
                else "FLAT_OR_NOT_EVALUABLE"
            ),
            "release_membership": "NONE",
        }
        payload["c1_record_id"] = f"RPS.C1.{canonical_hash(payload)[:24]}"
        records.append(payload)
        if evaluable:
            previous_close[key] = str(bar.close)
    return records


def build_c2_records(c1_records: Iterable[dict[str, Any]], *, active_model_release_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for c1 in c1_records:
        direction = c1["direction"]
        quality = "EVALUABLE" if c1["quality_state"] == "COMPLETE" else "NOT_EVALUABLE"
        payload = {
            "c1_record_id": c1["c1_record_id"],
            "bar_end_utc": c1["bar_end_utc"],
            "clock": c1["clock"],
            "side": c1["side"],
            "active_c2_model_release_id": active_model_release_id,
            "axes": {
                "LOCATION": "UNRESOLVED_FIXTURE",
                "MOTION": direction,
                "ORGANISATION": "UNRESOLVED_FIXTURE",
                "INTERACTION": "UNRESOLVED_FIXTURE",
                "QUALITY": quality,
            },
            "historical_release_membership": False,
            "operation_mode": "TIME_GATED_REPLAY",
        }
        payload["c2_record_id"] = f"RPS.C2.{canonical_hash(payload)[:24]}"
        records.append(payload)
    return records
