from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_workbench_contract(self):
  s=(ROOT/'apps/research_console_vnext/src/researchNative/WorkbenchFrame.tsx').read_text();
  for x in ['rnFrame','rnNav','rnCanvas','rnInspector','rnDock','EvidencePassport','AuthorityBadge','AvailabilityBadge','QAStatus','ReasonCode','ChronologyChip','DegradedState']: self.assertIn(x,s)
  self.assertNotIn('FixtureChart',s)
 def test_router_uses_research_native_frame(self):
  s=(ROOT/'apps/research_console_vnext/src/app/router.tsx').read_text(); self.assertIn('WorkbenchFrame',s); self.assertNotIn('FoundationWorkspace',s)
if __name__=='__main__':unittest.main()
