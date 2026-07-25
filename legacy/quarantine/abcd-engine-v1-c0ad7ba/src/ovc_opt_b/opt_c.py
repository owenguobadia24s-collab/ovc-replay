from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from typing import Mapping
from decimal import Decimal


OPT_C_CONTRACT_VERSION = "OPT-C-OUTCOME-0.1"
OPT_C_HORIZONS_HOURS = (1, 2, 4, 8, 12, 24, 48)


@dataclass(frozen=True, slots=True)
class PathCoverageAssessment:
    coverage_status: str
    censor_reasons: tuple[str, ...]
    endpoint_time: datetime
    expected_bar_count: int
    available_bar_count: int
    missing_interval_count: int
    missing_run_count: int
    max_missing_run_bars: int
    first_missing_open_time: datetime | None
    last_missing_open_time: datetime | None
    missing_open_times_hash: str | None
    available_bar_ids_hash: str
    path_bar_ids_hash: str | None


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def expected_15m_open_times(anchor_time: datetime, horizon_hours: int) -> tuple[datetime, ...]:
    if horizon_hours not in OPT_C_HORIZONS_HOURS:
        raise ValueError("horizon is not ratified by OPT-C-OUTCOME-0.1")
    return tuple(anchor_time + timedelta(minutes=15 * index) for index in range(horizon_hours * 4))


def assess_15m_path_coverage(
    anchor_time: datetime,
    horizon_hours: int,
    *,
    bar_ids_by_open_time: Mapping[datetime, str],
    source_last_close_time: datetime,
) -> PathCoverageAssessment:
    expected = expected_15m_open_times(anchor_time, horizon_hours)
    endpoint = anchor_time + timedelta(hours=horizon_hours)
    missing_indices = [index for index, at in enumerate(expected) if at not in bar_ids_by_open_time]
    missing_times = [expected[index] for index in missing_indices]
    available_ids = [bar_ids_by_open_time[at] for at in expected if at in bar_ids_by_open_time]
    runs = []
    for index in missing_indices:
        if not runs or index != runs[-1][-1] + 1:
            runs.append([index])
        else:
            runs[-1].append(index)

    reasons = set()
    if endpoint > source_last_close_time:
        reasons.add("SOURCE_END_TRUNCATION")
    if missing_indices:
        if 0 in missing_indices:
            reasons.add("ANCHOR_START_INTERVAL_MISSING")
        if len(expected) - 1 in missing_indices:
            reasons.add("ENDPOINT_INTERVAL_MISSING")
        if any(0 < index < len(expected) - 1 for index in missing_indices):
            reasons.add("INTERNAL_INTERVALS_MISSING")
    status = "COMPLETE" if not missing_indices and endpoint <= source_last_close_time else "CENSORED"
    path_ids = [bar_ids_by_open_time[at] for at in expected] if status == "COMPLETE" else None
    return PathCoverageAssessment(
        coverage_status=status,
        censor_reasons=tuple(sorted(reasons)),
        endpoint_time=endpoint,
        expected_bar_count=len(expected),
        available_bar_count=len(available_ids),
        missing_interval_count=len(missing_indices),
        missing_run_count=len(runs),
        max_missing_run_bars=max((len(run) for run in runs), default=0),
        first_missing_open_time=missing_times[0] if missing_times else None,
        last_missing_open_time=missing_times[-1] if missing_times else None,
        missing_open_times_hash=_canonical_hash([at.isoformat() for at in missing_times]) if missing_times else None,
        available_bar_ids_hash=_canonical_hash(available_ids),
        path_bar_ids_hash=_canonical_hash(path_ids) if path_ids is not None else None,
    )


