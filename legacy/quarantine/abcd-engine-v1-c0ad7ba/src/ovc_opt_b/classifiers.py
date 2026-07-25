from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from .models import (
    Bar,
    Direction,
    ReferenceLevel,
    State,
    TermRecord,
    TermStatus,
    assert_compatible_bars,
)
from .primitives import (
    ZERO,
    atr_before,
    body_fraction,
    close_location,
    decimal_median,
    overlap_fraction,
    path_efficiency,
    tolerances,
    true_range,
)


def _record(
    term_id: str,
    bars: Sequence[Bar],
    indices: Sequence[int],
    direction: Direction,
    status: TermStatus,
    anchor_index: int,
    valid_index: int,
    measurements: dict[str, Decimal | int | str],
    level: ReferenceLevel | None = None,
    reasons: tuple[str, ...] = (),
) -> TermRecord:
    first = bars[0]
    return TermRecord(
        term_id=term_id,
        instrument_id=first.instrument_id,
        timeframe=first.timeframe,
        direction=direction,
        anchor_time=bars[anchor_index].close_time,
        first_valid_time=bars[valid_index].close_time,
        status=status,
        input_bar_ids=tuple(bars[i].bar_id for i in indices),
        source_release_id=first.source_release_id,
        measurements={key: str(value) for key, value in measurements.items()},
        reference_level_id=level.level_id if level else None,
        reason_codes=reasons,
    )


def _ensure_level_preexists(level: ReferenceLevel, bar: Bar) -> None:
    if level.status.value != "ACTIVE":
        raise ValueError("reference level must be ACTIVE")
    if (
        level.instrument_id,
        level.timeframe,
        level.source_release_id,
        level.price_side,
    ) != (bar.instrument_id, bar.timeframe, bar.source_release_id, bar.price_side):
        raise ValueError("reference level and candidate bar must share source identity")
    if level.first_valid_time > bar.open_time:
        raise ValueError("reference level must be known no later than candidate open")
    if level.retired_at is not None and bar.open_time >= level.retired_at:
        raise ValueError("reference level was retired before the candidate")


def compression(bars: Sequence[Bar], end_index: int) -> TermRecord:
    assert_compatible_bars(bars)
    if end_index < 28 or end_index >= len(bars):
        raise ValueError("compression requires 28 prior/current bars")
    start = end_index - 7
    baseline_start = end_index - 27
    baseline_end = end_index - 8
    candidate_tr = [true_range(bars, i) for i in range(start, end_index + 1)]
    baseline_tr = [true_range(bars, i) for i in range(baseline_start, baseline_end + 1)]
    tr_ratio = decimal_median(candidate_tr) / decimal_median(baseline_tr)
    span = max(b.high for b in bars[start : end_index + 1]) - min(
        b.low for b in bars[start : end_index + 1]
    )
    span_atr = span / atr_before(bars, start)
    overlaps = [overlap_fraction(bars[i - 1], bars[i]) for i in range(start + 1, end_index + 1)]
    mean_overlap = sum(overlaps, ZERO) / Decimal(len(overlaps))
    efficiency = path_efficiency(bars, start, end_index)
    passed = (
        tr_ratio <= Decimal("0.70")
        and span_atr <= Decimal("2.00")
        and mean_overlap >= Decimal("0.55")
        and efficiency <= Decimal("0.35")
    )
    return _record(
        "B.TERM.COMPRESSION.v0.1",
        bars,
        range(baseline_start, end_index + 1),
        Direction.NONE,
        TermStatus.CONFIRMED if passed else TermStatus.FAILED,
        start,
        end_index,
        {
            "tr_ratio": tr_ratio,
            "span_atr": span_atr,
            "mean_overlap": mean_overlap,
            "path_efficiency": efficiency,
        },
        reasons=() if passed else ("COMPRESSION_THRESHOLDS_NOT_MET",),
    )


