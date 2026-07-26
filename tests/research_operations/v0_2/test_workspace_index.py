from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.research_operations.v0_2.workspace_index import AccessDenied, build_indexes, validation_metadata_only

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/v0_2/wp1_workspace_index_cases.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class WorkspaceIndexTests(unittest.TestCase):
    def test_deterministic_index_hash_and_counts(self):
        fixture = load_fixture()
        first = build_indexes(fixture["approved_releases"], fixture["validation_metadata"])
        second = build_indexes(list(reversed(fixture["approved_releases"])), fixture["validation_metadata"])
        self.assertEqual(first["logical_index_hash"], second["logical_index_hash"])
        self.assertEqual(len(first["workspaces"]), 2)
        self.assertEqual(len(first["observations"]), 3)
        self.assertEqual(first["validation"]["availability"], "METADATA_ONLY")
        self.assertEqual(first["validation"]["validation_consumption"], "LOCKED_UNCONSUMED")

    def test_validation_denied_before_path_resolution(self):
        metadata = dict(load_fixture()["validation_metadata"])
        metadata["local_path"] = "C:/forbidden"
        with self.assertRaisesRegex(AccessDenied, "before path resolution"):
            validation_metadata_only(metadata)

    def test_validation_cannot_enter_content_build(self):
        release = dict(load_fixture()["validation_metadata"])
        release["observations"] = []
        with self.assertRaises(AccessDenied):
            build_indexes([release])

    def test_unknown_role_fails_closed(self):
        release = dict(load_fixture()["approved_releases"][0])
        release["role"] = "UNKNOWN"
        with self.assertRaises(AccessDenied):
            build_indexes([release])

    def test_conflicting_duplicate_observation_is_blocked(self):
        release = dict(load_fixture()["approved_releases"][0])
        duplicate = dict(release["observations"][0])
        duplicate["observation_id"] = "FIXED-ID"
        first = dict(duplicate)
        first["clock"] = "15M"
        second = dict(duplicate)
        second["clock"] = "2H_A_L"
        release["observations"] = [first, second]
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            build_indexes([release])


if __name__ == "__main__":
    unittest.main()
