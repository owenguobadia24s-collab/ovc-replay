from __future__ import annotations

import unittest

from ovc.research_operations.v0_2.lineage import inspect_lineage
from ovc.research_operations.v0_2.quality import project_quality
from ovc.research_operations.v0_2.release_diff import compare_snapshots
from ovc.research_operations.v0_2.replay import replay_to_cutoff


ROWS = [
    {"source_object_id": "A", "clock": "15M", "side": "BID", "first_valid_at": "2024-01-01T00:15:00Z", "schema_version": "opt-a-bar/v2", "release_id": "R1", "manifest_sha256": "m1"},
    {"source_object_id": "B", "clock": "2H_A_L", "side": "BID", "first_valid_at": "2024-01-01T02:00:00Z", "schema_version": "opt-a-bar/v2", "parent_object_id": "A", "release_id": "R1", "manifest_sha256": "m1"},
]


class WP2OperationTests(unittest.TestCase):
    def test_quality_projection_passes_clean_rows(self) -> None:
        result = project_quality(reversed(ROWS))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["record_count"], 2)

    def test_lineage_is_read_only_and_exact(self) -> None:
        result = inspect_lineage(ROWS, "B")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["trace"][1], {"kind": "PARENT_OBJECT_ID", "id": "A"})
        self.assertEqual(result["writes"], "NONE")

    def test_replay_rejects_post_cutoff_rows(self) -> None:
        result = replay_to_cutoff(ROWS, "2024-01-01T00:30:00Z", "DEVELOPMENT")
        self.assertEqual(result["accepted_count"], 1)
        self.assertEqual(result["post_cutoff_rejected"], ["B"])

    def test_validation_denied_before_resolution(self) -> None:
        with self.assertRaisesRegex(PermissionError, "DENY_BEFORE_PATH_RESOLUTION"):
            replay_to_cutoff(ROWS, "2025-01-01T00:00:00Z", "VALIDATION")

    def test_release_diff_is_deterministic(self) -> None:
        first = compare_snapshots({"b": 2, "a": 1}, {"a": 1, "b": 3})
        second = compare_snapshots({"a": 1, "b": 2}, {"b": 3, "a": 1})
        self.assertEqual(first, second)
        self.assertEqual(first["changed_keys"], ["b"])


if __name__ == "__main__":
    unittest.main()
