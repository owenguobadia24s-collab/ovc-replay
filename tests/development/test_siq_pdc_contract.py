from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SIQPDCCompatibilityTests(unittest.TestCase):
    def test_current_pdc_predecessor_guards_remain_present(self) -> None:
        text = (ROOT / "tools/ci/ovc_run_with_main_lease.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("PREDECESSOR_MOVED", text)
        self.assertIn("OVC_REQUIRED_ASSURANCE_LEASE_INVALIDATED", text)
        self.assertIn("OVC_REQUIRED_ASSURANCE_LEASE_OBSERVABILITY_FAILED", text)
        self.assertIn("_terminate_process_group(process)", text)
        self.assertIn("recompose the same PIP", text)

    def test_constitution_keeps_parallel_merge_false(self) -> None:
        text = (
            ROOT
            / "contracts/development/v0_4/OVC_SERIALIZED_INTEGRATION_QUEUE_CONSTITUTION_v0_1.md"
        ).read_text(encoding="utf-8")
        self.assertIn("`parallel_merge` remains `false`", text)
        self.assertIn("BASE_INDEPENDENT", text)
        self.assertIn("BASE_SENSITIVE", text)


if __name__ == "__main__":
    unittest.main()
