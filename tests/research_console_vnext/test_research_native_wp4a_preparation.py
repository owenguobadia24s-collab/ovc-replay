from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; FIXTURES=ROOT/'fixtures/research_console_vnext/console_pack_v0_1'; REGISTRY=ROOT/'registries/research_console_vnext/research_native/wp4a_investigate_binding_candidates_v1.json'; ROUTES=ROOT/'registries/research_console_vnext/research_native/route_registry_v2.json'; STATE=ROOT/'registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class ResearchNativeWP4APreparationTests(unittest.TestCase):
 def test_fixture_composer_preserves_c1_c2_and_fails_honest_for_absent_upper_layers(self):
  from ovc.console_vnext.application.investigate_preparation import build_fixture_investigate_snapshot
  market=load(FIXTURES/'market.json'); structure=load(FIXTURES/'structure.json'); preparation=load(FIXTURES/'investigate_preparation.json'); snapshot=build_fixture_investigate_snapshot(market=market,structure=structure,preparation=preparation); self.assertEqual('FIXTURE_ONLY_G4_PREPARATION',snapshot['mode']); self.assertEqual('NONE',snapshot['authority_effect']); self.assertEqual(structure['c1'],snapshot['translation']['c1']); self.assertEqual(structure['c2'],snapshot['structure']['c2']); self.assertEqual('PROHIBITED',snapshot['structure']['c2e']['reconstruction']); self.assertEqual('PROHIBITED',snapshot['structure']['transitions']['synthesis'])
 def test_binding_candidates_remain_historical_preparation_declarations(self):
  registry=load(REGISTRY); self.assertEqual('PREPARATION_ONLY',registry['status']); self.assertEqual('NONE',registry['authority_effect']); self.assertEqual('RCN-RN-G4',registry['first_real_source_presentation_gate']); self.assertTrue(all(x['activation_state']=='PREPARED_NOT_BOUND' and not x['real_source_presented'] for x in registry['candidates']))
 def test_route_and_current_state_record_post_g4_binding_without_authority_widening(self):
  routes=load(ROUTES); state=load(STATE); self.assertEqual('GET_ONLY',routes['transport']); self.assertEqual('BOUND_EXPLICIT_MODE_MARKET_C1_C2_C2E',routes['real_source_exposure']); self.assertEqual('IMPLEMENTED_PENDING_QA',routes['post_g4_binding']['binding_state']); self.assertEqual('NONE',routes['post_g4_binding']['authority_delta']); self.assertEqual(['MARKET','C1','C2','C2E'],routes['post_g4_binding']['capabilities']); self.assertEqual('RCN-RN-POST-G4-SOURCE-BINDING',state['packet_id']); self.assertEqual('IMPLEMENTED',state['status']); self.assertEqual('AUTO_EXECUTABLE_WITHIN_G4_PASS',state['authority_required']); self.assertEqual('NONE',state['authority_delta']); self.assertIn('OTHERS_DENIED',state['real_source_routes'])
 @unittest.skipIf(importlib.util.find_spec('fastapi') is None,'FastAPI dependency not installed')
 def test_default_runtime_remains_explicit_fixture_and_validation_denies_before_resource_reads(self):
  from fastapi.testclient import TestClient
  from apps.research_api.app import create_app
  app=create_app(); client=TestClient(app); store=app.state.fixture_store; before=store.resource_reads; denied=client.get('/api/v1/investigate/snapshot?role=VALIDATION'); self.assertEqual(403,denied.status_code); self.assertEqual(before,store.resource_reads); body=client.get('/api/v1/investigate/snapshot').json(); self.assertEqual('SYNTHETIC_FIXTURE',body['fixture_banner']['data_classification']); self.assertEqual('FIXTURE_ONLY_G4_PREPARATION',body['payload']['mode'])
if __name__=='__main__': unittest.main()
