from __future__ import annotations

import json
import unittest

from ovc.research_orchestration.golden2_assurance import run_assurance


class Golden2WeeklyWP3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_assurance()
        print("GOLDEN2_ASSURANCE_RESULT=" + json.dumps(cls.result, sort_keys=True, separators=(",", ":")))

    def test_fresh_repeat_and_alternate_order_are_equivalent(self) -> None:
        self.assertTrue(self.result["fresh_repeated_equivalent"])
        self.assertTrue(self.result["alternate_order_equivalent"])
        self.assertEqual(self.result["scientific_logical_hash"], self.result["repeated_logical_hash"])

    def test_checkpoint_resume_reuses_complete_chain_and_corruption_is_bounded(self) -> None:
        checkpoint = self.result["checkpoint"]
        self.assertTrue(checkpoint["reused_all_stages"])
        self.assertEqual([], checkpoint["rerun_stage_ids"])
        self.assertEqual(1, checkpoint["restart_count"])
        self.assertEqual(["SRI_REPRESENTATION"], checkpoint["corrupt_quarantined_stage_ids"])
        self.assertIn("SRI_REPRESENTATION", checkpoint["corrupt_rerun_stage_ids"])
        self.assertIn("COMPARABILITY_COMPARISON_DISTANCE", checkpoint["corrupt_rerun_stage_ids"])
        self.assertIn("FDI_C2G_FAMILY", checkpoint["corrupt_rerun_stage_ids"])
        self.assertIn("FAMILY_EVIDENCE_STREAM", checkpoint["corrupt_rerun_stage_ids"])
        self.assertIn("RESEARCH_OPERATIONS", checkpoint["corrupt_rerun_stage_ids"])
        self.assertIn("IROF_CHECKPOINT_CONTENT_CORRUPTION", checkpoint["corrupt_reason_codes"])

    def test_semantic_cache_reuses_exact_output_and_quarantines_corruption(self) -> None:
        cache = self.result["cache"]
        self.assertEqual("HIT", cache["initial_status"])
        self.assertGreater(cache["bytes_avoided"], 0)
        self.assertGreater(cache["work_units_avoided"], 0)
        self.assertEqual("MISS", cache["corrupt_status"])
        self.assertIn("IROF_CACHE_PAYLOAD_CORRUPTION", cache["corrupt_reason_codes"])
        self.assertEqual("MISS", cache["post_quarantine_status"])
        self.assertIn("IROF_CACHE_KEY_QUARANTINED", cache["post_quarantine_reason_codes"])

    def test_per_stage_and_whole_run_telemetry_is_machine_readable(self) -> None:
        telemetry = self.result["telemetry"]
        required = {
            "POPULATION_SOURCE_OPT_A", "C1", "C2_REVISED", "C2E_V0_2", "OCCURRENCE_CONTEXT",
            "SRI_REPRESENTATION", "COMPARABILITY_COMPARISON_DISTANCE", "FDI_C2G_FAMILY",
            "FAMILY_EVIDENCE_STREAM", "RESEARCH_OPERATIONS",
        }
        self.assertTrue(required <= set(telemetry))
        for stage in required:
            ids = {row["metric_id"] for row in telemetry[stage]["metrics"]}
            self.assertIn("wall_seconds", ids)
            self.assertIn("cpu_seconds", ids)
            self.assertIn("peak_rss_bytes", ids)
            self.assertIn("object_count", ids)
            self.assertEqual("NONE", telemetry[stage]["scientific_effect"])
        self.assertGreater(self.result["whole_run"]["wall_seconds"], 0)
        self.assertGreaterEqual(self.result["whole_run"]["cpu_seconds"], 0)

    def test_weekly_full_chain_stays_authority_neutral(self) -> None:
        self.assertFalse(self.result["real_source_replay"])
        self.assertFalse(self.result["validation_consumed"])
        self.assertEqual("NONE", self.result["authority_effect"])
        self.assertEqual("NULL_CONTROL_EXECUTION_ASSURANCE_ONLY", self.result["representation_interpretation"])
        self.assertEqual("FAMILY_EVIDENCE_PRESENT", self.result["family_evidence_status"])


if __name__ == "__main__":
    unittest.main()
