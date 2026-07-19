from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Mapping


STATE_CONTRACT_VERSION_V03 = "B-STATE-0.3"


@dataclass(frozen=True, slots=True)
class AxisEvidence:
    axis: str
    term_family: str
    semantic_state: str
    direction: str
    level_id: str | None
    term_record_id: str
    status: str
    return_min: Decimal | None = None


@dataclass(slots=True)
class LocationCondition:
    level_id: str
    direction: str
    state_since: datetime
    refreshed_at: datetime
    trigger_term_record_ids: tuple[str, ...]
    return_min: Decimal
    challenge_count: int = 0
    stale_after_gap: bool = False


@dataclass(frozen=True, slots=True)
class LocationSnapshot:
    semantic_state: str
    above_level_ids: tuple[str, ...]
    below_level_ids: tuple[str, ...]
    challenged_level_ids: tuple[str, ...]
    trigger_term_record_ids: tuple[str, ...]
    genuine_conflict: bool
    conflict_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InteractionComponent:
    semantic_state: str
    direction: str
    support_level_ids: tuple[str, ...]
    trigger_term_record_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InteractionSnapshot:
    semantic_state: str
    components: tuple[InteractionComponent, ...]
    genuine_conflict: bool
    conflict_reasons: tuple[str, ...]


def acceptance_maintenance_passes(
    condition: LocationCondition,
    *,
    close: Decimal,
    level_price: Decimal,
) -> bool:
    if condition.direction == "UP":
        return close >= level_price + condition.return_min
    if condition.direction == "DOWN":
        return close <= level_price - condition.return_min
    raise ValueError(f"unsupported acceptance direction: {condition.direction}")


def resolve_location_snapshot(
    conditions: Mapping[str, LocationCondition],
    *,
    level_prices: Mapping[str, Decimal],
    extra_conflict_reasons: Iterable[str] = (),
) -> LocationSnapshot:
    above = tuple(sorted(level_id for level_id, item in conditions.items() if item.direction == "UP"))
    below = tuple(sorted(level_id for level_id, item in conditions.items() if item.direction == "DOWN"))
    challenged = tuple(sorted(level_id for level_id, item in conditions.items() if item.challenge_count))
    trigger_ids = tuple(sorted({
        record_id
        for item in conditions.values()
        for record_id in item.trigger_term_record_ids
    }))
    conflicts = set(extra_conflict_reasons)
    duplicated = set(above).intersection(below)
    if duplicated:
        conflicts.add("SAME_LEVEL_ACCEPTED_BOTH_DIRECTIONS")
    if above and below:
        highest_above = max(level_prices[level_id] for level_id in above)
        lowest_below = min(level_prices[level_id] for level_id in below)
        if highest_above >= lowest_below:
            conflicts.add("INVERTED_ACCEPTED_LOCATION_BOUNDS")
    if conflicts:
        state = "CONFLICTING"
    elif above and below:
        state = "ACCEPTED_CORRIDOR"
    elif above:
        state = "ACCEPTED_ABOVE"
    elif below:
        state = "ACCEPTED_BELOW"
    else:
        state = "NEUTRAL"
    return LocationSnapshot(
        semantic_state=state,
        above_level_ids=above,
        below_level_ids=below,
        challenged_level_ids=challenged,
        trigger_term_record_ids=trigger_ids,
        genuine_conflict=bool(conflicts),
        conflict_reasons=tuple(sorted(conflicts)),
    )


def resolve_interaction_snapshot(evidence: Iterable[AxisEvidence]) -> InteractionSnapshot:
    items = tuple(evidence)
    conflicts: set[str] = set()
    for item in items:
        if item.status == "AMBIGUOUS":
            conflicts.add("CLASSIFIER_AMBIGUITY")
    by_identity: dict[tuple[str, str | None], set[str]] = {}
    for item in items:
        if item.status != "CONFIRMED":
            continue
        by_identity.setdefault((item.term_family, item.level_id), set()).add(item.direction)
    if any(len(directions) > 1 for directions in by_identity.values()):
        conflicts.add("SAME_INTERACTION_AND_LEVEL_OPPOSITE_DIRECTIONS")

    grouped: dict[tuple[str, str], list[AxisEvidence]] = {}
    for item in items:
        if item.status != "CONFIRMED":
            continue
        grouped.setdefault((item.semantic_state, item.direction), []).append(item)
    components = tuple(
        InteractionComponent(
            semantic_state=semantic_state,
            direction=direction,
            support_level_ids=tuple(sorted({item.level_id for item in grouped_items if item.level_id})),
            trigger_term_record_ids=tuple(sorted({item.term_record_id for item in grouped_items})),
        )
        for (semantic_state, direction), grouped_items in sorted(grouped.items())
    )
    if conflicts:
        state = "CONFLICTING"
    elif not components:
        state = "NONE"
    elif len(components) == 1:
        state = components[0].semantic_state
    else:
        state = "COMPOUND"
    return InteractionSnapshot(
        semantic_state=state,
        components=components,
        genuine_conflict=bool(conflicts),
        conflict_reasons=tuple(sorted(conflicts)),
    )


def displacement_trigger_state(evidence: Iterable[AxisEvidence]) -> tuple[str | None, tuple[str, ...]]:
    items = tuple(evidence)
    conflicts = {"CLASSIFIER_AMBIGUITY" for item in items if item.status == "AMBIGUOUS"}
    directions = {item.direction for item in items if item.status == "CONFIRMED"}
    if len(directions) > 1:
        conflicts.add("OPPOSITE_DISPLACEMENTS_ON_ONE_BAR")
    if conflicts:
        return "CONFLICTING", tuple(sorted(conflicts))
    if not directions:
        return None, ()
    direction = next(iter(directions))
    return f"DISPLACING_{direction}", ()

