from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from ovc.research_operations.mta.marker_population_audit import MTAWP5AuditError,validate_reference
ROOT=Path(__file__).resolve().parents[3]
REF=json.loads((ROOT/'docs/releases/market-translation-audit-v0-2/mta-g5/MTA_WP5_MARKER_POPULATION_AUDIT_REFERENCE.json').read_text())
class Tests(unittest.TestCase):
 def test_pass(self): self.assertEqual(validate_reference(REF)['status'],'PASS')
 def test_denominator_blocks(self):
  v=copy.deepcopy(REF);v['population']['eligible_windows']=7115
  with self.assertRaises(MTAWP5AuditError):validate_reference(v)
 def test_rule_accounting_blocks(self):
  v=copy.deepcopy(REF);v['rule_counts']['BREACH_ACTIVE']['fired']+=1
  with self.assertRaises(MTAWP5AuditError):validate_reference(v)
 def test_authority_escape_blocks(self):
  v=copy.deepcopy(REF);v['marker_semantic_promotion']='APPROVED'
  with self.assertRaises(MTAWP5AuditError):validate_reference(v)
if __name__=='__main__':unittest.main()
