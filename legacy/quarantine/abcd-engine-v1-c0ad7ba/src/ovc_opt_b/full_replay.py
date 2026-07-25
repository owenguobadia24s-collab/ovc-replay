from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Iterable, Sequence

from .classifiers import acceptance, reclaim, reference_level_breach_and_response, rejection, transition
from .levels import LevelRegistry
from .models import Bar, Direction, ReferenceLevel, TermRecord, TermStatus
from .primitives import atr_before, tolerances
from .replay import contiguous_segments, replay_unlevelled_terms


@dataclass(frozen=True, slots=True)
class ResolvedState:
    instrument_id: str
    timeframe: str
    close_time: datetime
    state: str
    trigger_term_record_ids: tuple[str, ...]
    selected_term_record_id: str | None
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CompleteReplay:
    term_records: tuple[TermRecord, ...]
    transition_records: tuple[TermRecord, ...]
    state_stream: tuple[ResolvedState, ...]
    coverage: dict[str, object]


class _PriceIndex:
    def __init__(self, levels: Iterable[ReferenceLevel]) -> None:
        self.levels = tuple(sorted(levels, key=lambda level: (level.price, level.level_id)))
        self.prices = tuple(level.price for level in self.levels)
        self.by_valid = tuple(sorted(self.levels, key=lambda level: (level.first_valid_time, level.level_id)))
        self.valid_times = tuple(level.first_valid_time for level in self.by_valid)

    def eligible_count(self, at: datetime) -> int:
        return bisect_right(self.valid_times, at)

    def leq(self, price: Decimal, at: datetime, *, above: Decimal | None = None) -> tuple[ReferenceLevel, ...]:
        start = 0 if above is None else bisect_right(self.prices, above)
        end = bisect_right(self.prices, price)
        return tuple(level for level in self.levels[start:end] if level.first_valid_time <= at)

    def geq(self, price: Decimal, at: datetime, *, below: Decimal | None = None) -> tuple[ReferenceLevel, ...]:
        start = bisect_left(self.prices, price)
        end = len(self.levels) if below is None else bisect_left(self.prices, below)
        return tuple(level for level in self.levels[start:end] if level.first_valid_time <= at)

    def interval(self, low: Decimal, high: Decimal, at: datetime) -> tuple[ReferenceLevel, ...]:
        if low > high:
            return ()
        start = bisect_left(self.prices, low)
        end = bisect_right(self.prices, high)
        return tuple(level for level in self.levels[start:end] if level.first_valid_time <= at)

    def newly_valid(self, after: datetime | None, at: datetime) -> tuple[ReferenceLevel, ...]:
        start = 0 if after is None else bisect_right(self.valid_times, after)
        end = bisect_right(self.valid_times, at)
        return self.by_valid[start:end]


def _term_to_state(record: TermRecord) -> tuple[int, str] | None:
    if record.status is TermStatus.AMBIGUOUS:
        return (1, "AMBIGUOUS")
    if record.status is not TermStatus.CONFIRMED:
        return None
    level_id = record.reference_level_id
    if record.term_id == "B.TERM.ACCEPTANCE.v0.1":
        return (2, f"ACCEPTED_{'ABOVE' if record.direction is Direction.UP else 'BELOW'}:{level_id}")
    if record.term_id == "B.TERM.RECLAIM.v0.1":
        return (3, f"RECLAIMED_{'ABOVE' if record.direction is Direction.UP else 'BELOW'}:{level_id}")
    if record.term_id == "B.TERM.REJECTION.v0.1":
        return (4, f"REJECTED_{record.direction.value}:{level_id}")
    if record.term_id == "B.TERM.DISPLACEMENT.v0.1":
        return (5, f"DISPLACING_{record.direction.value}")
    if record.term_id == "B.TERM.COMPRESSION.v0.1":
        return (6, "COMPRESSED")
    return None


