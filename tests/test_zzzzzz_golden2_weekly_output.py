from __future__ import annotations

import json
import unittest

from ovc.research_orchestration.golden2_assurance import run_assurance


class ZZZZZZGolden2WeeklyOutputTest(unittest.TestCase):
    def test_emit_compact_golden2_result_last(self) -> None:
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
        self.assertTrue(result["fresh_repeated_equivalent"])
        self.assertTrue(result["alternate_order_equivalent"])
        self.assertFalse(result["real_source_replay"])
        self.assertFalse(result["validation_consumed"])
        self.assertEqual("NONE", result["authority_effect"])


if __name__ == "__main__":
    unittest.main()
