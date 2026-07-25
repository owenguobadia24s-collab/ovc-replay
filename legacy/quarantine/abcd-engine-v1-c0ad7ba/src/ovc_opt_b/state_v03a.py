from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from typing import Iterable, Mapping

from .state_v03 import AxisEvidence, LocationCondition


STATE_CONTRACT_VERSION_V03A = "B-STATE-0.3a"


@dataclass(frozen=True, slots=True)
class AcceptanceEventComponent:
    semantic_state: str
    direction: str
    support_level_ids: tuple[str, ...]
    trigger_term_record_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AcceptanceEventSnapshot:
    semantic_state: str
    components: tuple[AcceptanceEventComponent, ...]
    genuine_conflict: bool
    conflict_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AcceptanceRelationInventory:
    accepted_above_level_ids: tuple[str, ...]
    accepted_below_level_ids: tuple[str, ...]
    challenged_level_ids: tuple[str, ...]
    accepted_floor_level_ids: tuple[str, ...]
    accepted_floor_price: Decimal | None
    accepted_ceiling_level_ids: tuple[str, ...]
    accepted_ceiling_price: Decimal | None
    boundary_width: Decimal | None
    close_position_in_boundary: Decimal | None
    accepted_above_count: int
    accepted_below_count: int
    relation_count: int
    challenged_count: int
    refreshed_this_bar_count: int
    youngest_relation_age_bars: int | None
    median_relation_age_bars: float | None
    oldest_relation_age_bars: int | None
    relation_balance: int
    genuine_conflict: bool
    conflict_reasons: tuple[str, ...]


def resolve_acceptance_event(evidence: Iterable[AxisEvidence]) -> AcceptanceEventSnapshot:
    items = tuple(evidence)
    conflicts = {"CLASSIFIER_AMBIGUITY" for item in items if item.status == "AMBIGUOUS"}
    by_level: dict[str, set[str]] = {}
    for item in items:
        if item.status == "CONFIRMED" and item.level_id is not None:
            by_level.setdefault(item.level_id, set()).add(item.direction)
    if any(len(directions) > 1 for directions in by_level.values()):
        conflicts.add("SAME_LEVEL_ACCEPTED_BOTH_DIRECTIONS")

    grouped: dict[str, list[AxisEvidence]] = {}
    for item in items:
        if item.status == "CONFIRMED":
            grouped.setdefault(item.direction, []).append(item)
    components = tuple(
        AcceptanceEventComponent(
            semantic_state="ACCEPTED_ABOVE_EVENT" if direction == "UP" else "ACCEPTED_BELOW_EVENT",
            direction=direction,
            support_level_ids=tuple(sorted({item.level_id for item in grouped_items if item.level_id})),
            trigger_term_record_ids=tuple(sorted({item.term_record_id for item in grouped_items})),
        )
        for direction, grouped_items in sorted(grouped.items())
    )
    if conflicts:
        state = "CONFLICTING"
    elif not components:
        state = "NONE"
    elif len(components) == 1:
        state = components[0].semantic_state
    else:
        state = "COMPOUND_ACCEPTANCE_EVENT"
    return AcceptanceEventSnapshot(
        semantic_state=state,
        components=components,
        genuine_conflict=bool(conflicts),
        conflict_reasons=tuple(sorted(conflicts)),
    )


def resolve_acceptance_relation_inventory(
    conditions: Mapping[str, LocationCondition],
    *,
    level_prices: Mapping[str, Decimal],
    close: Decimal,
    relation_age_bars: Mapping[str, int],
    refreshed_level_ids: Iterable[str] = (),
    extra_conflict_reasons: Iterable[str] = (),
) -> AcceptanceRelationInventory:
    above = tuple(sorted(level_id for level_id, item in conditions.items() if item.direction == "UP"))
    below = tuple(sorted(level_id for level_id, item in conditions.items() if item.direction == "DOWN"))
    challenged = tuple(sorted(level_id for level_id, item in conditions.items() if item.challenge_count))
    conflicts = set(extra_conflict_reasons)
    if set(above).intersection(below):
        conflicts.add("SAME_LEVEL_ACCEPTED_BOTH_DIRECTIONS")

    floor_price = max((level_prices[level_id] for level_id in above), default=None)
    ceiling_price = min((level_prices[level_id] for level_id in below), default=None)
    floor_ids = tuple(
        sorted(level_id for level_id in above if floor_price is not None and level_prices[level_id] == floor_price)
    )
    ceiling_ids = tuple(
        sorted(level_id for level_id in below if ceiling_price is not None and level_prices[level_id] == ceiling_price)
    )
    width = None
    position = None
    if floor_price is not None and ceiling_price is not None:
        width = ceiling_price - floor_price
        if width <= 0:
            conflicts.add("INVERTED_ACCEPTED_RELATION_BOUNDS")
        else:
            position = (close - floor_price) / width

    ages = sorted(relation_age_bars[level_id] for level_id in conditions)
    refreshed = set(refreshed_level_ids)
    return AcceptanceRelationInventory(
        accepted_above_level_ids=above,
        accepted_below_level_ids=below,
        challenged_level_ids=challenged,
        accepted_floor_level_ids=floor_ids,
        accepted_floor_price=floor_price,
        accepted_ceiling_level_ids=ceiling_ids,
        accepted_ceiling_price=ceiling_price,
        boundary_width=width,
        close_position_in_boundary=position,
        accepted_above_count=len(above),
        accepted_below_count=len(below),
        relation_count=len(conditions),
        challenged_count=len(challenged),
        refreshed_this_bar_count=sum(1 for level_id in refreshed if level_id in conditions),
        youngest_relation_age_bars=ages[0] if ages else None,
        median_relation_age_bars=float(median(ages)) if ages else None,
        oldest_relation_age_bars=ages[-1] if ages else None,
        relation_balance=len(above) - len(below),
        genuine_conflict=bool(conflicts),
        conflict_reasons=tuple(sorted(conflicts)),
    )