def _elapsed_minutes(anchor_time: datetime, at: datetime) -> int:
    return int((at - anchor_time).total_seconds() // 60)


def _frontier_test(
    frontier_type: str,
    price: Decimal,
    *,
    anchor_time: datetime,
    path_bars: tuple[object, ...],
) -> dict[str, object]:
    touches = [bar for bar in path_bars if bar.low <= price <= bar.high]
    if frontier_type == "FLOOR":
        invalidations = [bar for bar in path_bars if bar.close < price]
        held = path_bars[-1].close >= price
    else:
        invalidations = [bar for bar in path_bars if bar.close > price]
        held = path_bars[-1].close <= price
    endpoint = path_bars[-1].close
    endpoint_relation = "ABOVE" if endpoint > price else "BELOW" if endpoint < price else "AT"
    return {
        "frontier_type": frontier_type,
        "frontier_price": str(price),
        "retested": bool(touches),
        "first_retest_elapsed_minutes": _elapsed_minutes(anchor_time, touches[0].close_time) if touches else None,
        "lost_on_close": bool(invalidations),
        "first_loss_elapsed_minutes": (
            _elapsed_minutes(anchor_time, invalidations[0].close_time) if invalidations else None
        ),
        "held_at_endpoint": held,
        "endpoint_relation": endpoint_relation,
    }


def measure_neutral_path(
    *,
    anchor_time: datetime,
    anchor_price: Decimal,
    event_direction_value: str,
    event_bar_high: Decimal,
    event_bar_low: Decimal,
    path_bars: Iterable[object],
    frontier_summary: Mapping[str, object],
    pip_size: Decimal = Decimal("0.0001"),
) -> dict[str, object]:
    bars = tuple(path_bars)
    if not bars:
        raise ValueError("neutral path measurement requires at least one bar")
    max_high = max(bar.high for bar in bars)
    min_low = min(bar.low for bar in bars)
    max_high_index = next(index for index, bar in enumerate(bars) if bar.high == max_high)
    min_low_index = next(index for index, bar in enumerate(bars) if bar.low == min_low)
    max_high_bar = bars[max_high_index]
    min_low_bar = bars[min_low_index]
    endpoint = bars[-1].close
    raw_return = endpoint - anchor_price
    upward = max(Decimal("0"), max_high - anchor_price)
    downward = max(Decimal("0"), anchor_price - min_low)
    forward_range = max_high - min_low
    position = (endpoint - min_low) / forward_range if forward_range else None
    if max_high_index < min_low_index:
        first_extreme = "UP_FIRST"
    elif min_low_index < max_high_index:
        first_extreme = "DOWN_FIRST"
    else:
        first_extreme = "SAME_15M_BAR"

    if event_direction_value == "UP":
        normalized_return = raw_return
        favorable = upward
        adverse = downward
        continued = max_high > event_bar_high
        continuation_bar = next((bar for bar in bars if bar.high > event_bar_high), None)
        desired_primary_frontier = "FLOOR"
    elif event_direction_value == "DOWN":
        normalized_return = -raw_return
        favorable = downward
        adverse = upward
        continued = min_low < event_bar_low
        continuation_bar = next((bar for bar in bars if bar.low < event_bar_low), None)
        desired_primary_frontier = "CEILING"
    else:
        normalized_return = favorable = adverse = None
        continued = None
        continuation_bar = None
        desired_primary_frontier = None

    frontier_tests = []
    floor = frontier_summary.get("accepted_floor_price")
    ceiling = frontier_summary.get("accepted_ceiling_price")
    if floor is not None:
        frontier_tests.append(
            _frontier_test("FLOOR", Decimal(str(floor)), anchor_time=anchor_time, path_bars=bars)
        )
    if ceiling is not None:
        frontier_tests.append(
            _frontier_test("CEILING", Decimal(str(ceiling)), anchor_time=anchor_time, path_bars=bars)
        )
    primary = next(
        (item for item in frontier_tests if item["frontier_type"] == desired_primary_frontier),
        None,
    )
    return {
        "endpoint_price": str(endpoint),
        "raw_return_price": str(raw_return),
        "raw_return_pips": str(raw_return / pip_size),
        "maximum_upward_excursion_price": str(upward),
        "maximum_upward_excursion_pips": str(upward / pip_size),
        "maximum_downward_excursion_price": str(downward),
        "maximum_downward_excursion_pips": str(downward / pip_size),
        "forward_maximum_price": str(max_high),
        "forward_minimum_price": str(min_low),
        "forward_range_price": str(forward_range),
        "endpoint_close_position_in_forward_range": str(position) if position is not None else None,
        "maximum_time_elapsed_minutes": _elapsed_minutes(anchor_time, max_high_bar.close_time),
        "minimum_time_elapsed_minutes": _elapsed_minutes(anchor_time, min_low_bar.close_time),
        "first_extreme": first_extreme,
        "direction_normalization_status": (
            "DIRECTIONAL" if event_direction_value in ("UP", "DOWN") else "NOT_DIRECTIONAL"
        ),
        "direction_normalized_endpoint_return_pips": (
            str(normalized_return / pip_size) if normalized_return is not None else None
        ),
        "direction_normalized_favorable_excursion_pips": (
            str(favorable / pip_size) if favorable is not None else None
        ),
        "direction_normalized_adverse_excursion_pips": (
            str(adverse / pip_size) if adverse is not None else None
        ),
        "continued_beyond_event_extreme": continued,
        "first_continuation_elapsed_minutes": (
            _elapsed_minutes(anchor_time, continuation_bar.close_time) if continuation_bar else None
        ),
        "frontier_tests": frontier_tests,
        "primary_frontier_type": primary["frontier_type"] if primary else None,
        "primary_frontier_retested": primary["retested"] if primary else None,
        "primary_frontier_lost_on_close": primary["lost_on_close"] if primary else None,
        "primary_frontier_held_at_endpoint": primary["held_at_endpoint"] if primary else None,
        "directional_reversal_through_frontier": primary["lost_on_close"] if primary else None,
    }


def event_direction(components: Iterable[Mapping[str, object]]) -> str:
    directions = {
        str(component["direction"])
        for component in components
        if component.get("direction") in ("UP", "DOWN")
    }
    if not directions:
        return "NONE"
    if len(directions) == 1:
        return next(iter(directions))
    return "MIXED"


def persistent_trigger_kind(previous_state: str | None, current_state: str, inactive_state: str) -> str:
    if current_state == inactive_state:
        return "EXIT"
    if previous_state in (None, inactive_state):
        return "ONSET"
    if previous_state == current_state:
        return "REFRESH"
    return "DIRECTION_CHANGE"


def context_quality(anchor_time: datetime, context_time: datetime | None, *, maximum_age_minutes: int) -> str:
    if context_time is None:
        return "UNAVAILABLE"
    age_minutes = int((anchor_time - context_time).total_seconds() // 60)
    if age_minutes < 0:
        raise ValueError("cross-clock context cannot come from the future")
    return "CURRENT" if age_minutes < maximum_age_minutes else "STALE_AFTER_GAP"
