from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from apps.research_console.ro2_projection_source import load_ro2_projection, projection_identity


class RcG3AcceptanceTests(unittest.TestCase):
    def _write(self, payload: dict) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "projection.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_discovery_projection_is_consumed_read_only(self) -> None:
        path = self._write({
            "schema": "ovc-ro2-console-research-projection/v1",
            "projection_id": "RO2-CONSOLE-001",
            "role": "DISCOVERY",
            "release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
            "manifest_sha256": "a" * 64,
            "availability": "AVAILABLE",
            "writes": "NONE",
        })
        result = load_ro2_projection(path)
        self.assertEqual(result["authority"], "ACCEPTED_LOCAL_READ_ONLY_PRESENTATION")
        self.assertEqual(result["writes"], "NONE")
        self.assertEqual(projection_identity(result)["projection_id"], "RO2-CONSOLE-001")

    def test_validation_is_metadata_only(self) -> None:
        path = self._write({
            "schema": "ovc-ro2-console-research-projection/v1",
            "projection_id": "RO2-VAL-001",
            "role": "VALIDATION",
            "release_id": "OPT-A.GBPUSD.VALIDATION.2025.v2",
            "manifest_sha256": "b" * 64,
            "aggregate_record_count": 10,
            "validation_consumption": "LOCKED_UNCONSUMED",
            "availability": "METADATA_ONLY",
            "writes": "NONE",
        })
        self.assertEqual(load_ro2_projection(path)["availability"], "METADATA_ONLY")

    def test_validation_content_is_denied_before_presentation(self) -> None:
        path = self._write({
            "schema": "ovc-ro2-console-research-projection/v1",
            "projection_id": "RO2-VAL-002",
            "role": "VALIDATION",
            "release_id": "VAL",
            "manifest_sha256": "c" * 64,
            "aggregate_record_count": 10,
            "validation_consumption": "LOCKED_UNCONSUMED",
            "availability": "METADATA_ONLY",
            "timestamps": ["2025-01-01T00:00:00Z"],
            "writes": "NONE",
        })
        self.assertEqual(load_ro2_projection(path)["reason"], "VALIDATION_CONTENT_DENIED_BEFORE_PRESENTATION")

    def test_write_capability_fails_closed(self) -> None:
        path = self._write({
            "schema": "ovc-ro2-console-research-projection/v1",
            "projection_id": "RO2-WRITE-001",
            "role": "DISCOVERY",
            "writes": "GIT",
        })
        self.assertEqual(load_ro2_projection(path)["reason"], "RO2_PROJECTION_WRITE_DENIED")

    def test_missing_projection_is_not_evaluated(self) -> None:
        result = load_ro2_projection("/definitely/missing/ro2.json")
        self.assertEqual(result["availability"], "NOT_EVALUATED")
        self.assertEqual(result["writes"], "NONE")


if __name__ == "__main__":
    unittest.main()
