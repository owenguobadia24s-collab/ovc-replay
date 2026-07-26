from __future__ import annotations

import unittest

from ovc.research_operations.v0_2.console_adapters import (
    ConsoleProjectionDenied,
    adapt_replay,
    adapt_workspace,
    build_research_console_projection,
)


class ConsoleAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = {
            "workspaces": [
                {
                    "workspace_id": "RO2-WS-1",
                    "role": "DISCOVERY",
                    "release_id": "REL-D",
                    "manifest_sha256": "a" * 64,
                    "instrument": "GBPUSD",
                    "availability": "AVAILABLE",
                    "observation_count": 2,
                }
            ],
            "validation": {
                "role": "VALIDATION",
                "release_id": "REL-V",
                "manifest_sha256": "b" * 64,
                "aggregate_record_count": 10,
                "validation_consumption": "LOCKED_UNCONSUMED",
                "availability": "METADATA_ONLY",
            },
        }
        self.quality = {"status": "PASS", "record_count": 2, "duplicate_source_object_ids": [], "missing_required_fields": []}
        self.lineage = {"status": "PASS", "source_object_id": "OBS-1", "trace": [{"kind": "OBSERVATION", "id": "OBS-1"}]}
        self.replay = {
            "role": "DISCOVERY",
            "cutoff": "2024-01-02T00:00:00Z",
            "accepted": [{"source_object_id": "OBS-1"}],
            "accepted_count": 1,
            "post_cutoff_rejected": ["OBS-2"],
        }
        self.comparison = {
            "status": "DIFFERENT",
            "base_identity": "BASE",
            "target_identity": "TARGET",
            "dimensions": {"record_count": {"base": 1, "target": 2}},
            "differences": ["record_count"],
            "comparison_sha256": "c" * 64,
        }

    def test_projection_is_deterministic_and_read_only(self) -> None:
        first = build_research_console_projection(
            workspace=self.workspace,
            quality=self.quality,
            lineage=self.lineage,
            replay=self.replay,
            comparison=self.comparison,
        )
        second = build_research_console_projection(
            workspace=self.workspace,
            quality=self.quality,
            lineage=self.lineage,
            replay=self.replay,
            comparison=self.comparison,
        )
        self.assertEqual(first, second)
        self.assertTrue(first["read_only"])
        self.assertEqual(first["writes"], "NONE")

    def test_validation_is_metadata_only(self) -> None:
        projection = adapt_workspace(self.workspace)
        self.assertEqual(projection["validation"]["availability"], "METADATA_ONLY")
        self.assertEqual(projection["validation"]["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertNotIn("rows", projection["validation"])

    def test_validation_content_is_denied_before_resolution(self) -> None:
        forbidden = {"role": "VALIDATION", "release_id": "REL-V", "manifest_sha256": "b" * 64, "rows": []}
        with self.assertRaisesRegex(ConsoleProjectionDenied, "VALIDATION_DENY_BEFORE_PATH_RESOLUTION"):
            adapt_workspace({"workspaces": [], "validation": forbidden})

    def test_replay_hides_post_cutoff_ids(self) -> None:
        projection = adapt_replay(self.replay)
        self.assertEqual(projection["visible_source_object_ids"], ["OBS-1"])
        self.assertEqual(projection["hidden_post_cutoff_count"], 1)
        self.assertNotIn("OBS-2", str(projection))

    def test_write_capability_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConsoleProjectionDenied, "READ_ONLY_CONSOLE_PROJECTION_REQUIRED"):
            adapt_replay({**self.replay, "git_write": True})


if __name__ == "__main__":
    unittest.main()
