from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
QUALIFY = ROOT / "scripts/governance/grt_v0_2/qualify.py"

spec = importlib.util.spec_from_file_location("grt2_g2_qualify", QUALIFY)
assert spec and spec.loader
qualify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualify)


class GRT2G2CurrentMainRenewalTests(unittest.TestCase):
    def test_exact_head_census_and_a8_shadow_remain_resolved_after_main_movement(self) -> None:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        base = subprocess.check_output(
            ["git", "merge-base", "HEAD", "origin/main"], cwd=ROOT, text=True
        ).strip()
        census = qualify.current_census(head)
        probes = qualify.mutation_probes()
        shadow = qualify.a8_shadow(base, head, census, probes)

        self.assertEqual(census["source_commit"], head)
        self.assertEqual(census["classification_status"], "RESOLVED")
        self.assertEqual(census["not_evaluable_component_count"], 0)
        self.assertEqual(probes["mandatory_mutation_survivors"], 0)
        self.assertEqual(shadow["base_commit"], base)
        self.assertEqual(shadow["head_commit"], head)
        self.assertTrue(shadow["real_ci_candidate"])
        self.assertEqual(shadow["review_status"], "PASS")
        self.assertEqual(shadow["unresolved_enforcement_false_negatives"], 0)
        self.assertEqual(shadow["blocking_false_positives"], 0)
        self.assertEqual(shadow["pilot_escapes"], 0)
        self.assertEqual(shadow["not_evaluable_changed_paths"], [])


if __name__ == "__main__":
    unittest.main()
