from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "research_console_vnext" / "console_pack_v0_1"
REGISTRY = ROOT / "registries" / "research_console_vnext" / "research_native" / "wp4a_investigate_binding_candidates_v1.json"
ROUTES = ROOT / "registries" / "research_console_vnext" / "research_native" / "route_registry_v2.json"
STATE = ROOT / "registries" / "implementation" / "research_console_vnext" / "OVC_RCN_RN_STATE_v0_2.json"

def load(path: Path): return json.loads(path.read_text(encoding="utf-8"))

class ResearchNativeWP4APreparationTests(unittest.TestCase):
    def test_fixture_composer_preserves_c1_c2_and_fails_honest_for_absent_upper_layers(self):
        from ovc.console_vnext.application.investigate_preparation import build_fixture_investigate_snapshot
        market=load(FIXTURES/"market.json"); structure=load(FIXTURES/"structure.json"); preparation=load(FIXTURES/"investigate_preparation.json")
        snapshot=build_fixture_investigate_snapshot(market=market,structure=structure,preparation=preparation)
        self.assertEqual("FIXTURE_ONLY_G4_PREPARATION",snapshot["mode"]); self.assertEqual("NONE",snapshot["authority_effect"]); self.assertEqual("DENIED_PENDING_RCN_RN_G4",snapshot["real_source_presentation"])
        self.assertEqual(structure["c1"],snapshot["translation"]["c1"]); self.assertEqual(structure["c2"],snapshot["structure"]["c2"])
        self.assertEqual("NOT_MATERIALIZED",snapshot["structure"]["c2e"]["availability"]); self.assertEqual("PROHIBITED",snapshot["structure"]["c2e"]["reconstruction"]); self.assertEqual([],snapshot["structure"]["c2e"]["episodes"]); self.assertEqual([],snapshot["structure"]["c2e"]["events"])
        self.assertEqual("NOT_MATERIALIZED",snapshot["structure"]["transitions"]["availability"]); self.assertEqual("PROHIBITED",snapshot["structure"]["transitions"]["synthesis"]); self.assertEqual([],snapshot["structure"]["transitions"]["items"])
        self.assertEqual(len(market["bars"]),snapshot["market_context"]["bar_count"]); self.assertEqual("OPTIONAL_CONTEXT_ONLY",snapshot["market_context"]["scientific_role"])
        for key in ("overall_state","winner_axis","confidence_score"): self.assertNotIn(key,snapshot["structure"]["c2"])

    def test_binding_candidates_are_declarations_not_real_source_bindings(self):
        registry=load(REGISTRY); self.assertEqual("PREPARATION_ONLY",registry["status"]); self.assertEqual("NONE",registry["authority_effect"]); self.assertEqual("RCN-RN-G4",registry["first_real_source_presentation_gate"])
        for candidate in registry["candidates"]:
            self.assertEqual("PREPARED_NOT_BOUND",candidate["activation_state"]); self.assertFalse(candidate["real_source_presented"]); self.assertEqual("NONE",candidate["authority_effect"]); self.assertEqual("RCN-RN-G4",candidate["gate_required"])

    def test_route_and_programme_state_preserve_g4_boundary(self):
        routes=load(ROUTES); self.assertEqual("GET_ONLY",routes["transport"]); self.assertIn("/investigate/snapshot",routes["domains"]["INVESTIGATE"]); self.assertEqual("DENIED_UNTIL_RCN_RN_G4",routes["real_source_exposure"]); self.assertEqual("PREPARED_NOT_BOUND",routes["wp4a_preparation"]["binding_state"])
        state=load(STATE); self.assertTrue(state["packet_id"].startswith("RCN-RN-WP4") or state["packet_id"]=="RCN-RN-G4"); self.assertEqual("FIXTURE_ONLY_LOCAL_READ_ONLY",state["current_authority"]); self.assertEqual("DENIED_UNTIL_RCN_RN_G4",state["real_source_routes"]); self.assertEqual("RCN-RN-G4_BEFORE_FIRST_REAL_SOURCE_PRESENTATION",state["stop_boundary"]); self.assertEqual("NONE",state["authority_delta"])

    @unittest.skipIf(importlib.util.find_spec("fastapi") is None,"FastAPI dependency not installed")
    def test_runtime_route_is_fixture_only_and_validation_denies_before_resource_reads(self):
        from fastapi.testclient import TestClient
        from apps.research_api.app import create_app
        app=create_app(); client=TestClient(app); store=app.state.fixture_store; before=store.resource_reads
        denied=client.get("/api/v1/investigate/snapshot?role=VALIDATION"); self.assertEqual(403,denied.status_code); self.assertEqual(before,store.resource_reads)
        body=client.get("/api/v1/investigate/snapshot").json(); self.assertEqual("SYNTHETIC_FIXTURE",body["fixture_banner"]["data_classification"]); self.assertEqual("NONE",body["fixture_banner"]["authority_effect"]); self.assertEqual("FIXTURE_ONLY_G4_PREPARATION",body["payload"]["mode"]); self.assertEqual("PROHIBITED",body["payload"]["structure"]["c2e"]["reconstruction"])

if __name__=="__main__": unittest.main()
