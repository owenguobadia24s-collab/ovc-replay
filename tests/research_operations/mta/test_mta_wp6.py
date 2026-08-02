from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from ovc.research_operations.mta.overlap_independence_audit import MTAWP6AuditError,validate_reference
ROOT=Path(__file__).resolve().parents[3]
REF=json.loads((ROOT/'docs/releases/market-translation-audit-v0-2/mta-g6/MTA_WP6_OVERLAP_INDEPENDENCE_AUDIT_REFERENCE.json').read_text())
class Tests(unittest.TestCase):
 def test_pass(self):self.assertEqual(validate_reference(REF)['status'],'PASS')
 def test_occurrence_blocks(self):
  v=copy.deepcopy(REF);v['occurrence_count']=1778
  with self.assertRaises(MTAWP6AuditError):validate_reference(v)
 def test_histogram_blocks(self):
  v=copy.deepcopy(REF);v['variants_summary']['PRIMARY_OVERLAP_PLUS_1']['cluster_size_histogram']['13']=2
  with self.assertRaises(MTAWP6AuditError):validate_reference(v)
 def test_authority_blocks(self):
  v=copy.deepcopy(REF);v['cluster_semantic_promotion']='APPROVED'
  with self.assertRaises(MTAWP6AuditError):validate_reference(v)
if __name__=='__main__':unittest.main()
