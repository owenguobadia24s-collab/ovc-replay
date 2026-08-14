from __future__ import annotations
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
class SIQPDCCompatibilityTests(unittest.TestCase):
    def test_current_pdc_stable_main_guards_remain_present(self):
        text=(ROOT/"tools/ci/ovc_run_with_main_lease.py").read_text(encoding="utf-8")
        self.assertIn("OVC_BASE_MOVED_BEFORE_READINESS",text)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS",text)
        self.assertIn("OVC_REQUIRED_ASSURANCE_LEASE_INVALIDATED",text)
        self.assertIn("_terminate_process_group(process)",text)
    def test_constitution_keeps_parallel_merge_false(self):
        text=(ROOT/"contracts/development/v0_4/OVC_SERIALIZED_INTEGRATION_QUEUE_CONSTITUTION_v0_1.md").read_text(encoding="utf-8")
        self.assertIn("`parallel_merge` remains `false`",text)
        self.assertIn("BASE_INDEPENDENT",text)
        self.assertIn("BASE_SENSITIVE",text)
if __name__=="__main__": unittest.main()
