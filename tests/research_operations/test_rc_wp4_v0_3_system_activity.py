from __future__ import annotations

import unittest

from apps.research_console.fixtures import fixture_bundle
from apps.research_console.system_workspace import (
    build_system_projection,
    filter_activity,
    unavailable_system_projection,
)


class RcWp4SystemActivityTests(unittest.TestCase):
    def _build(self):
        return build_system_projection(
            source_commit="a" * 40,
            read_model_sha256="b" * 64,
            objects=[
                {
                    "object_id": "OBJ.2",
                    "object_type": "QA",
                    "status": "WARN",
                    "source_refs": ["docs/qa.json"],
                },
                {
                    "object_id": "OBJ.1",
                    "object_type": "RELEASE",
                    "status": "PASS",
                    "source_refs": ["docs/release.json"],
                },
            ],
            releases=[{"release_id": "R2"}, {"release_id": "R1"}],
            gates=[{"gate": "G2"}, {"gate": "G1"}],
            catalogue=[{"artifact_id": "B"}, {"artifact_id": "A"}],
            configuration={"local_only": True, "writes": "NONE"},
            activity=[
                {
                    "time": "2026-07-26T12:00:00Z",
                    "type": "release",
                    "status": "PASS",
                    "object_id": "OBJ.1",
                    "description": "release accepted",
                    "source_refs": ["docs/release.json"],
                },
                {
                    "time": "2026-07-26T13:00:00Z",
                    "type": "qa",
                    "status": "WARN",
                    "object_id": "OBJ.2",
                    "description": "qa warning",
                    "source_refs": ["docs/qa.json"],
                },
            ],
        )

    def test_projection_is_deterministic_and_sorted(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["writes"], "NONE")
        self.assertEqual(
            [item["object_id"] for item in first["panels"]["OBJECTS_LINEAGE"]],
            ["OBJ.1", "OBJ.2"],
        )
        self.assertEqual([item["object_id"] for item in first["activity"]], ["OBJ.2", "OBJ.1"])

    def test_activity_filter_is_read_only_and_deterministic(self):
        projection = self._build()
        rows = filter_activity(projection, activity_type="QA", status="WARN")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["object_id"], "OBJ.2")
        rows[0]["status"] = "BLOCK"
        self.assertEqual(projection["activity"][0]["status"], "WARN")

    def test_missing_source_refs_fail_closed(self):
        with self.assertRaises(ValueError):
            build_system_projection(
                source_commit="a" * 40,
                read_model_sha256="b" * 64,
                objects=[{"object_id": "OBJ.1"}],
                releases=[],
                gates=[],
                activity=[],
            )

    def test_unregistered_activity_vocabulary_fails_closed(self):
        with self.assertRaises(ValueError):
            build_system_projection(
                source_commit="a" * 40,
                read_model_sha256="b" * 64,
                objects=[{"object_id": "OBJ.1", "source_refs": ["x"]}],
                releases=[],
                gates=[],
                activity=[{"type": "TRADE", "status": "PASS", "object_id": "OBJ.1", "source_refs": ["x"]}],
            )

    def test_unregistered_status_fails_closed(self):
        with self.assertRaises(ValueError):
            build_system_projection(
                source_commit="a" * 40,
                read_model_sha256="b" * 64,
                objects=[{"object_id": "OBJ.1", "source_refs": ["x"]}],
                releases=[],
                gates=[],
                activity=[{"type": "QA", "status": "ACTIVE", "object_id": "OBJ.1", "source_refs": ["x"]}],
            )

    def test_fixture_bundle_consumes_exact_projection_surfaces(self):
        bundle = fixture_bundle("VALID")
        projection = bundle["system_projection"]
        self.assertIsNotNone(projection)
        self.assertEqual(bundle["objects"], projection["panels"]["OBJECTS_LINEAGE"])
        self.assertEqual(bundle["releases"], projection["panels"]["RELEASES"])
        self.assertEqual(bundle["gates"], projection["panels"]["QA_GATES"])
        self.assertEqual(bundle["activity"], projection["activity"])
        self.assertEqual(projection["writes"], "NONE")
        self.assertEqual(projection["panels"]["ABOUT_AUTHORITY"]["deployment"], "LOCAL_ONLY_NO_REMOTE_DEPLOY")

    def test_empty_fixture_has_no_projection_and_never_implies_pass(self):
        bundle = fixture_bundle("EMPTY")
        self.assertIsNone(bundle["system_projection"])
        self.assertEqual(bundle["summary_status"], "NOT_EVALUATED")
        self.assertEqual(bundle["objects"], [])
        self.assertEqual(bundle["activity"], [])

    def test_unavailable_projection_never_implies_pass(self):
        projection = unavailable_system_projection("SOURCE_MISSING")
        self.assertEqual(projection["availability"], "NOT_EVALUATED")
        self.assertEqual(projection["activity"], [])
        self.assertEqual(projection["writes"], "NONE")


if __name__ == "__main__":
    unittest.main()