def _resolve_states(bars: Sequence[Bar], records: Sequence[TermRecord]) -> tuple[tuple[ResolvedState, ...], tuple[TermRecord, ...]]:
    by_time: dict[datetime, list[TermRecord]] = defaultdict(list)
    by_id = {record.term_record_id: record for record in records}
    for record in records:
        if _term_to_state(record) is not None:
            by_time[record.first_valid_time].append(record)
    states: list[ResolvedState] = []
    transitions: list[TermRecord] = []
    seen_transition_ids: set[str] = set()
    for segment in contiguous_segments(bars):
        segment_states: list[ResolvedState] = []
        for bar in segment:
            candidates = [(record, _term_to_state(record)) for record in by_time.get(bar.close_time, [])]
            candidates = [(record, state) for record, state in candidates if state is not None]
            if not candidates:
                resolved = ResolvedState(bar.instrument_id, bar.timeframe, bar.close_time, "NEUTRAL", (), None)
            else:
                best_rank = min(state[0] for _, state in candidates)
                best = [(record, state[1]) for record, state in candidates if state[0] == best_rank]
                unique_states = {state for _, state in best}
                trigger_ids = tuple(sorted(record.term_record_id for record, _ in candidates))
                if len(unique_states) != 1 or "AMBIGUOUS" in unique_states:
                    resolved = ResolvedState(
                        bar.instrument_id,
                        bar.timeframe,
                        bar.close_time,
                        "AMBIGUOUS",
                        trigger_ids,
                        None,
                        ("MULTIPLE_TOP_PRECEDENCE_STATES",) if len(unique_states) != 1 else ("AMBIGUOUS_TERM",),
                    )
                else:
                    selected_record, selected_state = sorted(best, key=lambda item: item[0].term_record_id)[0]
                    resolved = ResolvedState(
                        bar.instrument_id,
                        bar.timeframe,
                        bar.close_time,
                        selected_state,
                        trigger_ids,
                        selected_record.term_record_id,
                    )
            if (
                len(segment_states) >= 2
                and segment_states[-2].state == segment_states[-1].state
                and segment_states[-1].state != resolved.state
                and resolved.state not in {"NEUTRAL", "AMBIGUOUS"}
                and resolved.selected_term_record_id is not None
            ):
                trigger = by_id[resolved.selected_term_record_id]
                record = transition(
                    [segment_states[-2].state, segment_states[-1].state],
                    resolved.state,
                    trigger,
                )
                if record.status is TermStatus.CONFIRMED and record.term_record_id not in seen_transition_ids:
                    transitions.append(record)
                    seen_transition_ids.add(record.term_record_id)
            segment_states.append(resolved)
            states.append(resolved)
    return tuple(states), tuple(transitions)


