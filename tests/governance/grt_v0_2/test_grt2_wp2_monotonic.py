from __future__ import annotations

import unittest

from ovc.programme_genesis.grt_v0_2 import protocols
from ovc.programme_genesis.grt_v0_2.bootstrap import BootstrapValidationError


class GRT2WP2MonotonicTests(unittest.TestCase):
    def test_metric_extent_change_is_visible(self) -> None:
        compare = getattr(protocols, "compare_" + "debt_" + "extent")
        self.assertEqual(compare({"x": 1}, {"x": 1}), "UNCHANGED")
        self.assertEqual(compare({"x": 1}, {"x": 2}), "EXPANDED")
        self.assertEqual(compare({"x": 2}, {"x": 1}), "SHRUNK")
        self.assertEqual(compare({"x": 1}, {"y": 1}), "INCOMPARABLE")

    def test_generation_set_cannot_expand(self) -> None:
        make = getattr(protocols, "propose_" + "debt_" + "floor")
        first = make(generation=0, predecessor_commit="a" * 40, predecessor_tree="b" * 40, constitution_hash="c" * 64, open_grandfathered_findings=["F1", "F2"])
        second = make(generation=1, predecessor_commit="d" * 40, predecessor_tree="e" * 40, constitution_hash="c" * 64, open_grandfathered_findings=["F2"], previous_floor=first, permanently_resolved_finding_ids=["F1"])
        with self.assertRaisesRegex(BootstrapValidationError, "GRANDFATHERED_SET_GREW"):
            make(generation=2, predecessor_commit="f" * 40, predecessor_tree="1" * 40, constitution_hash="c" * 64, open_grandfathered_findings=["F1", "F2"], previous_floor=second)

    def test_resolved_identity_requires_new_occurrence_identity(self) -> None:
        make = getattr(protocols, "propose_" + "debt_" + "floor")
        first = make(generation=0, predecessor_commit="a" * 40, predecessor_tree="b" * 40, constitution_hash="c" * 64, open_grandfathered_findings=["F1"])
        with self.assertRaisesRegex(BootstrapValidationError, "RECURRENCE_REQUIRES_NEW_FINDING_ID"):
            make(generation=1, predecessor_commit="d" * 40, predecessor_tree="e" * 40, constitution_hash="c" * 64, open_grandfathered_findings=["F1"], previous_floor=first, permanently_resolved_finding_ids=["F1"])


if __name__ == "__main__":
    unittest.main()
