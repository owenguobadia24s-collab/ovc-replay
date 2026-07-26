from __future__ import annotations

import unittest

from ovc.opt_b.c2.engine import C2ScopeEngine
from ovc.opt_b.c2.state import AXES
from tests.opt_b.c2.test_wp3_structure_engine import parent


class WP4EngineTrustTests(unittest.TestCase):
    def test_parallel_axes_are_complete_and_independent(self) -> None:
        engine = C2ScopeEngine("GBPUSD-15M-LOCAL-v0.1")
        result = None
        for index in range(32):
            result = engine.process(parent(index))
        assert result is not None
        self.assertEqual(tuple(result.state["axes"]), AXES)
        self.assertNotIn("overall_state", result.state)
        self.assertNotIn("winning_state", result.state)

    def test_deterministic_identity(self) -> None:
        def run() -> dict:
            engine = C2ScopeEngine("GBPUSD-15M-LOCAL-v0.1")
            result = None
            for index in range(32):
                result = engine.process(parent(index))
            assert result is not None
            return result.state

        self.assertEqual(run(), run())

    def test_persistence_increments_only_for_unchanged_axes(self) -> None:
        engine = C2ScopeEngine("GBPUSD-15M-LOCAL-v0.1")
        for index in range(32):
            first = engine.process(parent(index))
        second = engine.process(parent(32))
        self.assertGreaterEqual(second.state["persistence"]["LOCATION"], first.state["persistence"]["LOCATION"])
        self.assertEqual(second.state["continuity"], "CONTIGUOUS")

    def test_transition_lists_only_changed_axes(self) -> None:
        engine = C2ScopeEngine("GBPUSD-15M-LOCAL-v0.1")
        for index in range(32):
            engine.process(parent(index))
        changed = parent(32, close="1.1005")
        changed["measurements"]["body_signed"] = "-0.0045"
        changed["measurements"]["body_abs"] = "0.0045"
        changed["categorical"]["direction"] = "DOWN"
        result = engine.process(changed)
        self.assertIsNotNone(result.transition)
        self.assertIn("MOTION", result.transition["changed_axes"])
        self.assertNotIn("future_outcome", result.transition)

    def test_gap_resets_persistence_and_first_valid_history(self) -> None:
        engine = C2ScopeEngine("GBPUSD-15M-LOCAL-v0.1")
        for index in range(32):
            engine.process(parent(index))
        gapped = parent(40)
        result = engine.process(gapped)
        self.assertEqual(result.state["continuity"], "RESET")
        self.assertEqual(result.state["axes"]["QUALITY"]["value"], "CENSORED")


if __name__ == "__main__":
    unittest.main()
