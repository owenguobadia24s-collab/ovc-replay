from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; FIX=ROOT/'fixtures/research_console_vnext/console_pack_v0_1/c2p_preparation.json'; INV=ROOT/'registries/research_console_vnext/research_native/source_adapter_inventory_v2.json'; STATE=ROOT/'registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json'; ROUTES=ROOT/'registries/research_console_vnext/research_native/route_registry_v2.json'; C2P_STATE=ROOT/'registries/implementation/c2p_v0_2/OVC_C2P2_STATE_v0_1.json'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
class WP4BC2PPreparation(unittest.TestCase):
 def test_census_and_fixture_distinguish_synthetic_subsystem_from_runtime_owner(self):
  f=load(FIX); c=next(x for x in load(INV)['sources'] if x['capability_id']=='c2p'); upstream=load(C2P_STATE)
  self.assertTrue(c['repository_materialized']); self.assertEqual('src/ovc/opt_b/c2p_v0_2',c['source_path']); self.assertTrue(c['synthetic_fixture_subsystem_materialized']); self.assertEqual('C2P2-WP2',c['latest_packet']); self.assertFalse(c['runtime_owner_materialized']); self.assertEqual('NONE',c['active_source_authority']); self.assertEqual('SYNTHETIC_CANDIDATE_TRACKLET_SUBSYSTEM_PRESENT_RUNTIME_AND_REAL_SOURCE_AUTHORITY_NONE',c['reason_code']); self.assertEqual('NONE',upstream['authority']['c2p_runtime']); self.assertEqual('DENIED_FUTURE_C2P2_RS0',upstream['authority']['real_source_replay']); self.assertEqual([],f['objects']); self.assertFalse(f['runtime_owner_materialized']); self.assertEqual('RCN-RN-G4',f['gate_required'])
 def test_route_and_state_keep_c2p_excluded_after_g4_pass(self):
  r=load(ROUTES); s=load(STATE); self.assertEqual('GET_ONLY',r['transport']); self.assertIn('/c2p/objects',r['domains']['INVESTIGATE']); self.assertFalse(r['wp4b_preparation']['runtime_owner_materialized']); self.assertTrue(r['wp4b_preparation']['synthetic_fixture_subsystem_materialized']); self.assertEqual('C2P2-WP2',r['wp4b_preparation']['latest_packet']); self.assertEqual('SYNTHETIC_CANDIDATE_TRACKLET_SUBSYSTEM_PRESENT_RUNTIME_AND_REAL_SOURCE_AUTHORITY_NONE',r['wp4b_preparation']['reason_code']); self.assertEqual('APPROVED',s['status']); self.assertEqual('SATISFIED_OPERATOR_PASS',s['authority_required']); self.assertEqual('FIRST_LAWFUL_REAL_SOURCE_INVESTIGATE_PRESENTATION_APPROVED',s['authority_delta']); self.assertIn('OTHERS_DENIED',s['real_source_routes']); self.assertIn('G4_APPROVED_READ_ONLY',s['current_authority']); self.assertIsNotNone(s['decision_record'])
 @unittest.skipIf(importlib.util.find_spec('fastapi') is None,'FastAPI dependency not installed')
 def test_runtime_is_empty_typed_absence_and_validation_denies_before_read(self):
  from fastapi.testclient import TestClient
  from apps.research_api.app import create_app
  app=create_app(); client=TestClient(app); before=app.state.fixture_store.resource_reads; denied=client.get('/api/v1/c2p/objects?role=VALIDATION'); self.assertEqual(403,denied.status_code); self.assertEqual(before,app.state.fixture_store.resource_reads); p=client.get('/api/v1/c2p/objects').json()['payload']; self.assertEqual('NOT_MATERIALIZED',p['availability']); self.assertEqual([],p['objects']); self.assertFalse(p['runtime_owner_materialized']); self.assertEqual('DENIED_PENDING_RCN_RN_G4',p['real_source_presentation'])
if __name__=='__main__': unittest.main()
