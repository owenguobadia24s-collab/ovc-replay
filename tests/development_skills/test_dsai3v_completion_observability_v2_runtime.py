from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ovc.development.skills.vit_completion_runtime import persist_physical_completion
from ovc.development.skills.vit_materialisation import PhysicalMaterialisationTransaction, ReceiptStore


class CanonicalCompletionReceiptV2RuntimeTests(unittest.TestCase):
    def transaction(self) -> PhysicalMaterialisationTransaction:
        return PhysicalMaterialisationTransaction(
            vit_generation_id="g",
            ticket_id="ticket",
            train_generation_id="train",
            expected_predecessor_commit="1" * 40,
            expected_predecessor_tree="2" * 40,
            expected_result_tree="3" * 40,
            authority_frontier_id="4" * 64,
            assurance_frontier_id="5" * 64,
            materialisation_profile="LIVE_PHYSICAL_MAIN",
        )

    def test_generic_trace_completion_is_not_reinterpreted_as_materialisation_time(self) -> None:
        trace = {
            "schema": "ovc-development-observability-trace-summary/v1",
            "record_id": "9" * 64,
            "completed_at_utc": "2026-08-28T08:00:50Z",
            "total_wall_ms": 10,
            "throughput": {},
            "latency_decomposition": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            result = persist_physical_completion(
                transaction=self.transaction(),
                observed_commit="a" * 40,
                observed_tree="3" * 40,
                programme_id="OVC-DSAI-VIT-v0.3",
                packet_id="P",
                implementation_ref="github:pr:1:head:" + "6" * 40,
                qa_ref="q",
                gate_decision_ref="d",
                payload_id="7" * 64,
                next_packet=None,
                receipt_store=store,
                trace_summary=trace,
            )
            v2 = json.loads((Path(tmp) / f"{result['v2_development_latency_receipt_id']}.json").read_text())
            self.assertIsNone(v2["timing"]["physical_materialised_at_utc"])
            self.assertIsNotNone(v2["timing"]["packet_completion_receipt_persisted_at_utc"])
            self.assertEqual(
                v2["timing"]["selected_sources"]["packet_completion_receipt_persisted_at_utc"]["source_type"],
                "OWNER_LOCAL_RECEIPT",
            )

    def test_exact_caller_sources_are_admitted_without_inference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            result = persist_physical_completion(
                transaction=self.transaction(),
                observed_commit="a" * 40,
                observed_tree="3" * 40,
                programme_id="OVC-DSAI-VIT-v0.3",
                packet_id="P2",
                implementation_ref="github:pr:2:head:" + "6" * 40,
                qa_ref="q",
                gate_decision_ref="d",
                payload_id="7" * 64,
                next_packet=None,
                receipt_store=store,
                completion_timing_sources=[
                    {
                        "field": "physical_materialised_at_utc",
                        "source_type": "GITHUB_PR",
                        "source_id": "pr:2",
                        "observed_at_utc": "2026-08-28T08:00:50Z",
                        "authority": "OBSERVATIONAL_ONLY",
                    }
                ],
                completion_aa0_observability={
                    "repository_assurance_disposition": "EXACT_GENERATION_REUSE",
                    "unittest_parity_disposition": "EXACT_GENERATION_REUSE",
                    "runner_parity_disposition": "EXACT_GENERATION_REUSE",
                    "canonical_shards_executed": False,
                },
            )
            v2 = json.loads((Path(tmp) / f"{result['v2_development_latency_receipt_id']}.json").read_text())
            self.assertEqual(v2["timing"]["physical_materialised_at_utc"], "2026-08-28T08:00:50Z")
            self.assertEqual(v2["aa0"]["candidate_head_sha"], "6" * 40)
            self.assertEqual(v2["aa0"]["pip_id"], "7" * 64)
            self.assertEqual(v2["aa0"]["prospective_tree_sha"], "3" * 40)
            self.assertEqual(v2["aa0"]["physical_tree_sha"], "3" * 40)


if __name__ == "__main__":
    unittest.main()
