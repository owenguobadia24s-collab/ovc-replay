from __future__ import annotations

import unittest

from ovc.opt_b.c2.persistence import apply_persistence
from ovc.opt_b.c2.state import AXES, build_parallel_state
from ovc.opt_b.c2.transitions import build_transition


def fixture(close: str = "1.2500", open_: str = "1.2490") -> dict:
    measurements = {
        "open": open_, "high": "1.2510", "low": "1.2480", "close": close,
        "range_low": "1.2400", "range_high": "1.2600",
        "swing_low": "1.2300", "swing_high": "1.2700", "prior_range": "0.0020",
    }
    for index in range(9, 18):
        measurements[f"m{index}"] = str(index)
    return {
        "c1_record_id": "C1.TEST.1", "c1_release_id": "OPT-B.C1.GBPUSD.DISCOVERY.TEST",
        "c1_manifest_id": "MANIFEST.C1.TEST", "opt_a_release_id": "OPT-A.TEST",
        "opt_a_manifest_id": "MANIFEST.A.TEST", "role": "DISCOVERY",
        "authority_state": "ACTIVE_DISCOVERY", "instrument": "GBPUSD", "clock": "15M",
        "side": "BID", "close_time": "2026-01-01T00:15:00Z",
        "first_valid_time": "2026-01-01T00:15:00Z", "measurements": measurements,
        "quality_state": "VALID",
    }


class WP4EngineTrustTests(unittest.TestCase):
    def test_parallel_axes_are_complete_and_independent(self) -> None:
        state = build_parallel_state(fixture())
        self.assertEqual(tuple(state["axes"]), AXES)
        self.assertNotIn("overall_state", state)
        self.assertNotIn("winning_state", state)

    def test_deterministic_identity(self) -> None:
        self.assertEqual(build_parallel_state(fixture()), build_parallel_state(fixture()))

    def test_persistence_increments_only_for_unchanged_axes(self) -> None:
        first = apply_persistence(build_parallel_state(fixture()), None)
        second = apply_persistence(build_parallel_state(fixture()), first)
        self.assertTrue(all(value == 2 for value in second["persistence"].values()))

    def test_transition_lists_only_changed_axes(self) -> None:
        previous = apply_persistence(build_parallel_state(fixture()), None)
        changed_record = fixture(close="1.2485", open_="1.2495")
        changed_record["c1_record_id"] = "C1.TEST.2"
        current = apply_persistence(build_parallel_state(changed_record), previous)
        transition = build_transition(current, previous)
        self.assertIsNotNone(transition)
        self.assertIn("MOTION", transition["changed_axes"])
        self.assertNotIn("future_outcome", transition)


if __name__ == "__main__":
    unittest.main()
