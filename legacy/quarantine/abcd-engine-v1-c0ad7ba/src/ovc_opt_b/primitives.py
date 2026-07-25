from __future__ import annotations

from decimal import Decimal
from statistics import median
from typing import Sequence

from .models import Bar, assert_compatible_bars


ZERO = Decimal("0")


def true_range(bars: Sequence[Bar], index: int) -> Decimal:
    if index <= 0 or index >= len(bars):
        raise IndexError("true range requires a previous bar")
    bar = bars[index]
    previous_close = bars[index - 1].close
    return max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close))


def atr_before(bars: Sequence[Bar], index: int, periods: int = 20) -> Decimal:
    """Mean true range of the `periods` bars strictly before index."""
    assert_compatible_bars(bars)
    if index < periods + 1:
        raise ValueError("insufficient ATR history")
    values = [true_range(bars, i) for i in range(index - periods, index)]
    result = sum(values, ZERO) / Decimal(periods)
    if result == 0:
        raise ValueError("zero ATR baseline")
    return result


def body_fraction(bar: Bar) -> Decimal:
    span = bar.high - bar.low
    if span == 0:
        raise ValueError("zero-range bar")
    return abs(bar.close - bar.open) / span


def close_location(bar: Bar, upward: bool) -> Decimal:
    span = bar.high - bar.low
    if span == 0:
        raise ValueError("zero-range bar")
    return ((bar.close - bar.low) if upward else (bar.high - bar.close)) / span


def overlap_fraction(left: Bar, right: Bar) -> Decimal:
    overlap = max(ZERO, min(left.high, right.high) - max(left.low, right.low))
    union = max(left.high, right.high) - min(left.low, right.low)
    if union == 0:
        raise ValueError("zero union")
    return overlap / union


def path_efficiency(bars: Sequence[Bar], start: int, end: int) -> Decimal:
    if not 0 <= start < end < len(bars):
        raise IndexError("invalid efficiency window")
    path = sum((abs(bars[i].close - bars[i - 1].close) for i in range(start + 1, end + 1)), ZERO)
    if path == 0:
        return ZERO
    return abs(bars[end].close - bars[start].close) / path


def decimal_median(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("median requires values")
    return median(values)


def tolerances(bar: Bar, atr: Decimal) -> dict[str, Decimal]:
    epsilon = bar.price_increment
    return {
        "touch": max(Decimal(2) * epsilon, Decimal("0.05") * atr),
        "breach": max(Decimal(2) * epsilon, Decimal("0.10") * atr),
        "return": max(Decimal(2) * epsilon, Decimal("0.10") * atr),
        "depart": max(Decimal(4) * epsilon, Decimal("0.50") * atr),
    }

