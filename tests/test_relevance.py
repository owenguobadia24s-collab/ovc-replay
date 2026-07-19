from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import unittest

from test_contracts import START, level
from ovc_opt_b import RelevancePolicy, build_level_lifecycles


class RelevanceLifecycleTests(unittest.TestCase):
    def test_range_level_retires_when_next_same_type_becomes_valid(self) -> None:
        first = level()
        second = replace(
            first,
            level_id="L2",
            price=first.price + 1,
            created_at=START + timedelta(hours=1),
            first_valid_time=START + timedelta(hours=1),
        )
        policy = RelevancePolicy("supersession", None, None, True, False)
        lifecycles = {item.level_id: item for item in build_level_lifecycles([first, second], policy=policy)}
        self.assertEqual(lifecycles["L1"].retired_at, second.first_valid_time)
        self.assertEqual(lifecycles["L1"].retirement_reason, "RANGE_SUPERSEDED")
        self.assertFalse(lifecycles["L1"].is_relevant(second.first_valid_time))

    def test_acceptance_retirement_is_effective_at_confirmation(self) -> None:
        candidate = replace(level(), level_type="PRIOR_SWING_HIGH")
        accepted_at = START + timedelta(hours=4)
        policy = RelevancePolicy("acceptance", None, None, False, True)
        lifecycle = build_level_lifecycles(
            [candidate], policy=policy, acceptance_times={candidate.level_id: (accepted_at, "term-1")}
        )[0]
        self.assertTrue(lifecycle.is_relevant(accepted_at - timedelta(microseconds=1)))
        self.assertFalse(lifecycle.is_relevant(accepted_at))
        self.assertEqual(lifecycle.retirement_trigger_id, "term-1")

    def test_earliest_retirement_wins_with_deterministic_tie_priority(self) -> None:
        candidate = replace(level(), level_type="PRIOR_SWING_LOW")
        expiry = candidate.first_valid_time + timedelta(hours=48)
        policy = RelevancePolicy("hybrid", timedelta(hours=8), timedelta(hours=48), True, True)
        lifecycle = build_level_lifecycles(
            [candidate], policy=policy, acceptance_times={candidate.level_id: (expiry, "term-accept")}
        )[0]
        self.assertEqual(lifecycle.retired_at, expiry)
        self.assertEqual(lifecycle.retirement_reason, "ACCEPTED_THROUGH")


if __name__ == "__main__":
    unittest.main()
