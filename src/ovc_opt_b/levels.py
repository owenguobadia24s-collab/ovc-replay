from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Iterable, Sequence

from .models import Bar, LevelStatus, ReferenceLevel
from .replay import contiguous_segments


REGISTRY_ID = "OPT-B-REFERENCE-LEVELS"
REGISTRY_VERSION = "B-REF-0.1"
SWING_RULE_ID = "B.LEVEL.CONFIRMED_SWING_2X2.v0.1"
RANGE_RULE_ID = "B.LEVEL.ROLLING_RANGE_8.v0.1"


@dataclass(frozen=True, slots=True)
class LevelRegistry:
    registry_id: str
    registry_version: str
    instrument_id: str
    timeframe: str
    source_release_id: str
    levels: tuple[ReferenceLevel, ...]
    registry_hash: str


def _level_id(
    *,
    level_type: str,
    price: Decimal,
    first_valid_time: datetime,
    construction_rule_id: str,
    source_bar_ids: Sequence[str],
    instrument_id: str,
    timeframe: str,
    source_release_id: str,
    price_side: str,
) -> str:
    payload = {
        "registry_version": REGISTRY_VERSION,
        "level_type": level_type,
        "price": str(price),
        "first_valid_time": first_valid_time.astimezone(timezone.utc).isoformat(),
        "construction_rule_id": construction_rule_id,
        "source_bar_ids": list(source_bar_ids),
        "instrument_id": instrument_id,
        "timeframe": timeframe,
        "source_release_id": source_release_id,
        "price_side": price_side,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"level:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _make_level(
    *,
    level_type: str,
    price: Decimal,
    created_at: datetime,
    first_valid_time: datetime,
    construction_rule_id: str,
    source_bars: Sequence[Bar],
) -> ReferenceLevel:
    first = source_bars[0]
    source_bar_ids = tuple(bar.bar_id for bar in source_bars)
    return ReferenceLevel(
        level_id=_level_id(
            level_type=level_type,
            price=price,
            first_valid_time=first_valid_time,
            construction_rule_id=construction_rule_id,
            source_bar_ids=source_bar_ids,
            instrument_id=first.instrument_id,
            timeframe=first.timeframe,
            source_release_id=first.source_release_id,
            price_side=first.price_side,
        ),
        level_type=level_type,
        price=price,
        created_at=created_at,
        first_valid_time=first_valid_time,
        construction_rule_id=construction_rule_id,
        construction_rule_version="0.1",
        source_bar_ids=source_bar_ids,
        instrument_id=first.instrument_id,
        timeframe=first.timeframe,
        source_release_id=first.source_release_id,
        price_side=first.price_side,
        status=LevelStatus.ACTIVE,
    )


def _assert_registry_input(bars: Sequence[Bar]) -> None:
    if not bars:
        raise ValueError("level registry requires bars")
    identity = (
        bars[0].instrument_id,
        bars[0].timeframe,
        bars[0].source_release_id,
        bars[0].price_side,
    )
    seen: set[str] = set()
    previous_open: datetime | None = None
    for bar in bars:
        if (bar.instrument_id, bar.timeframe, bar.source_release_id, bar.price_side) != identity:
            raise ValueError("registry bars must share instrument, timeframe, release and price side")
        if bar.bar_id in seen:
            raise ValueError("duplicate bar_id")
        if previous_open is not None and bar.open_time <= previous_open:
            raise ValueError("registry bars must be strictly ordered")
        seen.add(bar.bar_id)
        previous_open = bar.open_time


def confirmed_swings(bars: Sequence[Bar], *, left: int = 2, right: int = 2) -> tuple[ReferenceLevel, ...]:
    """Create strict pivot levels only after the right confirmation bars close."""
    if left != 2 or right != 2:
        raise ValueError("B-REF-0.1 freezes swing confirmation at 2 left and 2 right bars")
    _assert_registry_input(bars)
    result: list[ReferenceLevel] = []
    for segment in contiguous_segments(bars):
        if len(segment) < left + 1 + right:
            continue
        for pivot_index in range(left, len(segment) - right):
            pivot = segment[pivot_index]
            window = segment[pivot_index - left : pivot_index + right + 1]
            neighbors = window[:left] + window[left + 1 :]
            first_valid_time = window[-1].close_time
            if all(pivot.high > bar.high for bar in neighbors):
                result.append(
                    _make_level(
                        level_type="PRIOR_SWING_HIGH",
                        price=pivot.high,
                        created_at=pivot.close_time,
                        first_valid_time=first_valid_time,
                        construction_rule_id=SWING_RULE_ID,
                        source_bars=window,
                    )
                )
            if all(pivot.low < bar.low for bar in neighbors):
                result.append(
                    _make_level(
                        level_type="PRIOR_SWING_LOW",
                        price=pivot.low,
                        created_at=pivot.close_time,
                        first_valid_time=first_valid_time,
                        construction_rule_id=SWING_RULE_ID,
                        source_bars=window,
                    )
                )
    return tuple(result)


