from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from apps.research_api.real_source_store import RealSourceStore
from ovc.console_vnext.application.errors import ContractError, SourceConflict

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registries/research_console_vnext/research_native/owner_read_projection_bindings_v1.json"


def projection(capability: str, namespace: str, payload: dict, *, denominator: int = 1, missing: int = 0) -> dict:
    return {
        "schema": "ovc-rcn-owner-read-projection/v1",
        "capability_id": capability,
        "owner_namespace": namespace,
        "availability": "AVAILABLE",
        "source_identity": {"source_id": f"TEST.{capability}.OWNER.v1", "source_commit": "abcdef1234567890"},
        "chronology": {"first_valid_time": "2024-01-01T00:00:00Z", "cutoff": "2024-01-01T02:00:00Z", "ordering": "FIRST_VALID_CHRONOLOGY"},
        "missingness": {"status": "COMPLETE" if missing == 0 else "PARTIAL", "evaluable_count": denominator - missing, "missing_count": missing, "denominator": denominator, "reason_codes": []},
        "qa": {"status": "PASS", "provenance": ["TEST_ONLY"]},
        "authority": {"read_only": True, "writes": "NONE", "validation_consumption": "LOCKED_UNCONSUMED", "source_owner_authority": "UNCHANGED"},
        "payload": payload,
    }


class PostG4RealSourceStoreTests(unittest.TestCase):
    def test_missing_owner_projection_is_typed_absence_without_fixture_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RealSourceStore(Path(tmp), REGISTRY)
            value = store.projection("C2E")
            self.assertEqual("NOT_MATERIALIZED", value["availability"])
            self.assertEqual("UPSTREAM_OWNER_READ_PROJECTION_UNAVAILABLE", value["missingness"]["reason_codes"][0])
            self.assertEqual(0, store.resource_reads)

    def test_contract_enforces_owner_identity_chronology_missingness_and_read_only_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = projection("C2", "src/ovc/opt_b/c2_vnext", {"state_id": "C2.TEST"})
            (root / "c2.json").write_text(json.dumps(good), encoding="utf-8")
            store = RealSourceStore(root, REGISTRY)
            self.assertEqual("AVAILABLE", store.projection("C2")["availability"])
            bad = dict(good); bad["owner_namespace"] = "src/ovc/opt_b/c1"
            (root / "c2.json").write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(SourceConflict): store.projection("C2")
            bad = projection("C2", "src/ovc/opt_b/c2_vnext", {"state_id": "C2.TEST"}, denominator=2, missing=1); bad["missingness"]["denominator"] = 3
            (root / "c2.json").write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ContractError): store.projection("C2")

    def test_c2_is_independent_when_c2e_is_unavailable_and_snapshot_never_reconstructs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "c2.json").write_text(json.dumps(projection("C2", "src/ovc/opt_b/c2_vnext", {"state_id": "C2.TEST"})), encoding="utf-8")
            store = RealSourceStore(root, REGISTRY)
            snapshot = store.investigate_snapshot()
            self.assertEqual("AVAILABLE", snapshot["payload"]["structure"]["c2"]["availability"])
            self.assertEqual("NOT_MATERIALIZED", snapshot["payload"]["structure"]["c2e"]["availability"])
            self.assertEqual("PROHIBITED", snapshot["payload"]["structure"]["c2_5"]["event_synthesis"])
            self.assertEqual("PROHIBITED", snapshot["payload"]["structure"]["c3"]["semantic_synthesis"])
            self.assertEqual("PRESENTATION_ONLY_NO_SCIENTIFIC_SYNTHESIS", snapshot["real_source_banner"]["composition_policy"])

    @unittest.skipIf(importlib.util.find_spec("fastapi") is None, "FastAPI dependency not installed")
    def test_real_api_is_explicit_read_only_and_validation_denies_before_source_read(self):
        from fastapi.testclient import TestClient
        from apps.research_api.app import create_app
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            market = projection("MARKET", "src/ovc/opt_a", {"bars": [{"timestamp": "2024-01-01T00:00:00Z", "open": 1.0}, {"timestamp": "2024-01-01T01:00:00Z", "open": 1.1}]}, denominator=2)
            c1 = projection("C1", "src/ovc/opt_b/c1", {"record_id": "C1.TEST"})
            c2 = projection("C2", "src/ovc/opt_b/c2_vnext", {"state_id": "C2.TEST"})
            c2e = projection("C2E", "src/ovc/opt_b/c2e_v2", {"episodes": []}, denominator=0)
            for filename, value in (("market.json", market), ("c1.json", c1), ("c2.json", c2), ("c2e.json", c2e)):
                (root / filename).write_text(json.dumps(value), encoding="utf-8")
            app = create_app(source_mode="REAL", real_source_root=root, real_source_bindings=REGISTRY)
            client = TestClient(app)
            real_store = app.state.real_source_store
            before = real_store.resource_reads
            denied = client.get("/api/v1/c2/state?role=VALIDATION")
            self.assertEqual(403, denied.status_code)
            self.assertEqual(before, real_store.resource_reads)
            response = client.get("/api/v1/c2/state")
            self.assertEqual(200, response.status_code)
            body = response.json()
            self.assertEqual("REAL_SOURCE_READ_ONLY", body["real_source_banner"]["mode"])
            self.assertEqual("PROHIBITED", body["real_source_banner"]["fixture_fallback"])
            self.assertEqual("C2.TEST", body["payload"]["state_id"])
            market_body = client.get("/api/v1/market/window?limit=1").json()
            self.assertEqual(1, len(market_body["payload"]))
            self.assertNotIn("fixture_banner", body)


if __name__ == "__main__":
    unittest.main()
