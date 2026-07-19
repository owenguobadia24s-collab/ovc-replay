from __future__ import annotations

import unittest

from ovc_opt_b import (
    paper_playbook_gate,
    robustness_disposition,
    summarize_leave_one_month_out,
)


class RobustnessTests(unittest.TestCase):
    def test_leave_one_month_out_requires_complete_unique_surface(self) -> None:
        row = {
            "omitted_month": "2025-01",
            "evaluable": True,
            "structural_story_reappeared": True,
            "counter_story_alert": True,
            "distinct_matching_overlap_clusters": 12,
            "distinct_contradictory_overlap_clusters": 20,
        }
        with self.assertRaises(ValueError):
            summarize_leave_one_month_out([row, row], expected_months=2)

    def test_leave_one_month_out_summary_preserves_counter_alert(self) -> None:
        rows = [
            {
                "omitted_month": f"2025-{month:02d}",
                "evaluable": True,
                "structural_story_reappeared": month != 2,
                "counter_story_alert": True,
                "distinct_matching_overlap_clusters": 20 - month,
                "distinct_contradictory_overlap_clusters": 30 - month,
            }
            for month in (1, 2)
        ]
        result = summarize_leave_one_month_out(rows, expected_months=2)
        self.assertFalse(result["reappearance_stable_across_all_deletions"])
        self.assertTrue(result["counter_alert_persistent_across_all_deletions"])
        self.assertEqual(result["counter_alert_after_deletion_count"], 2)

    def test_counter_story_is_a_robustness_blocker(self) -> None:
        self.assertEqual(
            robustness_disposition(
                evaluable=True,
                reappeared=True,
                counter_story_alert=True,
                lomo_reappearance_stable=True,
            ),
            "BLOCKED_COUNTER_STORY_DOMINANCE",
        )

    def test_paper_gate_cannot_rescue_counter_story_alert(self) -> None:
        validation = {
            "definition_drift_status": "NO_DRIFT_DETECTED",
            "edge_authority": "NONE",
            "execution_authority": "NONE",
            "evaluable": True,
            "structural_story_reappeared": True,
            "counter_story_alert": True,
            "coverage_audit": {
                "strict_path_rule": "COMPLETE_ONLY_NO_REPAIR",
                "coverage_records": 12,
                "complete_records": 10,
                "censored_records": 2,
            },
            "counts": {"antecedent_outcome_records": 10},
        }
        robustness = {
            "leave_one_month_out_summary": {
                "reappearance_stable_across_all_deletions": True
            }
        }
        result = paper_playbook_gate(validation=validation, robustness=robustness)
        self.assertEqual(result["gate_decision"], "BLOCK")
        self.assertIn("COUNTER_STORY_ALERT", result["blocking_reasons"])
        self.assertFalse(result["paper_playbook_authorized"])

    def test_paper_gate_defers_month_sensitive_candidate(self) -> None:
        validation = {
            "definition_drift_status": "NO_DRIFT_DETECTED",
            "edge_authority": "NONE",
            "execution_authority": "NONE",
            "evaluable": True,
            "structural_story_reappeared": True,
            "counter_story_alert": False,
            "coverage_audit": {
                "strict_path_rule": "COMPLETE_ONLY_NO_REPAIR",
                "coverage_records": 10,
                "complete_records": 10,
                "censored_records": 0,
            },
            "counts": {"antecedent_outcome_records": 10},
        }
        robustness = {
            "leave_one_month_out_summary": {
                "reappearance_stable_across_all_deletions": False
            }
        }
        result = paper_playbook_gate(validation=validation, robustness=robustness)
        self.assertEqual(result["gate_decision"], "DEFER")
        self.assertEqual(result["deferral_reasons"], ["MONTH_SENSITIVE_RECURRENCE"])


if __name__ == "__main__":
    unittest.main()
