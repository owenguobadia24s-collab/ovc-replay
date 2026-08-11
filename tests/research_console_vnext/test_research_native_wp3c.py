from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_semantic_risk_components(self):
  s=(ROOT/'apps/research_console_vnext/src/researchNative/SemanticRiskPrototypes.tsx').read_text()
  for x in ['MatrixView','ProofTimeline','AstRenderer','BoundedGraph','50,000','expansion_handle','Definition AST','First-valid time','NOT_EVALUABLE','display_projection']: self.assertIn(x,s)
  self.assertNotIn('Math.random',s); self.assertNotIn('fetch(',s)
 def test_gallery_is_in_primary_canvas(self):
  s=(ROOT/'apps/research_console_vnext/src/researchNative/WorkbenchFrame.tsx').read_text(); self.assertIn('SemanticRiskGallery',s); self.assertIn('SYNTHETIC_FIXTURE',s)
if __name__=='__main__':unittest.main()
