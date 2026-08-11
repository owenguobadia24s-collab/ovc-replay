from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class T(unittest.TestCase):
    def test_visual_constitution(self):
        w = (ROOT / 'apps/research_console_vnext/src/researchNative/WorkbenchFrame.tsx').read_text()
        c = (ROOT / 'apps/research_console_vnext/src/researchNative/researchNative.css').read_text()
        for x in ['rnWorkbenchGrid', 'rnContextNavigator', 'rnCanvas', 'rnInspector', 'rnDock', 'data-density="analytical"', 'EvidencePassport', 'SemanticRiskGallery']:
            self.assertIn(x, w)
        for x in ['grid-template-columns:minmax(210px,18%)', 'grid-template-rows:minmax(0,1fr) 116px', 'rnSemanticLayout', 'rnMatrixInstrument', 'rnProofInstrument', 'rnSemanticMiniRail']:
            self.assertIn(x, c)
        self.assertNotIn('FixtureChart', w)

    def test_semantic_risk_is_instrument_grade(self):
        s = (ROOT / 'apps/research_console_vnext/src/researchNative/SemanticRiskPrototypes.tsx').read_text()
        for x in ['MatrixView', 'ProofTimeline', 'AstRenderer', 'BoundedGraph', 'Definition AST', 'First-valid time', '50,000', 'expansion_handle', 'display_projection', 'NO COMPOSITE WINNER']:
            self.assertIn(x, s)
        self.assertNotIn('Math.random', s)
        self.assertNotIn('fetch(', s)


if __name__ == '__main__':
    unittest.main()
