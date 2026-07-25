from __future__ import annotations

from decimal import Decimal
import unittest

from test_contracts import START
from ovc_opt_b import (
    AxisEvidence,
    LocationCondition,
    acceptance_maintenance_passes,
    displacement_trigger_state,
    resolve_interaction_snapshot,
    resolve_location_snapshot,
)


def condition(level_id: str, direction: str, return_min: str = "0.1") -> LocationCondition:
    return LocationCondition(
        level_id=level_id,
        direction=direction,
        state_since=START,
        refreshed_at=START,
        trigger_term_record_ids=(f"record-{level_id}",),
        return_min=Decimal(return_min),
    )


class ParallelAxisStateTests(unittest.TestCase):
    def test_same_direction_acceptance_compounds_levels(self) -> None:
        snapshot = resolve_location_snapshot(
            {"L1": condition("L1", "UP"), "L2": condition("L2", "UP")},
            level_prices={"L1": Decimal("99"), "L2": Decimal("100")},
        )
        self.assertEqual(snapshot.semantic_state, "ACCEPTED_ABOVE")
        self.assertEqual(snapshot.above_level_ids, ("L1", "L2"))
        self.assertFalse(snapshot.genuine_conflict)

    def test_above_lower_and_below_higher_is_coherent_corridor(self) -> None:
        snapshot = resolve_location_snapshot(
            {"LOW": condition("LOW", "UP"), "HIGH": condition("HIGH", "DOWN")},
            level_prices={"LOW": Decimal("99"), "HIGH": Decimal("101")},
        )
        self.assertEqual(snapshot.semantic_state, "ACCEPTED_CORRIDOR")
        self.assertFalse(snapshot.genuine_conflict)

    def test_inverted_location_bounds_are_genuine_conflict(self) -> None:
        snapshot = resolve_location_snapshot(
            {"HIGH": condition("HIGH", "UP"), "LOW": condition("LOW", "DOWN")},
            level_prices={"LOW": Decimal("99"), "HIGH": Decimal("101")},
        )
        self.assertEqual(snapshot.semantic_state, "CONFLICTING")
        self.assertTrue(snapshot.genuine_conflict)

    def test_acceptance_maintenance_is_level_specific(self) -> None:
        above = condition("L1", "UP")
        below = condition("L2", "DOWN")
        self.assertTrue(acceptance_maintenance_passes(above, close=Decimal("100.1"), level_price=Decimal("100")))
        self.assertFalse(acceptance_maintenance_passes(above, close=Decimal("100.09"), level_price=Decimal("100")))
        self.assertTrue(acceptance_maintenance_passes(below, close=Decimal("99.9"), level_price=Decimal("100")))

    def test_different_interactions_at_different_levels_coexist(self) -> None:
        snapshot = resolve_interaction_snapshot([
            AxisEvidence("INTERACTION", "RECLAIM", "RECLAIMED_ABOVE", "UP", "L1", "R1", "CONFIRMED"),
            AxisEvidence("INTERACTION", "REJECTION", "REJECTED_DOWN", "DOWN", "L2", "R2", "CONFIRMED"),
        ])
        self.assertEqual(snapshot.semantic_state, "COMPOUND")
        self.assertFalse(snapshot.genuine_conflict)
        self.assertEqual(len(snapshot.components), 2)

    def test_same_interaction_and_level_opposite_directions_conflicts(self) -> None:
        snapshot = resolve_interaction_snapshot([
            AxisEvidence("INTERACTION", "RECLAIM", "RECLAIMED_ABOVE", "UP", "L1", "R1", "CONFIRMED"),
            AxisEvidence("INTERACTION", "RECLAIM", "RECLAIMED_BELOW", "DOWN", "L1", "R2", "CONFIRMED"),
        ])
        self.assertEqual(snapshot.semantic_state, "CONFLICTING")
        self.assertTrue(snapshot.genuine_conflict)

    def test_acceptance_does_not_suppress_displacement(self) -> None:
        location = resolve_location_snapshot(
            {"L1": condition("L1", "UP")},
            level_prices={"L1": Decimal("99")},
        )
        displacement, conflicts = displacement_trigger_state([
            AxisEvidence("DISPLACEMENT", "DISPLACEMENT", "DISPLACING_DOWN", "DOWN", None, "D1", "CONFIRMED")
        ])
        self.assertEqual(location.semantic_state, "ACCEPTED_ABOVE")
        self.assertEqual(displacement, "DISPLACING_DOWN")
        self.assertEqual(conflicts, ())


if __name__ == "__main__":
    unittest.main()
