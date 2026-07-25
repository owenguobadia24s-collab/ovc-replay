from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .state_v03a import AcceptanceEventComponent, AcceptanceEventSnapshot


STATE_CONTRACT_VERSION_V03B_REVIEW = "B-STATE-0.3b-REVIEW"
STATE_CONTRACT_VERSION_V03B = "B-STATE-0.3b"


@dataclass(frozen=True, slots=True)
class AcceptanceFrontierVariants:
    raw_confirmation_state: str
    boundary_confirmation_state: str
    frontier_advance_state: str
    boundary_components: tuple[AcceptanceEventComponent, ...]
    frontier_advance_components: tuple[AcceptanceEventComponent, ...]
    genuine_conflict: bool
    conflict_reasons: tuple[str, ...]


def _collapse(
    components: Iterable[AcceptanceEventComponent],
    *,
    up_label: str,
    down_label: str,
    compound_label: str,
) -> str:
    directions = {item.direction for item in components}
    if not directions:
        return "NONE"
    if directions == {"UP"}:
        return up_label
    if directions == {"DOWN"}:
        return down_label
    return compound_label


def resolve_acceptance_frontier_variants(
    raw_event: AcceptanceEventSnapshot,
    *,
    current_floor_level_ids: Iterable[str],
    current_floor_price: Decimal | None,
    current_ceiling_level_ids: Iterable[str],
    current_ceiling_price: Decimal | None,
    previous_floor_price: Decimal | None,
    previous_ceiling_price: Decimal | None,
    contiguous: bool,
) -> AcceptanceFrontierVariants:
    conflicts = set(raw_event.conflict_reasons)
    floor_ids = set(current_floor_level_ids)
    ceiling_ids = set(current_ceiling_level_ids)
    if current_floor_price is not None and current_ceiling_price is not None:
        if current_floor_price >= current_ceiling_price:
            conflicts.add("INVALID_ACCEPTED_FRONTIER_BOUNDS")

    boundary_components = []
    advance_components = []
    for component in raw_event.components:
        support = set(component.support_level_ids)
        if component.direction == "UP":
            at_boundary = bool(support.intersection(floor_ids))
            advances = (
                contiguous
                and at_boundary
                and current_floor_price is not None
                and (previous_floor_price is None or current_floor_price > previous_floor_price)
            )
        elif component.direction == "DOWN":
            at_boundary = bool(support.intersection(ceiling_ids))
            advances = (
                contiguous
                and at_boundary
                and current_ceiling_price is not None
                and (previous_ceiling_price is None or current_ceiling_price < previous_ceiling_price)
            )
        else:
            conflicts.add("INVALID_ACCEPTANCE_DIRECTION")
            at_boundary = False
            advances = False
        if at_boundary:
            boundary_components.append(component)
        if advances:
            advance_components.append(component)

    if conflicts:
        boundary_state = "CONFLICTING"
        advance_state = "CONFLICTING"
    else:
        boundary_state = _collapse(
            boundary_components,
            up_label="BOUNDARY_ACCEPTED_ABOVE_EVENT",
            down_label="BOUNDARY_ACCEPTED_BELOW_EVENT",
            compound_label="COMPOUND_BOUNDARY_ACCEPTANCE_EVENT",
        )
        advance_state = _collapse(
            advance_components,
            up_label="FRONTIER_ADVANCE_UP",
            down_label="FRONTIER_ADVANCE_DOWN",
            compound_label="COMPOUND_FRONTIER_ADVANCE",
        )
    return AcceptanceFrontierVariants(
        raw_confirmation_state=raw_event.semantic_state,
        boundary_confirmation_state=boundary_state,
        frontier_advance_state=advance_state,
        boundary_components=tuple(boundary_components),
        frontier_advance_components=tuple(advance_components),
        genuine_conflict=bool(conflicts),
        conflict_reasons=tuple(sorted(conflicts)),
    )
