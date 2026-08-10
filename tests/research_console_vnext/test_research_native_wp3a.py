from __future__ import annotations
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class ResearchNativeWP3ATests(unittest.TestCase):
 def test_reused_foundation_exists(self):
  v=json.loads((ROOT/'artifacts/research_console_vnext/research_native/RCN_RN_WP3A_CONFORMANCE.json').read_text())
  for p in v['reused'].values(): self.assertTrue((ROOT/p).exists(),p)
 def test_tooling_is_strict_react_vite_tanstack_generated(self):
  p=json.loads((ROOT/'apps/research_console_vnext/package.json').read_text())
  self.assertIn('typecheck',p['scripts']); self.assertIn('@tanstack/react-query',p['dependencies']); self.assertIn('react',p['dependencies']); self.assertIn('vite',p['devDependencies'])
 def test_chart_is_not_product_acceptance_dependency(self):
  v=json.loads((ROOT/'artifacts/research_console_vnext/research_native/RCN_RN_WP3A_CONFORMANCE.json').read_text()); self.assertEqual(v['chart_first_assumption'],'NOT_REQUIRED_BY_V0_2_FOUNDATION'); self.assertEqual(v['real_source_exposure'],'DENIED')
if __name__=='__main__': unittest.main()
