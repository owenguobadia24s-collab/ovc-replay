from __future__ import annotations

from decimal import Decimal
import unittest

from test_contracts import START
from ovc_opt_b import (
    AxisEvidence,
    LocationCondition,
    resolve_acceptance_event,
    resolve_acceptance_relation_inventory,
)


def condition(level_id: str, direction: str, challenge_count: int = 0) -> LocationCondition:
    return LocationCondition(
        level_id=level_id,
        direction=direction,
        state_since=START,
        refreshed_at=START,
        trigger_term_record_ids=(f"record-{level_id}",),
        return_min=Decimal("0.1"),
        challenge_count=challenge_count,
    )


class AcceptanceRelationStateTests(unittest.TestCase):
    def test_opposite_direction_events_at_different_levels_compound_without_conflict(self) -> None:
        snapshot = resolve_acceptance_event([
            AxisEvidence("LOCATION", "ACCEPTANCE", "ACCEPTED_ABOVE", "UP", "L1", "R1", "CONFIRMED"),
            AxisEvidence("LOCATION", "ACCEPTANCE", "ACCEPTED_BELOW", "DOWN", "L2", "R2", "CONFIRMED"),
        ])
        self.assertEqual(snapshot.semantic_state, "COMPOUND_ACCEPTANCE_EVENT")
        self.assertFalse(snapshot.genuine_conflict)

    def test_same_level_opposite_acceptance_is_conflict(self) -> None:
        snapshot = resolve_acceptance_event([
            AxisEvidence("LOCATION", "ACCEPTANCE", "ACCEPTED_ABOVE", "UP", "L1", "R1", "CONFIRMED"),
            AxisEvidence("LOCATION", "ACCEPTANCE", "ACCEPTED_BELOW", "DOWN", "L1", "R2", "CONFIRMED"),
        ])
        self.assertEqual(snapshot.semantic_state, "CONFLICTING")
        self.assertTrue(snapshot.genuine_conflict)

    def test_relation_inventory_has_no_categorical_corridor_state(self) -> None:
        inventory = resolve_acceptance_relation_inventory(
            {"LOW": condition("LOW", "UP"), "HIGH": condition("HIGH", "DOWN", 1)},
            level_prices={"LOW": Decimal("99"), "HIGH": Decimal("101")},
            close=Decimal("100.25"),
            relation_age_bars={"LOW": 8, "HIGH": 2},
            refreshed_level_ids=("HIGH",),
        )
        self.assertFalse(hasattr(inventory, "semantic_state"))
        self.assertEqual(inventory.accepted_floor_price, Decimal("99"))
        self.assertEqual(inventory.accepted_ceiling_price, Decimal("101"))
        self.assertEqual(inventory.boundary_width, Decimal("2"))
        self.assertEqual(inventory.close_position_in_boundary, Decimal("0.625"))
        self.assertEqual(inventory.relation_count, 2)
        self.assertEqual(inventory.challenged_count, 1)
        self.assertEqual(inventory.refreshed_this_bar_count, 1)
        self.assertEqual(inventory.youngest_relation_age_bars, 2)
        self.assertEqual(inventory.median_relation_age_bars, 5.0)
        self.assertEqual(inventory.oldest_relation_age_bars, 8)

    def test_tied_boundaries_preserve_every_level_id(self) -> None:
        inventory = resolve_acceptance_relation_inventory(
            {"A": condition("A", "UP"), "B": condition("B", "UP")},
            level_prices={"A": Decimal("100"), "B": Decimal("100")},
            close=Decimal("101"),
            relation_age_bars={"A": 1, "B": 3},
        )
        self.assertEqual(inventory.accepted_floor_level_ids, ("A", "B"))
        self.assertEqual(inventory.accepted_floor_price, Decimal("100"))


if __name__ == "__main__":
    unittest.main()
