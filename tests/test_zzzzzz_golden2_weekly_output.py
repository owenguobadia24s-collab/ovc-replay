from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest


class ZZZZZZGolden2WeeklyOutputTest(unittest.TestCase):
    def test_emit_compact_golden2_result_last_from_isolated_process(self) -> None:
        script = r'''
import json
from ovc.research_orchestration.golden2_assurance import run_assurance
result = run_assurance()
compact = {
    "scientific_logical_hash": result["scientific_logical_hash"],
    "receipt_hash": result["receipt_hash"],
    "fresh_repeated_equivalent": result["fresh_repeated_equivalent"],
    "alternate_order_equivalent": result["alternate_order_equivalent"],
    "counts": result["counts"],
    "family_evidence_status": result["family_evidence_status"],
    "representation_interpretation": result["representation_interpretation"],
    "checkpoint": result["checkpoint"],
    "cache": result["cache"],
    "whole_run": result["whole_run"],
    "measured_stage_seconds": {
        stage: {
            metric["metric_id"]: metric["value"]
            for metric in receipt["metrics"]
            if metric["metric_id"] in {"wall_seconds", "cpu_seconds", "object_count", "pair_count"}
        }
        for stage, receipt in result["telemetry"].items()
    },
    "real_source_replay": result["real_source_replay"],
    "validation_consumed": result["validation_consumed"],
    "authority_effect": result["authority_effect"],
}
print("GOLDEN2_FINAL_RESULT=" + json.dumps(compact, sort_keys=True, separators=(",", ":")))
assert result["fresh_repeated_equivalent"]
assert result["alternate_order_equivalent"]
assert not result["real_source_replay"]
assert not result["validation_consumed"]
assert result["authority_effect"] == "NONE"
'''
        environment = dict(os.environ)
        current_pythonpath = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = "src" if not current_pythonpath else "src" + os.pathsep + current_pythonpath
        completed = subprocess.run(
            [sys.executable, "-c", script],
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )
        if completed.stdout:
            print(completed.stdout.strip())
        if completed.stderr:
            print(completed.stderr.strip())
        self.assertEqual(0, completed.returncode)
        marker = next((line for line in completed.stdout.splitlines() if line.startswith("GOLDEN2_FINAL_RESULT=")), None)
        self.assertIsNotNone(marker)
        compact = json.loads(marker.split("=", 1)[1])
        self.assertTrue(compact["fresh_repeated_equivalent"])
        self.assertTrue(compact["alternate_order_equivalent"])
        self.assertFalse(compact["real_source_replay"])
        self.assertFalse(compact["validation_consumed"])
        self.assertEqual("NONE", compact["authority_effect"])


if __name__ == "__main__":
    unittest.main()