def displacement(bars: Sequence[Bar], index: int) -> TermRecord:
    assert_compatible_bars(bars)
    if index < 21 or index >= len(bars):
        raise ValueError("displacement requires 20-bar ATR history")
    atr = atr_before(bars, index)
    bar = bars[index]
    direction = Direction.UP if bar.close > bar.open else Direction.DOWN if bar.close < bar.open else Direction.NONE
    tr_atr = true_range(bars, index) / atr
    close_travel = abs(bar.close - bars[index - 1].close) / atr
    try:
        body = body_fraction(bar)
        location = close_location(bar, direction is Direction.UP) if direction is not Direction.NONE else ZERO
    except ValueError:
        body = ZERO
        location = ZERO
    passed = (
        direction is not Direction.NONE
        and tr_atr >= Decimal("1.50")
        and body >= Decimal("0.65")
        and location >= Decimal("0.80")
        and close_travel >= Decimal("0.80")
    )
    return _record(
        "B.TERM.DISPLACEMENT.v0.1",
        bars,
        range(index - 20, index + 1),
        direction,
        TermStatus.CONFIRMED if passed else TermStatus.FAILED,
        index,
        index,
        {"tr_atr": tr_atr, "body_fraction": body, "close_location": location, "close_travel_atr": close_travel},
        reasons=() if passed else ("DISPLACEMENT_THRESHOLDS_NOT_MET",),
    )


def _acceptance_passes(
    bars: Sequence[Bar], end_index: int, level: ReferenceLevel, direction: Direction, anchor_atr: Decimal
) -> bool:
    if end_index < 3:
        return False
    start = end_index - 3
    return_distance = max(Decimal(2) * bars[start].price_increment, Decimal("0.10") * anchor_atr)
    if direction is Direction.UP:
        closes = sum(b.close >= level.price + return_distance for b in bars[start : end_index + 1])
        return closes >= 3 and bars[end_index].close >= level.price + return_distance and min(
            b.low for b in bars[start : end_index + 1]
        ) >= level.price - Decimal("0.25") * anchor_atr
    closes = sum(b.close <= level.price - return_distance for b in bars[start : end_index + 1])
    return closes >= 3 and bars[end_index].close <= level.price - return_distance and max(
        b.high for b in bars[start : end_index + 1]
    ) <= level.price + Decimal("0.25") * anchor_atr


def acceptance(bars: Sequence[Bar], end_index: int, level: ReferenceLevel, direction: Direction) -> TermRecord:
    assert_compatible_bars(bars)
    if direction not in (Direction.UP, Direction.DOWN):
        raise ValueError("acceptance direction must be UP or DOWN")
    start = end_index - 3
    if start < 21 or end_index >= len(bars):
        raise ValueError("acceptance requires four bars plus ATR history")
    _ensure_level_preexists(level, bars[start])
    atr = atr_before(bars, start)
    passed = _acceptance_passes(bars, end_index, level, direction, atr)
    tol = tolerances(bars[start], atr)
    closes_beyond = sum(
        b.close >= level.price + tol["return"] if direction is Direction.UP else b.close <= level.price - tol["return"]
        for b in bars[start : end_index + 1]
    )
    return _record(
        "B.TERM.ACCEPTANCE.v0.1",
        bars,
        range(start - 20, end_index + 1),
        direction,
        TermStatus.CONFIRMED if passed else TermStatus.FAILED,
        start,
        end_index,
        {"anchor_atr": atr, "closes_beyond": closes_beyond, "return_min": tol["return"]},
        level,
        () if passed else ("ACCEPTANCE_THRESHOLDS_NOT_MET",),
    )


