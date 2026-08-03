from __future__ import annotations
import importlib.util,json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
V=ROOT/'scripts/development/v0_2/validate_da2_g1.py'; s=importlib.util.spec_from_file_location('v',V); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
class T(unittest.TestCase):
 def setUp(self): self.r=json.loads((ROOT/'registries/development/v0_2/OVC_DA2_WORKFLOW_ADMISSION_MODES_v0_1.json').read_text()); self.t=(ROOT/'.github/workflows/tests.yml').read_text(); self.o=(ROOT/'.github/workflows/ovc-tiered-tests.yml').read_text()
 def test_validator(self): self.assertEqual(m.main(),0)
 def test_closed_pr_admission(self): self.assertEqual(set(self.r['canonical_pull_request_workflows']),{'.github/workflows/tests.yml','.github/workflows/ovc-tiered-tests.yml'})
 def test_one_suite(self): self.assertEqual(self.t.count('python3 -m unittest discover -s tests -v'),1); self.assertNotIn('python3 -m unittest discover -s tests -v',self.o)
 def test_profiles(self):
  for x in ('FAST','PACKET','FINAL_HEAD','OVC merge readiness'): self.assertIn(x,self.o)
 def test_runtime_concurrency(self):
  for x in (self.t,self.o): self.assertIn('python-version: "3.11"',x); self.assertIn('cancel-in-progress: true',x)
 def test_inventory_method(self): self.assertEqual(self.r['inventory_method'],'ALL_WORKFLOW_FILES_SCANNED_AT_VALIDATION_TIME')
 def test_no_run_ids(self): self.assertNotIn('"run_id"',(ROOT/'docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_IMPLEMENTATION_PACKET.json').read_text())
 def test_fail_closed_ruleset(self):
  p=json.loads((ROOT/'docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_RULESET_MIGRATION_PACKET.json').read_text()); self.assertEqual(p['failure_result'],'BLOCK_PRESERVE_MIGRATION_AND_OLD_REQUIRED_CONTEXTS')
if __name__=='__main__': unittest.main()
