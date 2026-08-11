from __future__ import annotations
import json,unittest
from pathlib import Path
from srfd._current_pointer_compat import assert_lawful_v10_pointer
ROOT=Path(__file__).resolve().parents[2]; FAILURE=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-0/SRFDI_WP10_V10_EXECUTION_OUTPUT_CONTRACT_FAILURE.json'; QA=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-0/SRFDI_WP10_V10_EXECUTION_OUTPUT_CONTRACT_FAILURE_QA.json'; POINTER=ROOT/'registries/implementation/srfd/CURRENT_STATE_POINTER.json'
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c): c.f=json.loads(FAILURE.read_text()); c.q=json.loads(QA.read_text()); c.p=json.loads(POINTER.read_text())
 def test_failure_preserved(self): self.assertEqual('BLOCKED_PRESERVED_NOT_COMPLETED',self.f['status']); self.assertEqual('WORK_UNIT_DISPATCH_OUTPUT_CONTRACT_CORRUPTION',self.f['failure_class'])
 def test_corruption_range(self): e=self.f['checkpoint_evidence']; self.assertEqual(285,e['first_invalid_sequence']); self.assertEqual(338,e['last_invalid_sequence']); self.assertEqual(54,e['invalid_configuration_unit_count']); self.assertEqual('FORBIDDEN',e['same_run_resume'])
 def test_hardening(self): self.assertEqual('PASS_2020_OF_2020',self.f['hardening_resolution']['rehearsal_status']); self.assertEqual('PASS',self.f['hardening_resolution']['strict_output_contracts'])
 def test_current_pointer_preserves_lineage(self): self.assertTrue(assert_lawful_v10_pointer(self,self.p)); self.assertEqual('BLOCKED_DISPATCH_OUTPUT_CONTRACT_FAILURE_PRESERVED',self.p['wp10_v1_0_execution_route']); self.assertEqual('DENIED',self.p['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',self.p['validation_2025'])
