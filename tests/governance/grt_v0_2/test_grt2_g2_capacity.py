from __future__ import annotations

import unittest

from ovc.programme_genesis.grt_v0_2.capacity import CapacityExceeded, enforce_capacity


class GRT2G2CapacityTests(unittest.TestCase):
    def test_capacity_guard_is_exact_and_fail_closed(self) -> None:
        enforce_capacity(observed_scale=99, capacity_failure_threshold=100)
        with self.assertRaises(CapacityExceeded) as ctx:
            enforce_capacity(observed_scale=100, capacity_failure_threshold=100)
        self.assertIn("CAPACITY_EXCEEDED", str(ctx.exception))

    def test_invalid_capacity_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            enforce_capacity(observed_scale=True, capacity_failure_threshold=100)
        with self.assertRaises(ValueError):
            enforce_capacity(observed_scale=1, capacity_failure_threshold=0)


if __name__ == "__main__":
    unittest.main()
