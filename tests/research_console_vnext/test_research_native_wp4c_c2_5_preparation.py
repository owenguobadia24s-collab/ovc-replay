from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; FIX=ROOT/'fixtures/research_console_vnext/console_pack_v0_1/c2_5_preparation.json'; INV=ROOT/'registries/research_console_vnext/research_native/source_adapter_inventory_v2.json'; STATE=ROOT/'registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json'; ROUTES=ROOT/'registries/research_console_vnext/research_native/route_registry_v2.json'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
class WP4CC25Preparation(unittest.TestCase):
 def test_census_fixture_typed_absence(self):
  f=load(FIX); c=next(x for x in load(INV)['sources'] if x['capability_id']=='c2_5'); self.assertFalse(c['repository_materialized']); self.assertIsNone(c['source_path']); self.assertEqual(c['reason_code'],f['reason_code']); self.assertEqual([],f['events']); self.assertEqual('PROHIBITED',f['event_synthesis']); self.assertFalse(f['runtime_owner_materialized']); self.assertEqual('RCN-RN-G4',f['gate_required'])
 def test_route_state_g4_boundary(self):
  r=load(ROUTES); s=load(STATE); self.assertEqual('GET_ONLY',r['transport']); self.assertIn('/c2-5/events',r['domains']['INVESTIGATE']); self.assertFalse(r['wp4c_preparation']['runtime_owner_materialized']); self.assertEqual('PROHIBITED',r['wp4c_preparation']['event_synthesis']); self.assertTrue(s['packet_id'].startswith('RCN-RN-WP4') or s['packet_id']=='RCN-RN-G4'); self.assertEqual('DENIED_UNTIL_RCN_RN_G4',s['real_source_routes']); self.assertEqual('FIXTURE_ONLY_LOCAL_READ_ONLY',s['current_authority'])
  if s['packet_id']=='RCN-RN-G4': self.assertEqual('GATE_READY',s['status']); self.assertEqual('OPERATOR_REQUIRED',s['authority_required']); self.assertEqual('PROPOSED_FIRST_LAWFUL_REAL_SOURCE_INVESTIGATE_PRESENTATION',s['authority_delta']); self.assertIsNone(s['decision_record'])
  else: self.assertEqual('NONE',s['authority_delta'])
 @unittest.skipIf(importlib.util.find_spec('fastapi') is None,'FastAPI dependency not installed')
 def test_runtime_empty_and_validation_denied_before_read(self):
  from fastapi.testclient import TestClient
  from apps.research_api.app import create_app
  app=create_app(); client=TestClient(app); before=app.state.fixture_store.resource_reads; denied=client.get('/api/v1/c2-5/events?role=VALIDATION'); self.assertEqual(403,denied.status_code); self.assertEqual(before,app.state.fixture_store.resource_reads); p=client.get('/api/v1/c2-5/events').json()['payload']; self.assertEqual('NOT_MATERIALIZED',p['availability']); self.assertEqual([],p['events']); self.assertEqual('PROHIBITED',p['event_synthesis']); self.assertFalse(p['runtime_owner_materialized']); self.assertEqual('DENIED_PENDING_RCN_RN_G4',p['real_source_presentation'])
if __name__=='__main__': unittest.main()
