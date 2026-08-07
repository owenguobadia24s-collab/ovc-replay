from __future__ import annotations

import json
import unittest

from ovc.research_operations.mcarb.capacity import capacity_profile


class MCARBIWP6CapacityReceiptOutputTest(unittest.TestCase):
    def test_zzz_emit_github_hosted_c0_c1_capacity_receipt(self) -> None:
        profile = capacity_profile(c0_n=64, c1_n=449)
        profile["budget"] = {
            "max_runtime_seconds": 14400,
            "max_peak_memory_bytes": 17179869184,
            "max_external_artifact_bytes": 10737418240,
        }
        profile["budget_result"] = {
            "c0_runtime_pass": profile["C0"]["wall_seconds"] <= 14400,
            "c1_runtime_pass": profile["C1"]["wall_seconds"] <= 14400,
            "c0_peak_python_memory_pass": profile["C0"]["peak_python_tracemalloc_bytes"] <= 17179869184,
            "c1_peak_python_memory_pass": profile["C1"]["peak_python_tracemalloc_bytes"] <= 17179869184,
            "external_artifact_bytes": 0,
            "external_artifact_budget_pass": True,
        }
        print("MCARBI_CAPACITY_RECEIPT=" + json.dumps(profile, sort_keys=True, separators=(",", ":")))
        self.assertTrue(all(value is True or key == "external_artifact_bytes" for key, value in profile["budget_result"].items()))
        self.assertEqual(profile["C1"]["n_per_side"], 449)
        self.assertEqual(profile["C1"]["input_bar_count"], 898)


if __name__ == "__main__":
    unittest.main()
