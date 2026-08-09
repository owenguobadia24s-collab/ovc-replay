from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "research_console_vnext" / "console_pack_v0_1"


class WP2StaticContractTests(unittest.TestCase):
    def test_fixture_manifest_is_non_evidentiary_and_complete(self) -> None:
        manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("OVC-RC-VNEXT-CONSOLE-FIXTURE-PACK-v0.1", manifest["pack_id"])
        self.assertEqual("SYNTHETIC_FIXTURE", manifest["data_classification"])
        self.assertEqual("NON_EVIDENTIARY", manifest["evidence_status"])
        self.assertEqual("NONE", manifest["authority_effect"])
        self.assertTrue(manifest["display_banner_required"])
        self.assertIn("investigations", manifest["resources"])

    def test_capability_dependency_status_has_full_contract(self) -> None:
        payload = json.loads((FIXTURES / "capabilities.json").read_text(encoding="utf-8"))
        required = {
            "capability_id", "display_name", "implementation_state", "source_materialization",
            "source_compatibility", "available", "authorised", "active", "authority_effect",
            "source_identity", "blockers", "dependencies", "last_verified_commit",
        }
        for row in payload["items"]:
            self.assertEqual(required, set(row))
            self.assertEqual("NONE", row["authority_effect"])
            self.assertEqual({"commit", "release_id", "contract_ids", "schema_ids", "logical_hashes"}, set(row["source_identity"]))
            for dependency in row["dependencies"]:
                self.assertEqual({"capability_id", "relation", "evidence_class"}, set(dependency))

    def test_openapi_snapshot_declares_get_only_routes(self) -> None:
        snapshot = json.loads((FIXTURES / "openapi_snapshot_v1.json").read_text(encoding="utf-8"))
        self.assertEqual("3.1.0", snapshot["openapi"])
        self.assertTrue(snapshot["paths"])
        self.assertTrue(all(value["methods"] == ["get"] for value in snapshot["paths"].values()))

    @unittest.skipIf(importlib.util.find_spec("fastapi") is None, "FastAPI dependency not installed in generic repository environment")
    def test_runtime_contract(self) -> None:
        from fastapi.testclient import TestClient
        from apps.research_api.app import create_app
        from apps.research_api.query import CACHE_ENABLED, CanonicalQuery

        app = create_app()
        client = TestClient(app)
        self.assertFalse(CACHE_ENABLED)

        openapi = app.openapi()
        snapshot = json.loads((FIXTURES / "openapi_snapshot_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(set(snapshot["paths"]), {path for path in openapi["paths"] if path.startswith("/api/v1/")})
        for path in snapshot["paths"]:
            self.assertEqual({"get"}, {method.lower() for method in openapi["paths"][path] if method.lower() in {"get","post","put","patch","delete"}})

        status = client.get("/api/v1/status")
        self.assertEqual(200, status.status_code)
        body = status.json()
        self.assertEqual("SYNTHETIC_FIXTURE", body["fixture_banner"]["data_classification"])
        self.assertEqual("NON_EVIDENTIARY", body["fixture_banner"]["evidence_status"])
        self.assertEqual("NONE", body["capability"]["authority_effect"])
        self.assertTrue(body["schema_id"])
        self.assertTrue(body["source_identity"]["commit"])

        capabilities = client.get("/api/v1/capabilities").json()["payload"]
        self.assertEqual(sorted(row["capability_id"] for row in capabilities), [row["capability_id"] for row in capabilities])
        c2e = next(row for row in capabilities if row["capability_id"] == "C2E")
        self.assertFalse(c2e["available"])
        self.assertFalse(c2e["authorised"])
        self.assertFalse(c2e["active"])

        store = app.state.fixture_store
        before = store.resource_reads
        denied = client.get("/api/v1/market/window?role=VALIDATION")
        self.assertEqual(403, denied.status_code)
        self.assertEqual("AUTHORITY_DENIED", denied.json()["reason_code"])
        self.assertEqual(before, store.resource_reads)

        for method in ("post", "put", "patch", "delete"):
            response = getattr(client, method)("/api/v1/status")
            self.assertEqual(405, response.status_code)
            self.assertEqual("MUTATION_METHOD_DENIED", response.json()["reason_code"])

        first = client.get("/api/v1/evidence/objects?cursor=0&limit=2").json()["payload"]
        second = client.get(f"/api/v1/evidence/objects?cursor={first['next_cursor']}&limit=2").json()["payload"]
        self.assertEqual(["EV-SYNTH-001", "EV-SYNTH-002"], [row["evidence_id"] for row in first["items"]])
        self.assertEqual(["EV-SYNTH-003", "EV-SYNTH-004"], [row["evidence_id"] for row in second["items"]])

        window = client.get("/api/v1/market/window?start=2026-01-01T08:15:00Z&end=2026-01-01T08:30:00Z&limit=10").json()["payload"]
        self.assertEqual(2, len(window["items"]))

        left = CanonicalQuery.from_mapping("evidence", {"limit": 2, "cursor": 0}).cache_key()
        right = CanonicalQuery.from_mapping("evidence", {"cursor": 0, "limit": 2}).cache_key()
        self.assertEqual(left, right)


if __name__ == "__main__":
    unittest.main()
