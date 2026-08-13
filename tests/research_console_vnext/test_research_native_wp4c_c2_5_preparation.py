from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "fixtures/research_console_vnext/console_pack_v0_1/c2_5_preparation.json"
INV = ROOT / "registries/research_console_vnext/research_native/source_adapter_inventory_v2.json"
STATE = ROOT / "registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json"
ROUTES = ROOT / "registries/research_console_vnext/research_native/route_registry_v2.json"
POST_G4_DECISION = ROOT / "artifacts/research_console_vnext/pvs3/RCN_RN_POST_G4_SOURCE_BINDING_DECISION.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class WP4CC25Preparation(unittest.TestCase):
    def test_census_fixture_typed_absence(self):
        fixture = load(FIX)
        census = next(
            row for row in load(INV)["sources"] if row["capability_id"] == "c2_5"
        )
        self.assertFalse(census["repository_materialized"])
        self.assertIsNone(census["source_path"])
        self.assertEqual(census["reason_code"], fixture["reason_code"])
        self.assertEqual([], fixture["events"])
        self.assertEqual("PROHIBITED", fixture["event_synthesis"])
        self.assertFalse(fixture["runtime_owner_materialized"])

    def test_c2_5_exclusion_is_preserved_across_post_g4_and_wp5a_progression(self):
        routes = load(ROUTES)
        historical = load(POST_G4_DECISION)
        state = load(STATE)

        self.assertEqual("GET_ONLY", routes["transport"])
        self.assertIn("/c2-5/events", routes["domains"]["INVESTIGATE"])
        self.assertFalse(routes["wp4c_preparation"]["runtime_owner_materialized"])
        self.assertEqual(
            "PROHIBITED",
            routes["wp4c_preparation"]["event_synthesis"],
        )
        self.assertNotIn("C2_5", routes["post_g4_binding"]["capabilities"])

        self.assertEqual(
            historical["packet_id"],
            "RCN-RN-POST-G4-SOURCE-BINDING",
        )
        self.assertEqual(historical["decision"], "PASS")
        self.assertEqual(historical["authority_delta"], "NONE")
        self.assertEqual(historical["next_packet"], "RCN-RN-WP5A")

        self.assertEqual(state["packet_id"], "RCN-RN-WP5A")
        self.assertEqual(state["status"], "READY")
        self.assertEqual(state["authority_delta"], "NONE")
        self.assertEqual(
            state["decision"],
            "GOVERNING_ARTIFACT_MATERIALISATION_COMPLETED_AUTHORITY_UNCHANGED",
        )
        self.assertIn("OTHERS_DENIED", state["real_source_routes"])

    @unittest.skipIf(
        importlib.util.find_spec("fastapi") is None,
        "FastAPI dependency not installed",
    )
    def test_runtime_empty_and_validation_denied_before_read(self):
        from fastapi.testclient import TestClient
        from apps.research_api.app import create_app

        app = create_app()
        client = TestClient(app)
        before = app.state.fixture_store.resource_reads
        denied = client.get("/api/v1/c2-5/events?role=VALIDATION")
        self.assertEqual(403, denied.status_code)
        self.assertEqual(before, app.state.fixture_store.resource_reads)
        payload = client.get("/api/v1/c2-5/events").json()["payload"]
        self.assertEqual("NOT_MATERIALIZED", payload["availability"])
        self.assertEqual([], payload["events"])
        self.assertEqual("PROHIBITED", payload["event_synthesis"])


if __name__ == "__main__":
    unittest.main()
