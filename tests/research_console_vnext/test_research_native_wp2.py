from __future__ import annotations
import json, unittest
from pathlib import Path
from fastapi.testclient import TestClient
from apps.research_api.app import create_app
ROOT=Path(__file__).resolve().parents[2]
class ResearchNativeWP2Tests(unittest.TestCase):
 def test_four_domain_registry_get_only(self):
  v=json.loads((ROOT/'registries/research_console_vnext/research_native/route_registry_v2.json').read_text())
  self.assertEqual(set(v['domains']),{'INVESTIGATE','RESEARCH','EVIDENCE','CONTROL'}); self.assertEqual(v['transport'],'GET_ONLY'); self.assertEqual(v['mutation_disposition'],'DENIED')
 def test_adv_catalogue_is_exact_28_and_non_evidentiary(self):
  v=json.loads((ROOT/'fixtures/research_console_vnext/research_native/adv_catalogue_v1.json').read_text())
  self.assertEqual([x['id'] for x in v['cases']],[f'ADV-{i:02d}' for i in range(1,29)]); self.assertIn('NON_EVIDENTIARY',v['authority'])
 def test_transport_rejects_mutation(self):
  c=TestClient(create_app()); r=c.post('/api/v1/c2/state'); self.assertEqual(r.status_code,405); self.assertEqual(r.json()['reason_code'],'MUTATION_METHOD_DENIED')
if __name__=='__main__': unittest.main()