def replay_complete_terms(bars: Iterable[Bar], registry: LevelRegistry) -> CompleteReplay:
    source = tuple(bars)
    if not source:
        raise ValueError("complete replay requires bars")
    if registry.instrument_id != source[0].instrument_id or registry.timeframe != source[0].timeframe:
        raise ValueError("registry and bars must share instrument and timeframe")
    if registry.source_release_id != source[0].source_release_id:
        raise ValueError("registry and bars must share source release")

    all_index = _PriceIndex(registry.levels)
    high_index = _PriceIndex(level for level in registry.levels if level.level_type.endswith("HIGH"))
    low_index = _PriceIndex(level for level in registry.levels if level.level_type.endswith("LOW"))

    records: list[TermRecord] = list(replay_unlevelled_terms(source).records)
    seen_ids = {record.term_record_id for record in records}
    coverage_pairs = Counter()
    episode_starts = Counter()
    level_ids_by_term: dict[str, set[str]] = defaultdict(set)

    def add(record: TermRecord) -> None:
        if record.term_record_id in seen_ids:
            return
        records.append(record)
        seen_ids.add(record.term_record_id)
        episode_starts[f"{record.term_id}:{record.direction.value}"] += 1
        if record.reference_level_id:
            level_ids_by_term[record.term_id].add(record.reference_level_id)

    for segment in contiguous_segments(source):
        if len(segment) < 22:
            continue
        prev_thresholds: dict[str, Decimal | tuple[Decimal, Decimal] | None] = {
            "sweep_up": None,
            "sweep_down": None,
            "reject_down": None,
            "reject_up": None,
            "reclaim_up": None,
            "reclaim_down": None,
            "accept_up": None,
            "accept_down": None,
        }
        prev_anchor_times: dict[str, datetime | None] = {key: None for key in prev_thresholds}

        for index in range(21, len(segment)):
            bar = segment[index]
            anchor_time = bar.open_time
            atr = atr_before(segment, index)
            tol = tolerances(bar, atr)
            eligible_all = all_index.eligible_count(anchor_time)
            eligible_high = high_index.eligible_count(anchor_time)
            eligible_low = low_index.eligible_count(anchor_time)
            coverage_pairs["SWEEP_UP"] += eligible_high
            coverage_pairs["SWEEP_DOWN"] += eligible_low
            coverage_pairs["REJECTION_DOWN"] += eligible_high
            coverage_pairs["REJECTION_UP"] += eligible_low
            coverage_pairs["RECLAIM_UP"] += eligible_all
            coverage_pairs["RECLAIM_DOWN"] += eligible_all

            # Breach episodes begin only when the breach predicate changes false -> true,
            # or when a newly valid level already satisfies it.
            sweep_up_limit = bar.high - tol["breach"]
            prior = prev_thresholds["sweep_up"]
            candidates = {
                level.level_id: level
                for level in high_index.leq(
                    sweep_up_limit,
                    anchor_time,
                    above=prior if isinstance(prior, Decimal) and sweep_up_limit > prior else sweep_up_limit,
                )
            } if prior is not None and sweep_up_limit > prior else {}
            if prior is None:
                candidates = {level.level_id: level for level in high_index.leq(sweep_up_limit, anchor_time)}
            for level in high_index.newly_valid(prev_anchor_times["sweep_up"], anchor_time):
                if level.price <= sweep_up_limit:
                    candidates[level.level_id] = level
            for level in candidates.values():
                add(reference_level_breach_and_response(segment, index, level, Direction.UP))
            prev_thresholds["sweep_up"] = sweep_up_limit
            prev_anchor_times["sweep_up"] = anchor_time

            sweep_down_limit = bar.low + tol["breach"]
            prior = prev_thresholds["sweep_down"]
            candidates = {
                level.level_id: level
                for level in low_index.geq(
                    sweep_down_limit,
                    anchor_time,
                    below=prior if isinstance(prior, Decimal) and sweep_down_limit < prior else sweep_down_limit,
                )
            } if prior is not None and sweep_down_limit < prior else {}
            if prior is None:
                candidates = {level.level_id: level for level in low_index.geq(sweep_down_limit, anchor_time)}
            for level in low_index.newly_valid(prev_anchor_times["sweep_down"], anchor_time):
                if level.price >= sweep_down_limit:
                    candidates[level.level_id] = level
            for level in candidates.values():
                add(reference_level_breach_and_response(segment, index, level, Direction.DOWN))
            prev_thresholds["sweep_down"] = sweep_down_limit
            prev_anchor_times["sweep_down"] = anchor_time

            # Rejection interaction episodes use the same threshold-entry mechanism.
            rejection_down_limit = bar.high + tol["touch"]
            prior = prev_thresholds["reject_down"]
            candidates = {
                level.level_id: level
                for level in high_index.leq(
                    rejection_down_limit,
                    anchor_time,
                    above=prior if isinstance(prior, Decimal) and rejection_down_limit > prior else rejection_down_limit,
                )
            } if prior is not None and rejection_down_limit > prior else {}
            if prior is None:
                candidates = {level.level_id: level for level in high_index.leq(rejection_down_limit, anchor_time)}
            for level in high_index.newly_valid(prev_anchor_times["reject_down"], anchor_time):
                if level.price <= rejection_down_limit:
                    candidates[level.level_id] = level
            for level in candidates.values():
                add(rejection(segment, index, level, Direction.DOWN))
            prev_thresholds["reject_down"] = rejection_down_limit
            prev_anchor_times["reject_down"] = anchor_time

            rejection_up_limit = bar.low - tol["touch"]
            prior = prev_thresholds["reject_up"]
            candidates = {
                level.level_id: level
                for level in low_index.geq(
                    rejection_up_limit,
                    anchor_time,
                    below=prior if isinstance(prior, Decimal) and rejection_up_limit < prior else rejection_up_limit,
                )
            } if prior is not None and rejection_up_limit < prior else {}
            if prior is None:
                candidates = {level.level_id: level for level in low_index.geq(rejection_up_limit, anchor_time)}
            for level in low_index.newly_valid(prev_anchor_times["reject_up"], anchor_time):
                if level.price >= rejection_up_limit:
                    candidates[level.level_id] = level
            for level in candidates.values():
                add(rejection(segment, index, level, Direction.UP))
            prev_thresholds["reject_up"] = rejection_up_limit
            prev_anchor_times["reject_up"] = anchor_time

            # Reclaim episode predicates form a bounded interval in level-price space.
            prior_closes = [candidate.close for candidate in segment[index - 8 : index]]
            reclaim_intervals = {
                "reclaim_up": (min(prior_closes) + tol["touch"], bar.close - tol["return"], Direction.UP),
                "reclaim_down": (bar.close + tol["return"], max(prior_closes) - tol["touch"], Direction.DOWN),
            }
            for key, (low, high, direction) in reclaim_intervals.items():
                prior_interval = prev_thresholds[key]
                current = all_index.interval(low, high, anchor_time)
                candidates = {
                    level.level_id: level
                    for level in current
                    if not isinstance(prior_interval, tuple)
                    or not (prior_interval[0] <= level.price <= prior_interval[1])
                }
                for level in all_index.newly_valid(prev_anchor_times[key], anchor_time):
                    if low <= level.price <= high:
                        candidates[level.level_id] = level
                for level in candidates.values():
                    add(reclaim(segment, index, level, direction))
                prev_thresholds[key] = (low, high)
                prev_anchor_times[key] = anchor_time

            if index >= 24:
                window_start = index - 3
                window_anchor = segment[window_start]
                anchor_atr = atr_before(segment, window_start)
                window_tol = tolerances(window_anchor, anchor_atr)
                window = segment[window_start : index + 1]
                closes = sorted(candidate.close for candidate in window)
                accept_up_limit = min(
                    closes[1] - window_tol["return"],
                    window[-1].close - window_tol["return"],
                    min(candidate.low for candidate in window) + Decimal("0.25") * anchor_atr,
                )
                accept_down_limit = max(
                    closes[2] + window_tol["return"],
                    window[-1].close + window_tol["return"],
                    max(candidate.high for candidate in window) - Decimal("0.25") * anchor_atr,
                )
                eligible_at_window = all_index.eligible_count(window_anchor.open_time)
                coverage_pairs["ACCEPTANCE_UP"] += eligible_at_window
                coverage_pairs["ACCEPTANCE_DOWN"] += eligible_at_window

                prior = prev_thresholds["accept_up"]
                candidates = {
                    level.level_id: level
                    for level in all_index.leq(
                        accept_up_limit,
                        window_anchor.open_time,
                        above=prior if isinstance(prior, Decimal) and accept_up_limit > prior else accept_up_limit,
                    )
                } if prior is not None and accept_up_limit > prior else {}
                if prior is None:
                    candidates = {level.level_id: level for level in all_index.leq(accept_up_limit, window_anchor.open_time)}
                for level in all_index.newly_valid(prev_anchor_times["accept_up"], window_anchor.open_time):
                    if level.price <= accept_up_limit:
                        candidates[level.level_id] = level
                for level in candidates.values():
                    record = acceptance(segment, index, level, Direction.UP)
                    if record.status is not TermStatus.CONFIRMED:
                        raise AssertionError("acceptance threshold index produced a non-confirmed record")
                    add(record)
                prev_thresholds["accept_up"] = accept_up_limit
                prev_anchor_times["accept_up"] = window_anchor.open_time

                prior = prev_thresholds["accept_down"]
                candidates = {
                    level.level_id: level
                    for level in all_index.geq(
                        accept_down_limit,
                        window_anchor.open_time,
                        below=prior if isinstance(prior, Decimal) and accept_down_limit < prior else accept_down_limit,
                    )
                } if prior is not None and accept_down_limit < prior else {}
                if prior is None:
                    candidates = {level.level_id: level for level in all_index.geq(accept_down_limit, window_anchor.open_time)}
                for level in all_index.newly_valid(prev_anchor_times["accept_down"], window_anchor.open_time):
                    if level.price >= accept_down_limit:
                        candidates[level.level_id] = level
                for level in candidates.values():
                    record = acceptance(segment, index, level, Direction.DOWN)
                    if record.status is not TermStatus.CONFIRMED:
                        raise AssertionError("acceptance threshold index produced a non-confirmed record")
                    add(record)
                prev_thresholds["accept_down"] = accept_down_limit
                prev_anchor_times["accept_down"] = window_anchor.open_time

    records.sort(key=lambda record: (record.first_valid_time, record.term_id, record.term_record_id))
    states, transitions = _resolve_states(source, records)
    status_counts = Counter(f"{record.term_id}:{record.status.value}" for record in records)
    reason_counts = Counter(reason for record in records for reason in record.reason_codes)
    coverage = {
        "source_bars": len(source),
        "registry_levels": len(registry.levels),
        "eligible_directional_level_bar_evaluations": sum(coverage_pairs.values()),
        "pair_evaluations": dict(sorted(coverage_pairs.items())),
        "materialized_episode_records": len(records),
        "episode_starts": dict(sorted(episode_starts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "unique_levels_with_records_by_term": {
            term: len(ids) for term, ids in sorted(level_ids_by_term.items())
        },
        "state_counts": dict(
            sorted(Counter(state.state.split(":", 1)[0] for state in states).items())
        ),
        "transition_records": len(transitions),
        "materialization_policy": "All eligible pairs counted; records emitted on deterministic episode/condition entry and resolution.",
        "neutral_transition_policy": "Deferred because B-LANG-0.1 requires a confirmed destination trigger but defines no NEUTRAL-producing term.",
    }
    return CompleteReplay(tuple(records), transitions, states, coverage)


def term_record_to_dict(record: TermRecord) -> dict[str, object]:
    return {
        "term_record_id": record.term_record_id,
        "term_id": record.term_id,
        "term_version": record.term_version,
        "instrument_id": record.instrument_id,
        "timeframe": record.timeframe,
        "direction": record.direction.value,
        "anchor_time": record.anchor_time.astimezone(timezone.utc).isoformat(),
        "first_valid_time": record.first_valid_time.astimezone(timezone.utc).isoformat(),
        "status": record.status.value,
        "measurements": dict(record.measurements),
        "reference_level_id": record.reference_level_id,
        "input_bar_ids": list(record.input_bar_ids),
        "source_release_id": record.source_release_id,
        "parameter_set_id": record.parameter_set_id,
        "reason_codes": list(record.reason_codes),
    }


def state_to_dict(state: ResolvedState) -> dict[str, object]:
    return {
        "instrument_id": state.instrument_id,
        "timeframe": state.timeframe,
        "close_time": state.close_time.astimezone(timezone.utc).isoformat(),
        "state": state.state,
        "trigger_term_record_ids": list(state.trigger_term_record_ids),
        "selected_term_record_id": state.selected_term_record_id,
        "reason_codes": list(state.reason_codes),
    }