def reference_level_breach_and_response(
    bars: Sequence[Bar], anchor_index: int, level: ReferenceLevel, direction: Direction
) -> TermRecord:
    assert_compatible_bars(bars)
    if direction not in (Direction.UP, Direction.DOWN):
        raise ValueError("breach direction must be UP or DOWN")
    if anchor_index < 21 or anchor_index >= len(bars):
        raise ValueError("breach requires ATR history")
    _ensure_level_preexists(level, bars[anchor_index])
    atr = atr_before(bars, anchor_index)
    tol = tolerances(bars[anchor_index], atr)
    anchor = bars[anchor_index]
    breached = (
        anchor.high >= level.price + tol["breach"]
        if direction is Direction.UP
        else anchor.low <= level.price - tol["breach"]
    )
    last = min(anchor_index + 3, len(bars) - 1)
    if not breached:
        return _record(
            "B.TERM.REFERENCE_LEVEL_BREACH_RESPONSE.v0.1", bars, range(anchor_index - 20, anchor_index + 1),
            direction, TermStatus.FAILED, anchor_index, anchor_index,
            {"anchor_atr": atr, "breach_min": tol["breach"]}, level, ("BREACH_NOT_CONFIRMED",)
        )
    for response_index in range(anchor_index, last + 1):
        response = bars[response_index]
        returned = (
            response.close <= level.price - tol["return"]
            if direction is Direction.UP
            else response.close >= level.price + tol["return"]
        )
        if returned:
            opposite = Direction.DOWN if direction is Direction.UP else Direction.UP
            # Acceptance requires four bars, so check only when a complete candidate window exists.
            accepted = response_index >= anchor_index + 3 and _acceptance_passes(bars, response_index, level, opposite, atr)
            status = TermStatus.AMBIGUOUS if accepted else TermStatus.CONFIRMED
            return _record(
                "B.TERM.REFERENCE_LEVEL_BREACH_RESPONSE.v0.1", bars,
                range(anchor_index - 20, response_index + 1), direction, status, anchor_index, response_index,
                {"anchor_atr": atr, "breach_min": tol["breach"], "return_min": tol["return"]}, level,
                ("RETURN_AND_ACCEPTANCE_OVERLAP",) if accepted else (),
            )
    status = TermStatus.PENDING if last < anchor_index + 3 else TermStatus.FAILED
    reason = "RESPONSE_WINDOW_INCOMPLETE" if status is TermStatus.PENDING else "NO_RESPONSE_IN_WINDOW"
    return _record(
        "B.TERM.REFERENCE_LEVEL_BREACH_RESPONSE.v0.1", bars, range(anchor_index - 20, last + 1),
        direction, status, anchor_index, last, {"anchor_atr": atr, "breach_min": tol["breach"], "return_min": tol["return"]},
        level, (reason,),
    )


def reclaim(bars: Sequence[Bar], anchor_index: int, level: ReferenceLevel, direction: Direction) -> TermRecord:
    assert_compatible_bars(bars)
    if direction not in (Direction.UP, Direction.DOWN):
        raise ValueError("reclaim direction must be UP or DOWN")
    if anchor_index < 21 or anchor_index >= len(bars):
        raise ValueError("reclaim requires ATR history")
    _ensure_level_preexists(level, bars[anchor_index])
    atr = atr_before(bars, anchor_index)
    tol = tolerances(bars[anchor_index], atr)
    prior = bars[max(0, anchor_index - 8) : anchor_index]
    lost_side = any(
        b.close <= level.price - tol["touch"] if direction is Direction.UP else b.close >= level.price + tol["touch"]
        for b in prior
    )
    anchor_crossed = (
        bars[anchor_index].close >= level.price + tol["return"]
        if direction is Direction.UP
        else bars[anchor_index].close <= level.price - tol["return"]
    )
    if not lost_side or not anchor_crossed:
        reasons = tuple(code for condition, code in ((not lost_side, "NO_PRIOR_LOST_SIDE"), (not anchor_crossed, "ANCHOR_DID_NOT_RECLAIM")) if condition)
        return _record("B.TERM.RECLAIM.v0.1", bars, range(anchor_index - 20, anchor_index + 1), direction,
                       TermStatus.FAILED, anchor_index, anchor_index, {"anchor_atr": atr}, level, reasons)
    last = min(anchor_index + 2, len(bars) - 1)
    for end in range(anchor_index + 1, last + 1):
        qualifying = sum(
            b.close >= level.price + tol["return"] if direction is Direction.UP else b.close <= level.price - tol["return"]
            for b in bars[anchor_index : end + 1]
        )
        if qualifying >= 2 and (
            bars[end].close >= level.price + tol["return"] if direction is Direction.UP else bars[end].close <= level.price - tol["return"]
        ):
            return _record("B.TERM.RECLAIM.v0.1", bars, range(anchor_index - 20, end + 1), direction,
                           TermStatus.CONFIRMED, anchor_index, end,
                           {"anchor_atr": atr, "confirming_closes": qualifying}, level)
    status = TermStatus.PENDING if last < anchor_index + 2 else TermStatus.FAILED
    return _record("B.TERM.RECLAIM.v0.1", bars, range(anchor_index - 20, last + 1), direction, status,
                   anchor_index, last, {"anchor_atr": atr}, level,
                   ("RECLAIM_WINDOW_INCOMPLETE" if status is TermStatus.PENDING else "INSUFFICIENT_CONFIRMING_CLOSES",))