def rolling_range_boundaries(bars: Sequence[Bar], *, window_bars: int = 8) -> tuple[ReferenceLevel, ...]:
    """Emit a new boundary only when the rolling eight-bar boundary price changes."""
    if window_bars != 8:
        raise ValueError("B-REF-0.1 freezes rolling range construction at eight bars")
    _assert_registry_input(bars)
    result: list[ReferenceLevel] = []
    for segment in contiguous_segments(bars):
        prior_high: Decimal | None = None
        prior_low: Decimal | None = None
        for end in range(window_bars - 1, len(segment)):
            window = segment[end - window_bars + 1 : end + 1]
            high = max(bar.high for bar in window)
            low = min(bar.low for bar in window)
            valid_time = window[-1].close_time
            if high != prior_high:
                result.append(
                    _make_level(
                        level_type="RANGE_HIGH",
                        price=high,
                        created_at=valid_time,
                        first_valid_time=valid_time,
                        construction_rule_id=RANGE_RULE_ID,
                        source_bars=window,
                    )
                )
                prior_high = high
            if low != prior_low:
                result.append(
                    _make_level(
                        level_type="RANGE_LOW",
                        price=low,
                        created_at=valid_time,
                        first_valid_time=valid_time,
                        construction_rule_id=RANGE_RULE_ID,
                        source_bars=window,
                    )
                )
                prior_low = low
    return tuple(result)


def build_level_registry(bars: Iterable[Bar]) -> LevelRegistry:
    source = tuple(bars)
    _assert_registry_input(source)
    levels = tuple(
        sorted(
            (*confirmed_swings(source), *rolling_range_boundaries(source)),
            key=lambda level: (level.first_valid_time, level.level_type, level.price, level.level_id),
        )
    )
    payload = [reference_level_to_dict(level) for level in levels]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return LevelRegistry(
        registry_id=REGISTRY_ID,
        registry_version=REGISTRY_VERSION,
        instrument_id=source[0].instrument_id,
        timeframe=source[0].timeframe,
        source_release_id=source[0].source_release_id,
        levels=levels,
        registry_hash=hashlib.sha256(canonical.encode()).hexdigest(),
    )


def eligible_levels(levels: Iterable[ReferenceLevel], candidate: Bar) -> tuple[ReferenceLevel, ...]:
    """Return levels known no later than candidate open; never select a silent 'best' level."""
    eligible = [
        level
        for level in levels
        if level.status is LevelStatus.ACTIVE
        and level.instrument_id == candidate.instrument_id
        and level.timeframe == candidate.timeframe
        and level.source_release_id == candidate.source_release_id
        and level.price_side == candidate.price_side
        and level.first_valid_time <= candidate.open_time
        and (level.retired_at is None or candidate.open_time < level.retired_at)
    ]
    return tuple(sorted(eligible, key=lambda level: (level.first_valid_time, level.level_type, level.level_id)))


def reference_level_to_dict(level: ReferenceLevel) -> dict[str, object]:
    return {
        "reference_level_id": level.level_id,
        "registry_version": REGISTRY_VERSION,
        "instrument_id": level.instrument_id,
        "timeframe": level.timeframe,
        "level_type": level.level_type,
        "price": str(level.price),
        "price_side": level.price_side,
        "created_at": level.created_at.astimezone(timezone.utc).isoformat(),
        "first_valid_time": level.first_valid_time.astimezone(timezone.utc).isoformat(),
        "construction_rule_id": level.construction_rule_id,
        "construction_rule_version": level.construction_rule_version,
        "source_bar_ids": list(level.source_bar_ids),
        "source_release_id": level.source_release_id,
        "status": level.status.value,
        "retired_at": level.retired_at.astimezone(timezone.utc).isoformat() if level.retired_at else None,
    }
