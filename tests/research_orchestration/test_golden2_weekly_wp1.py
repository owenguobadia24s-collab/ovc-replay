from __future__ import annotations

import unittest

from ovc.research_orchestration.golden2_weekly import run_weekly_upstream


class Golden2WeeklyWP1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_weekly_upstream()

    def test_generated_week_uses_separate_bid_ask_and_exact_gap_accounting(self) -> None:
        opt_a = self.result["opt_a"]
        self.assertEqual(7195, len(opt_a["raw"]["BID"]))
        self.assertEqual(7195, len(opt_a["raw"]["ASK"]))
        self.assertNotEqual(opt_a["raw"]["BID"][0].open, opt_a["raw"]["ASK"][0].open)
        self.assertEqual(479, len(opt_a["derived"]["15M"]["BID"]))
        self.assertEqual(479, len(opt_a["derived"]["15M"]["ASK"]))
        self.assertEqual(59, len(opt_a["derived"]["2H_A_L"]["BID"]))
        self.assertEqual(59, len(opt_a["derived"]["2H_A_L"]["ASK"]))
        self.assertEqual(4, opt_a["summary"]["quarantine_count"])
        self.assertEqual({"INCOMPLETE_OR_NONCONTIGUOUS_M1_BUCKET": 4}, opt_a["summary"]["quarantine_reason_counts"])

    def test_c1_is_computed_by_current_reference_engine_for_both_clocks_and_sides(self) -> None:
        c1 = self.result["c1"]
        self.assertEqual(1076, c1["summary"]["record_count"])
        self.assertEqual(1076, c1["summary"]["synthetic_count"])
        self.assertEqual(
            {"15M:ASK": 479, "15M:BID": 479, "2H_A_L:ASK": 59, "2H_A_L:BID": 59},
            c1["summary"]["by_clock_side"],
        )
        self.assertTrue(all(str(row["record_id"]).startswith("c1:") for row in c1["records"]))
        self.assertTrue(all(row["formula_registry_id"] == "C1.FORMULAS.v0.1" for row in c1["records"]))
        self.assertTrue(any(row["null_reasons"] for row in c1["records"]))

    def test_revised_c2_accounts_for_every_week_slot_and_preserves_missingness(self) -> None:
        summary = self.result["c2"]["summary"]
        self.assertEqual(1344, summary["expected_slot_count"])
        self.assertEqual(1344, summary["observation_count"])
        self.assertEqual(956, summary["evidence_counts"]["PRESENT_COMPLETE"])
        self.assertEqual(2, summary["evidence_counts"]["PRESENT_INCOMPLETE"])
        self.assertEqual(2, summary["evidence_counts"]["ABSENT"])
        self.assertEqual(384, summary["evidence_counts"]["NOT_EXPECTED"])
        self.assertTrue(summary["chronology_pass"])

    def test_revised_c2_runs_current_structural_components_at_week_scale(self) -> None:
        c2 = self.result["c2"]
        summary = c2["summary"]
        self.assertGreater(summary["structural_snapshot_count"], 900)
        self.assertGreater(summary["transition_count"], 4000)
        self.assertGreater(summary["separate_side_snapshot_counts"]["BID"], 400)
        self.assertGreater(summary["separate_side_snapshot_counts"]["ASK"], 400)
        for snapshot in c2["snapshots"][:20]:
            self.assertEqual({"LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY"}, {row["axis"] for row in snapshot["formula_outputs"]})
            self.assertEqual("SHADOW_FROZEN_READ_ONLY", snapshot["authority"])
            self.assertTrue(snapshot["levels"])
            self.assertTrue(snapshot["container"]["container_id"])
            self.assertTrue(snapshot["level_relation_set"]["complete_scoped_inventory"])

    def test_no_market_or_reserved_authority_is_created(self) -> None:
        summary = self.result["summary"]
        self.assertFalse(summary["real_market_data"])
        self.assertFalse(summary["validation_consumed"])
        self.assertFalse(summary["hidden_generator_truth_consumed"])
        self.assertEqual("NONE", summary["authority_effect"])
        self.assertEqual("FIXTURE_ONLY", summary["opt_a"]["authority"])
        self.assertEqual("SHADOW_FROZEN_READ_ONLY", summary["c2"]["authority"])


if __name__ == "__main__":
    unittest.main()
