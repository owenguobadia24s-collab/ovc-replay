from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "fixtures/research_console_vnext/console_pack_v0_1/c3_preparation.json"
MANIFEST = ROOT / "fixtures/research_console_vnext/console_pack_v0_1/manifest.json"
OPENAPI = ROOT / "fixtures/research_console_vnext/console_pack_v0_1/openapi_snapshot_v1.json"
INV = ROOT / "registries/research_console_vnext/research_native/source_adapter_inventory_v2.json"
STATE = ROOT / "registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json"
ROUTES = ROOT / "registries/research_console_vnext/research_native/route_registry_v2.json"
SCHEMA = ROOT / "schemas/research_console_vnext/c3_preparation_v1.schema.json"
ADMISSION = ROOT / "artifacts/research_console_vnext/pvs3/PVS3_PHASE3_ADMISSION_RECORD.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class WP4DC3Preparation(unittest.TestCase):
    def test_census_and_fixture_preserve_typed_owner_absence(self):
        fixture = load(FIX)
        census = next(item for item in load(INV)["sources"] if item["capability_id"] == "c3")
        self.assertFalse(census["repository_materialized"])
        self.assertIsNone(census["source_path"])
        self.assertEqual("TYPED_DEGRADED_STATE", census["console_binding"])
        self.assertEqual(census["reason_code"], fixture["reason_code"])
        self.assertEqual("NOT_MATERIALIZED", fixture["availability"])
        self.assertFalse(fixture["runtime_owner_materialized"])
        self.assertEqual("PREPARED_NOT_BOUND", fixture["binding_state"])
        self.assertEqual([], fixture["nodes"])
        self.assertEqual([], fixture["edges"])
        self.assertEqual("PROHIBITED", fixture["semantic_synthesis"])
        self.assertEqual("NO_C2_C2E_C2_5_SUBSTITUTION", fixture["substitution_policy"])
        self.assertEqual("NONE", fixture["authority_effect"])
        self.assertEqual("RCN-RN-G4", fixture["gate_required"])

    def test_schema_manifest_route_and_openapi_are_exactly_fixture_only(self):
        schema = load(SCHEMA)
        manifest = load(MANIFEST)
        routes = load(ROUTES)
        openapi = load(OPENAPI)

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(False, schema["properties"]["runtime_owner_materialized"]["const"])
        self.assertEqual(0, schema["properties"]["nodes"]["maxItems"])
        self.assertEqual(0, schema["properties"]["edges"]["maxItems"])
        self.assertEqual("PROHIBITED", schema["properties"]["semantic_synthesis"]["const"])
        self.assertEqual("NONE", schema["properties"]["authority_effect"]["const"])
        self.assertEqual("RCN-RN-G4", schema["properties"]["gate_required"]["const"])

        self.assertIn("RCN_RN_WP4D_C3_PREPARATION_CONTRACT_v1", manifest["source_identity"]["contract_ids"])
        self.assertIn("c3_preparation_v1", manifest["source_identity"]["schema_ids"])
        self.assertEqual("c3_preparation.json", manifest["resources"]["c3_preparation"])
        self.assertEqual("FIXTURE_ONLY", manifest["mode"])
        self.assertEqual("NONE", manifest["authority_effect"])

        self.assertEqual("GET_ONLY", routes["transport"])
        self.assertEqual("DENIED", routes["mutation_disposition"])
        self.assertEqual(["POST", "PUT", "PATCH", "DELETE"], routes["mutation_methods"])
        self.assertEqual("DENIED_UNTIL_RCN_RN_G4", routes["real_source_exposure"])
        self.assertIn("/c3/graph", routes["domains"]["INVESTIGATE"])
        self.assertFalse(routes["wp4d_preparation"]["runtime_owner_materialized"])
        self.assertEqual("PREPARED_NOT_BOUND", routes["wp4d_preparation"]["binding_state"])
        self.assertEqual("PROHIBITED", routes["wp4d_preparation"]["semantic_synthesis"])

        self.assertEqual(["get"], openapi["paths"]["/api/v1/c3/graph"]["methods"])
        self.assertEqual("FIXTURE_ONLY", openapi["mode"])
        self.assertEqual("NONE", openapi["authority_effect"])
        for path, definition in openapi["paths"].items():
            self.assertEqual(["get"], definition["methods"], path)

    def test_phase3_admission_does_not_imply_g4_authority(self):
        admission = load(ADMISSION)
        state = load(STATE)
        self.assertEqual("Begin Phase 3", admission["operator_instruction"])
        self.assertTrue(admission["g4_decision_not_implied_by_phase_admission"])
        self.assertEqual("NONE", admission["authority_delta_before_g4"])
        self.assertEqual("DENIED_UNTIL_RCN_RN_G4", admission["real_source_presentation"])
        self.assertEqual(611, admission["historical_wp4d_pr"])
        self.assertEqual("RCN-RN-WP4D", state["packet_id"])
        self.assertEqual("RUNNING", state["status"])
        self.assertEqual("NONE", state["authority_delta"])
        self.assertEqual("DENIED_UNTIL_RCN_RN_G4", state["real_source_routes"])

    @unittest.skipIf(importlib.util.find_spec("fastapi") is None, "FastAPI dependency not installed")
    def test_runtime_is_empty_typed_absence_and_validation_is_denied_before_read(self):
        from fastapi.testclient import TestClient
        from apps.research_api.app import create_app

        app = create_app()
        client = TestClient(app)
        before = app.state.fixture_store.resource_reads
        denied = client.get("/api/v1/c3/graph?role=VALIDATION")
        self.assertEqual(403, denied.status_code)
        self.assertEqual(before, app.state.fixture_store.resource_reads)

        response = client.get("/api/v1/c3/graph")
        self.assertEqual(200, response.status_code)
        envelope = response.json()
        self.assertEqual("C3", envelope["capability"]["capability_id"])
        self.assertEqual("NONE", envelope["capability"]["authority_effect"])
        payload = envelope["payload"]
        self.assertEqual("NOT_MATERIALIZED", payload["availability"])
        self.assertFalse(payload["runtime_owner_materialized"])
        self.assertEqual([], payload["nodes"])
        self.assertEqual([], payload["edges"])
        self.assertEqual("PROHIBITED", payload["semantic_synthesis"])
        self.assertEqual("DENIED_PENDING_RCN_RN_G4", payload["real_source_presentation"])


if __name__ == "__main__":
    unittest.main()
