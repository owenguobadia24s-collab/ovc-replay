from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.research_console.repository_topology_surface import (
    load_repository_topology,
    load_repository_topology_diff,
    projection_identity,
)


class RepositoryTopologySurfaceTests(unittest.TestCase):
    def test_repository_topology_surface_fails_closed_when_missing(self) -> None:
        with TemporaryDirectory() as directory:
            value = load_repository_topology(Path(directory) / "missing.json")
        identity = projection_identity(value)
        self.assertEqual(identity["availability"], "NOT_MATERIALIZED")
        self.assertEqual(identity["authority_effect"], "NONE_PRESENTATION_ONLY")

    def test_repository_topology_surface_accepts_only_derived_authority_neutral_model(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "topology.json"
            path.write_text(json.dumps({
                "schema": "ovc-genesis-repository-topology-read-model/v1",
                "authority_effect": "NONE_DERIVED_REPLACEABLE_READ_MODEL",
                "topology_sha256": "a" * 64,
                "portfolio": {"source_commit": "b" * 40, "programme_count": 3, "component_count": 7, "anomaly_count": 2},
            }), encoding="utf-8")
            value = load_repository_topology(path)
        identity = projection_identity(value)
        self.assertEqual(identity, {
            "availability": "AVAILABLE",
            "route_state": "LOCAL_READ_ONLY_SYSTEM_SURFACE",
            "topology_sha256": "a" * 64,
            "source_commit": "b" * 40,
            "programme_count": 3,
            "component_count": 7,
            "anomaly_count": 2,
            "authority_effect": "NONE_PRESENTATION_ONLY",
        })

    def test_repository_topology_surface_rejects_authority_bearing_payload(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({
                "schema": "ovc-genesis-repository-topology-read-model/v1",
                "authority_effect": "MUTATION_ALLOWED",
            }), encoding="utf-8")
            value = load_repository_topology(path)
        self.assertEqual(value["availability"], "NOT_MATERIALIZED")
        self.assertEqual(value["reason"], "TOPOLOGY_AUTHORITY_BOUNDARY_MISMATCH")

    def test_repository_topology_diff_fails_closed_when_missing_or_authority_bearing(self) -> None:
        with TemporaryDirectory() as directory:
            missing = load_repository_topology_diff(Path(directory) / "missing.json")
            self.assertEqual(missing["reason"], "TOPOLOGY_DIFF_NOT_PRESENT")
            path = Path(directory) / "bad-diff.json"
            path.write_text(json.dumps({
                "schema": "ovc-genesis-repository-topology-diff/v1",
                "authority_effect": "MUTATION_ALLOWED",
            }), encoding="utf-8")
            rejected = load_repository_topology_diff(path)
        self.assertEqual(rejected["availability"], "NOT_MATERIALIZED")
        self.assertEqual(rejected["reason"], "TOPOLOGY_DIFF_AUTHORITY_BOUNDARY_MISMATCH")

    def test_repository_topology_diff_accepts_only_read_only_wp10_payload(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "diff.json"
            payload = {
                "schema": "ovc-genesis-repository-topology-diff/v1",
                "authority_effect": "NONE_DERIVED_COMMIT_DIFF_ONLY",
                "before": {"source_commit": "a" * 40, "topology_sha256": "b" * 64},
                "after": {"source_commit": "c" * 40, "topology_sha256": "d" * 64},
                "change_count": 0,
                "change_type_counts": {},
                "changes": [],
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            value = load_repository_topology_diff(path)
        self.assertEqual(value["schema"], "ovc-genesis-repository-topology-diff/v1")
        self.assertEqual(value["authority_effect"], "NONE_DERIVED_COMMIT_DIFF_ONLY")


if __name__ == "__main__":
    unittest.main()
