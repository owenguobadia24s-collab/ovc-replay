from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; FIX=ROOT/'fixtures/research_console_vnext/console_pack_v0_1/c3_preparation.json'; INV=ROOT/'registries/research_console_vnext/research_native/source_adapter_inventory_v2.json'; STATE=ROOT/'registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json'; ROUTES=ROOT/'registries/research_console_vnext/research_native/route_registry_v2.json'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
class WP4DC3Preparation(unittest.TestCase):
 def test_census_fixture_typed_absence(self):
  f=load(FIX); c=next(x for x in load(INV)['sources'] if x['capability_id']=='c3'); self.assertFalse(c['repository_materialized']); self.assertIsNone(c['source_path']); self.assertEqual(c['reason_code'],f['reason_code']); self.assertEqual([],f['nodes']); self.assertEqual([],f['edges']); self.assertEqual('PROHIBITED',f['semantic_synthesis']); self.assertFalse(f['runtime_owner_materialized']); self.assertEqual('RCN-RN-G4',f['gate_required'])
 def test_route_state_g4_boundary(self):
  r=load(ROUTES); s=load(STATE); self.assertEqual('GET_ONLY',r['transport']); self.assertIn('/c3/graph',r['domains']['INVESTIGATE']); self.assertFalse(r['wp4d_preparation']['runtime_owner_materialized']); self.assertEqual('PROHIBITED',r['wp4d_preparation']['semantic_synthesis']); self.assertEqual('RCN-RN-WP4D',s['packet_id']); self.assertEqual('NONE',s['authority_delta']); self.assertEqual('DENIED_UNTIL_RCN_RN_G4',s['real_source_routes'])
 @unittest.skipIf(importlib.util.find_spec('fastapi') is None,'FastAPI dependency not installed')
 def test_runtime_empty_and_validation_denied_before_read(self):
  from fastapi.testclient import TestClient
  from apps.research_api.app import create_app
  app=create_app(); client=TestClient(app); before=app.state.fixture_store.resource_reads; denied=client.get('/api/v1/c3/graph?role=VALIDATION'); self.assertEqual(403,denied.status_code); self.assertEqual(before,app.state.fixture_store.resource_reads); p=client.get('/api/v1/c3/graph').json()['payload']; self.assertEqual('NOT_MATERIALIZED',p['availability']); self.assertEqual([],p['nodes']); self.assertEqual([],p['edges']); self.assertEqual('PROHIBITED',p['semantic_synthesis']); self.assertFalse(p['runtime_owner_materialized']); self.assertEqual('DENIED_PENDING_RCN_RN_G4',p['real_source_presentation'])
if __name__=='__main__': unittest.main()
