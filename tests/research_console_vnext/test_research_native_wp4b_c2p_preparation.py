from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "fixtures/research_console_vnext/console_pack_v0_1/c2p_preparation.json"
INV = ROOT / "registries/research_console_vnext/research_native/source_adapter_inventory_v2.json"
STATE = ROOT / "registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json"
ROUTES = ROOT / "registries/research_console_vnext/research_native/route_registry_v2.json"
C2P_STATE = ROOT / "registries/implementation/c2p_v0_2/OVC_C2P2_STATE_v0_1.json"
POST_G4 = ROOT / "artifacts/research_console_vnext/pvs3/RCN_RN_POST_G4_SOURCE_BINDING_MERGE_RECEIPT.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class WP4BC2PPreparation(unittest.TestCase):
    def test_census_and_fixture_distinguish_synthetic_subsystem_from_runtime_owner(self):
        fixture = load(FIX)
        census = next(row for row in load(INV)["sources"] if row["capability_id"] == "c2p")
        upstream = load(C2P_STATE)
        self.assertTrue(census["repository_materialized"])
        self.assertTrue(census["synthetic_fixture_subsystem_materialized"])
        self.assertFalse(census["runtime_owner_materialized"])
        self.assertEqual("NONE", census["active_source_authority"])
        self.assertEqual("DENIED", census["real_route"])
        self.assertEqual("NONE", upstream["authority"]["c2p_runtime"])
        self.assertEqual("DENIED_FUTURE_C2P2_RS0", upstream["authority"]["real_source_replay"])
        self.assertEqual([], fixture["objects"])

    def test_route_and_current_state_keep_c2p_excluded_after_historical_post_g4_pass(self):
        routes = load(ROUTES)
        historical = load(POST_G4)
        current = load(STATE)
        self.assertEqual("GET_ONLY", routes["transport"])
        self.assertIn("/c2p/objects", routes["domains"]["INVESTIGATE"])
        self.assertFalse(routes["wp4b_preparation"]["runtime_owner_materialized"])
        self.assertTrue(routes["wp4b_preparation"]["synthetic_fixture_subsystem_materialized"])
        self.assertNotIn("C2P", routes["post_g4_binding"]["capabilities"])

        self.assertEqual("RCN-RN-POST-G4-SOURCE-BINDING", historical["packet_id"])
        self.assertEqual("COMPLETED", historical["status"])
        self.assertEqual("PASS_DELEGATED_AUTO_RATIFICATION", historical["decision"])
        self.assertEqual("NONE", historical["authority_delta"])
        self.assertEqual(historical["authority_after_merge"], current["current_authority"])
        self.assertEqual(historical["real_source_routes"], current["real_source_routes"])
        self.assertEqual("NONE", current["authority_delta"])
        self.assertIn("OTHERS_DENIED", current["real_source_routes"])
        self.assertIn("G4_APPROVED_READ_ONLY", current["current_authority"])

    @unittest.skipIf(importlib.util.find_spec("fastapi") is None, "FastAPI dependency not installed")
    def test_runtime_is_empty_typed_absence_and_validation_denies_before_read(self):
        from fastapi.testclient import TestClient
        from apps.research_api.app import create_app

        app = create_app()
        client = TestClient(app)
        before = app.state.fixture_store.resource_reads
        denied = client.get("/api/v1/c2p/objects?role=VALIDATION")
        self.assertEqual(403, denied.status_code)
        self.assertEqual(before, app.state.fixture_store.resource_reads)
        payload = client.get("/api/v1/c2p/objects").json()["payload"]
        self.assertEqual("NOT_MATERIALIZED", payload["availability"])
        self.assertEqual([], payload["objects"])
        self.assertFalse(payload["runtime_owner_materialized"])


if __name__ == "__main__":
    unittest.main()
