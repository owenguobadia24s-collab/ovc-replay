from __future__ import annotations

import unittest

from ovc.research_orchestration.golden2_downstream import run_weekly_full_chain


class Golden2WeeklyWP2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_weekly_full_chain()

    def test_actual_golden2_c2_outputs_feed_current_c2e_lifecycle(self) -> None:
        c2e = self.result["c2e"]
        self.assertGreater(c2e["frame_count"], 850)
        self.assertGreaterEqual(c2e["episode_count"], 4)
        self.assertEqual(c2e["episode_count"], c2e["handoff_count"])
        self.assertGreater(c2e["event_count"], c2e["episode_count"])
        self.assertIn("CENSORED", c2e["status_counts"])
        self.assertFalse(c2e["real_source_replay"])
        self.assertEqual("NONE", c2e["active_c2e"])
        self.assertEqual("NONE", c2e["active_boundary_pack"])

    def test_sfc_consumes_current_c2e_handoff_without_side_collapse(self) -> None:
        sfc = self.result["sfc"]
        self.assertEqual(sfc["population"]["denominator_eligible"], len(sfc["representations"]))
        self.assertGreaterEqual(len(sfc["representations"]), 4)
        statuses = {row["status"] for row in sfc["pairs"]}
        self.assertIn("EVALUATED", statuses)
        self.assertIn("NOT_COMPARABLE", statuses)
        self.assertGreaterEqual(len(sfc["catalog"]["families"]), 2)
        self.assertEqual("FAMILY_EVIDENCE_PRESENT", sfc["family_evidence_stream"]["status"])
        self.assertEqual("NULL_CONTROL_EXECUTION_ASSURANCE_ONLY", sfc["representation_interpretation"])
        self.assertFalse(sfc["representation_or_family_promotion"])

    def test_occurrence_context_remains_nonstructural(self) -> None:
        projection = self.result["sfc"]["occurrence_context_projection"]
        self.assertEqual("GBPUSD", projection["fields"]["instrument_id"])
        self.assertEqual("SYNTHETIC_WEEK", projection["fields"]["session.id"])
        self.assertEqual("NONE", projection["authority_effect"])

    def test_research_operations_addresses_integrated_run_and_every_stage(self) -> None:
        research = self.result["research"]
        receipt = research["run_receipt"]
        self.assertEqual("COMPLETE", receipt.status)
        self.assertEqual(10, len(receipt.stage_receipts))
        self.assertTrue(research["logical_hash"])
        run_nodes = [node for node in research["read_model"].nodes if node.object_type == "IROF_INTEGRATED_RUN_RECEIPT"]
        self.assertEqual(1, len(run_nodes))
        self.assertEqual("DERIVED_EXECUTION_EVIDENCE_ONLY", run_nodes[0].payload["authority_state"])

    def test_full_chain_creates_no_real_validation_or_scientific_authority(self) -> None:
        summary = self.result["summary"]
        self.assertFalse(summary["real_market_data"])
        self.assertFalse(summary["validation_consumed"])
        self.assertEqual("NONE", summary["authority_effect"])
        self.assertEqual("FAMILY_EVIDENCE_PRESENT", summary["family_evidence_status"])


if __name__ == "__main__":
    unittest.main()
