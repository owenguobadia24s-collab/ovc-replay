from __future__ import annotations

from decimal import Decimal
import unittest

from ovc_opt_b import (
    AcceptanceEventComponent,
    AcceptanceEventSnapshot,
    resolve_acceptance_frontier_variants,
)


def event(*components: AcceptanceEventComponent) -> AcceptanceEventSnapshot:
    if not components:
        state = "NONE"
    elif len({item.direction for item in components}) > 1:
        state = "COMPOUND_ACCEPTANCE_EVENT"
    else:
        state = components[0].semantic_state
    return AcceptanceEventSnapshot(state, tuple(components), False, ())


def component(direction: str, *levels: str) -> AcceptanceEventComponent:
    return AcceptanceEventComponent(
        semantic_state="ACCEPTED_ABOVE_EVENT" if direction == "UP" else "ACCEPTED_BELOW_EVENT",
        direction=direction,
        support_level_ids=tuple(levels),
        trigger_term_record_ids=(f"record-{direction}",),
    )


class AcceptanceFrontierReviewTests(unittest.TestCase):
    def test_interior_confirmation_is_not_a_boundary_event(self) -> None:
        result = resolve_acceptance_frontier_variants(
            event(component("UP", "INTERIOR")),
            current_floor_level_ids=("FLOOR",),
            current_floor_price=Decimal("101"),
            current_ceiling_level_ids=("CEILING",),
            current_ceiling_price=Decimal("103"),
            previous_floor_price=Decimal("100"),
            previous_ceiling_price=Decimal("103"),
            contiguous=True,
        )
        self.assertEqual(result.boundary_confirmation_state, "NONE")
        self.assertEqual(result.frontier_advance_state, "NONE")

    def test_boundary_confirmation_without_advance_is_retained_as_diagnostic(self) -> None:
        result = resolve_acceptance_frontier_variants(
            event(component("UP", "FLOOR")),
            current_floor_level_ids=("FLOOR",),
            current_floor_price=Decimal("101"),
            current_ceiling_level_ids=(),
            current_ceiling_price=None,
            previous_floor_price=Decimal("101"),
            previous_ceiling_price=None,
            contiguous=True,
        )
        self.assertEqual(result.boundary_confirmation_state, "BOUNDARY_ACCEPTED_ABOVE_EVENT")
        self.assertEqual(result.frontier_advance_state, "NONE")

    def test_higher_floor_is_upward_frontier_advance(self) -> None:
        result = resolve_acceptance_frontier_variants(
            event(component("UP", "FLOOR")),
            current_floor_level_ids=("FLOOR",),
            current_floor_price=Decimal("102"),
            current_ceiling_level_ids=(),
            current_ceiling_price=None,
            previous_floor_price=Decimal("101"),
            previous_ceiling_price=None,
            contiguous=True,
        )
        self.assertEqual(result.frontier_advance_state, "FRONTIER_ADVANCE_UP")

    def test_lower_ceiling_is_downward_frontier_advance(self) -> None:
        result = resolve_acceptance_frontier_variants(
            event(component("DOWN", "CEILING")),
            current_floor_level_ids=(),
            current_floor_price=None,
            current_ceiling_level_ids=("CEILING",),
            current_ceiling_price=Decimal("99"),
            previous_floor_price=None,
            previous_ceiling_price=Decimal("100"),
            contiguous=True,
        )
        self.assertEqual(result.frontier_advance_state, "FRONTIER_ADVANCE_DOWN")

    def test_no_advance_is_inferred_across_gap(self) -> None:
        result = resolve_acceptance_frontier_variants(
            event(component("UP", "FLOOR")),
            current_floor_level_ids=("FLOOR",),
            current_floor_price=Decimal("102"),
            current_ceiling_level_ids=(),
            current_ceiling_price=None,
            previous_floor_price=Decimal("101"),
            previous_ceiling_price=None,
            contiguous=False,
        )
        self.assertEqual(result.boundary_confirmation_state, "BOUNDARY_ACCEPTED_ABOVE_EVENT")
        self.assertEqual(result.frontier_advance_state, "NONE")

    def test_opposite_frontier_advances_are_compound_not_conflict(self) -> None:
        result = resolve_acceptance_frontier_variants(
            event(component("UP", "FLOOR"), component("DOWN", "CEILING")),
            current_floor_level_ids=("FLOOR",),
            current_floor_price=Decimal("101"),
            current_ceiling_level_ids=("CEILING",),
            current_ceiling_price=Decimal("104"),
            previous_floor_price=Decimal("100"),
            previous_ceiling_price=Decimal("105"),
            contiguous=True,
        )
        self.assertEqual(result.frontier_advance_state, "COMPOUND_FRONTIER_ADVANCE")
        self.assertFalse(result.genuine_conflict)


if __name__ == "__main__":
    unittest.main()