def rejection(bars: Sequence[Bar], anchor_index: int, level: ReferenceLevel, direction: Direction) -> TermRecord:
    assert_compatible_bars(bars)
    if direction not in (Direction.UP, Direction.DOWN):
        raise ValueError("rejection direction must be UP or DOWN")
    if anchor_index < 21 or anchor_index >= len(bars):
        raise ValueError("rejection requires ATR history")
    _ensure_level_preexists(level, bars[anchor_index])
    atr = atr_before(bars, anchor_index)
    tol = tolerances(bars[anchor_index], atr)
    interacted = (
        bars[anchor_index].high >= level.price - tol["touch"]
        if direction is Direction.DOWN
        else bars[anchor_index].low <= level.price + tol["touch"]
    )
    last = min(anchor_index + 3, len(bars) - 1)
    if not interacted:
        return _record("B.TERM.REJECTION.v0.1", bars, range(anchor_index - 20, anchor_index + 1), direction,
                       TermStatus.FAILED, anchor_index, anchor_index, {"anchor_atr": atr}, level, ("NO_LEVEL_INTERACTION",))
    for end in range(anchor_index, last + 1):
        departed = (
            bars[end].close <= level.price - tol["depart"]
            if direction is Direction.DOWN
            else bars[end].close >= level.price + tol["depart"]
        )
        if departed:
            accepted_direction = Direction.UP if direction is Direction.DOWN else Direction.DOWN
            accepted = end >= anchor_index + 3 and _acceptance_passes(bars, end, level, accepted_direction, atr)
            return _record("B.TERM.REJECTION.v0.1", bars, range(anchor_index - 20, end + 1), direction,
                           TermStatus.AMBIGUOUS if accepted else TermStatus.CONFIRMED, anchor_index, end,
                           {"anchor_atr": atr, "depart_min": tol["depart"]}, level,
                           ("DEPARTURE_AND_ACCEPTANCE_OVERLAP",) if accepted else ())
    status = TermStatus.PENDING if last < anchor_index + 3 else TermStatus.FAILED
    return _record("B.TERM.REJECTION.v0.1", bars, range(anchor_index - 20, last + 1), direction, status,
                   anchor_index, last, {"anchor_atr": atr, "depart_min": tol["depart"]}, level,
                   ("REJECTION_WINDOW_INCOMPLETE" if status is TermStatus.PENDING else "NO_DEPARTURE_IN_WINDOW",))


def transition(previous_states: Sequence[str], destination: str, trigger: TermRecord) -> TermRecord:
    if len(previous_states) < 2:
        raise ValueError("transition requires two prior resolved states")
    previous = previous_states[-1]
    stable = previous_states[-2] == previous
    if trigger.status is not TermStatus.CONFIRMED:
        status = TermStatus.FAILED
        reasons = ("TRIGGER_NOT_CONFIRMED",)
    elif not stable:
        status = TermStatus.FAILED
        reasons = ("PREVIOUS_STATE_NOT_STABLE",)
    elif previous == destination:
        status = TermStatus.FAILED
        reasons = ("STATE_UNCHANGED",)
    elif State.AMBIGUOUS.value in (previous, destination):
        status = TermStatus.AMBIGUOUS
        reasons = ("AMBIGUOUS_STATE",)
    else:
        status = TermStatus.CONFIRMED
        reasons = ()
    measurements = {"from_state": previous, "to_state": destination, "trigger_term_record_id": trigger.term_record_id}
    return TermRecord(
        term_id="B.TERM.TRANSITION.v0.1",
        instrument_id=trigger.instrument_id,
        timeframe=trigger.timeframe,
        direction=trigger.direction,
        anchor_time=trigger.anchor_time,
        first_valid_time=trigger.first_valid_time,
        status=status,
        input_bar_ids=trigger.input_bar_ids,
        source_release_id=trigger.source_release_id,
        measurements=measurements,
        reference_level_id=trigger.reference_level_id,
        reason_codes=reasons,
    )
