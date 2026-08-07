from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

SLOT_LABELS = "ABCDEFGHIJKL"

def _dt(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

def enumerate_paired_2h_coverage(bid_timestamps_ms: Iterable[int], ask_timestamps_ms: Iterable[int]) -> dict[str, object]:
    bid=set(int(x) for x in bid_timestamps_ms)
    ask=set(int(x) for x in ask_timestamps_ms)
    paired=bid & ask
    by_day: dict[str,set[str]]=defaultdict(set)
    for value in sorted(paired):
        current=_dt(value)
        if current.minute or current.second or current.microsecond or current.hour % 2:
            raise ValueError("2H_A_L timestamp must be aligned to even UTC hour")
        by_day[current.date().isoformat()].add(SLOT_LABELS[current.hour // 2])
    slot_days={label:sum(label in slots for slots in by_day.values()) for label in SLOT_LABELS}
    return {
        "bid_count":len(bid), "ask_count":len(ask), "paired_count":len(paired),
        "pair_sets_equal":bid==ask, "eligible_market_days":len(by_day),
        "slot_day_counts":slot_days, "minimum_slot_day_count":min(slot_days.values()) if slot_days else 0,
        "days_with_all_12_slots":sum(len(slots)==12 for slots in by_day.values()),
    }

def stage_a_floor(coverage: dict[str, object], *, minimum_days: int = 20, minimum_slot_days: int = 15) -> dict[str, object]:
    return {
        "minimum_eligible_market_days":minimum_days,
        "minimum_each_slot_days":minimum_slot_days,
        "eligible_market_days_pass":int(coverage["eligible_market_days"]) >= minimum_days,
        "all_slots_pass":int(coverage["minimum_slot_day_count"]) >= minimum_slot_days,
        "overall_pass":int(coverage["eligible_market_days"]) >= minimum_days and int(coverage["minimum_slot_day_count"]) >= minimum_slot_days,
    }

def exact_pair_count(n: int) -> int:
    if n < 0:
        raise ValueError("n cannot be negative")
    return n * (n - 1) // 2
