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
from ovc.research_orchestration.golden2_weekly import build_opt_a_week
result = run_assurance()
opt_a = build_opt_a_week()
compact = {
    "scientific_logical_hash": result["scientific_logical_hash"],
    "receipt_hash": result["receipt_hash"],
    "fresh_repeated_equivalent": result["fresh_repeated_equivalent"],
    "alternate_order_equivalent": result["alternate_order_equivalent"],
    "counts": result["counts"],
    "opt_a_derived_counts": opt_a["summary"]["derived_counts"],
    "opt_a_quarantine_count": opt_a["summary"]["quarantine_count"],
    "opt_a_quarantine_reason_counts": opt_a["summary"]["quarantine_reason_counts"],
    "c2_axis_computability_counts": result["c2_axis_computability_counts"],
    "c2e_fixture_boundary_required_axes": result["c2e_fixture_boundary_required_axes"],
    "conformance_warnings": result["conformance_warnings"],
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
assert result["counts"] == {
    "m1_bid": 7195, "m1_ask": 7195, "c1": 1074, "c2_observations": 1344,
    "c2_structural_snapshots": 932, "c2_transitions": 4620,
    "c2e_frames": 932, "c2e_episodes": 8, "sri_representations": 8,
    "comparison_pairs": 28, "families": 2,
    "c2e_input_c2_snapshots": 932, "c2e_eligible_c2_snapshots": 932,
}
assert opt_a["summary"]["derived_counts"] == {"15M": {"BID": 479, "ASK": 479}, "2H_A_L": {"BID": 58, "ASK": 58}}
assert opt_a["summary"]["quarantine_count"] == 8
assert opt_a["summary"]["quarantine_reason_counts"] == {"INCOMPLETE_OR_NONCONTIGUOUS_M1_BUCKET": 8}
assert result["conformance_warnings"] == []
assert result["c2e_fixture_boundary_required_axes"] == ["LOCATION", "ORGANISATION"]
assert result["c2_axis_computability_counts"].get("MOTION:COMPUTABLE", 0) == 932
assert result["c2_axis_computability_counts"].get("MOTION:NOT_COMPUTABLE", 0) == 0
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
        self.assertEqual(1074, compact["counts"]["c1"])
        self.assertEqual(8, compact["opt_a_quarantine_count"])
        self.assertEqual([], compact["conformance_warnings"])
        self.assertEqual(["LOCATION", "ORGANISATION"], compact["c2e_fixture_boundary_required_axes"])
        self.assertEqual(932, compact["c2_axis_computability_counts"].get("MOTION:COMPUTABLE", 0))
        self.assertEqual(0, compact["c2_axis_computability_counts"].get("MOTION:NOT_COMPUTABLE", 0))
        self.assertFalse(compact["real_source_replay"])
        self.assertFalse(compact["validation_consumed"])
        self.assertEqual("NONE", compact["authority_effect"])


if __name__ == "__main__":
    unittest.main()
