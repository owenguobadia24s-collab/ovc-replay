from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_RUN_TESTS = (
    "tests/srfd/test_srfdi_wp10_v06_execution_blocker.py",
    "tests/srfd/test_srfdi_wp10_v07_segmentation_binding_blocker.py",
    "tests/srfd/test_srfdi_wp10_v09_run_start.py",
    "tests/srfd/test_srfdi_wp10_v09_capacity_failure.py",
    "tests/srfd/test_srfdi_wp10_execution_resilience_state.py",
)


class SRFDIHistoricalStateIndependenceTests(unittest.TestCase):
    def test_historical_run_evidence_tests_do_not_read_moving_current_pointer(self):
        for relative in HISTORICAL_RUN_TESTS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("CURRENT_STATE_POINTER.json", text, relative)
            self.assertNotIn("_current_pointer_compat", text, relative)

    def test_historical_run_evidence_tests_bind_versioned_state_records(self):
        expected = {
            "test_srfdi_wp10_v06_execution_blocker.py": "OVC_SRFDI_STATE_v0_22_WP10_V06_BLOCKED.json",
            "test_srfdi_wp10_v07_segmentation_binding_blocker.py": "OVC_SRFDI_STATE_v0_27_WP10_V07_SEGMENTATION_BINDING_BLOCKED.json",
            "test_srfdi_wp10_v09_run_start.py": "OVC_SRFDI_STATE_v0_42_WP10_V09_RUNNING.json",
            "test_srfdi_wp10_v09_capacity_failure.py": "OVC_SRFDI_STATE_v0_43_WP10_V09_CAPACITY_BLOCKED.json",
            "test_srfdi_wp10_execution_resilience_state.py": "OVC_SRFDI_STATE_v0_23_WP10_EXECUTION_RESILIENCE_READY.json",
        }
        for name, state_name in expected.items():
            text = (ROOT / "tests/srfd" / name).read_text(encoding="utf-8")
            self.assertIn(state_name, text, name)


if __name__ == "__main__":
    unittest.main()
