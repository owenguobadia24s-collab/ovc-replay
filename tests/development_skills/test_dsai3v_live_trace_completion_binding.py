from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.development.diagnostic_observability import summarize_trace
from ovc.development.skills.vit_local_completion_executor import (
    build_live_transaction_freeze,
    complete_frozen_transaction,
)
from ovc.development.skills.vit_materialisation import ReceiptStore
from ovc.development.skills.vit_routing import build_vit_lineage_record


class Dsai3vLiveTraceCompletionBindingTests(unittest.TestCase):
    def _freeze(self):
        lineage = build_vit_lineage_record(
            programme_id="OVC-TEST",
            packet_id="TEST-PACKET",
            pip_identity_payload={
                "schema_version": "packet-integration-payload/v0.1",
                "programme_id": "OVC-TEST",
                "packet_id": "TEST-PACKET",
                "logical_changes": [
                    {
                        "op": "ADD",
                        "path": "example.txt",
                        "blob_sha": "1" * 40,
                        "mode": "100644",
                    }
                ],
                "authority_manifest_id": "a" * 64,
                "dependency_frontier_id": "b" * 64,
                "completion_transition": {
                    "status": "COMPLETED",
                    "next_packet": "NEXT-PACKET",
                },
            },
            train_generation_id="test-train",
            ordinal=0,
            predecessor_tree_sha="c" * 40,
            result_tree_sha="d" * 40,
            apply_profile="INTEGRATION_APPLY_PROFILE_REFERENCE_v0_1",
        )
        return build_live_transaction_freeze(
            lineage_record=lineage,
            pr_number=123,
            base_sha="e" * 40,
            head_sha="f" * 40,
            base_tree="c" * 40,
            head_tree="d" * 40,
            workflow_run_id="9001",
            run_attempt="1",
        )

    def test_trace_summary_is_durable_and_bound_to_canonical_devobs(self) -> None:
        trace = summarize_trace(
            run_id="DSAI3V:TEST:123",
            programme_id="OVC-TEST",
            packet_id="TEST-PACKET",
            started_at_utc="2026-08-18T07:00:00Z",
            completed_at_utc="2026-08-18T07:00:01Z",
            total_wall_ms=1000,
            events=(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            proof = complete_frozen_transaction(
                freeze=self._freeze(),
                observed_commit="9" * 40,
                observed_tree="d" * 40,
                receipt_store=store,
                siq_receipts=(
                    {
                        "schema": "ovc-github-check-observation/v1",
                        "record_id": "siq-check",
                        "status": "SIQ_READY",
                    },
                ),
                trace_summary=trace,
                async_assurance_metrics={
                    "workflow_green_to_materialisation_ms": 250,
                },
            )

            self.assertEqual(proof["trace_summary_id"], trace["record_id"])
            self.assertTrue((Path(tmp) / f"{trace['record_id']}.json").is_file())
            devobs = json.loads(
                (
                    Path(tmp)
                    / f"{proof['receipt_ids']['development_latency_receipt_id']}.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(devobs["latency"]["status"], "OBSERVED")
            self.assertEqual(devobs["latency"]["total_wall_ms"], 1000)
            self.assertEqual(devobs["latency"]["trace_summary_id"], trace["record_id"])
            self.assertEqual(devobs["async_assurance"]["status"], "OBSERVED")
            self.assertEqual(
                devobs["async_assurance"]["workflow_green_to_materialisation_ms"],
                250,
            )
            self.assertEqual(
                devobs["latency"]["latency_decomposition"]["MODEL_REASONING"]["evidence_class"],
                "UNAVAILABLE",
            )

    def test_absent_trace_preserves_existing_unavailable_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            proof = complete_frozen_transaction(
                freeze=self._freeze(),
                observed_commit="9" * 40,
                observed_tree="d" * 40,
                receipt_store=store,
            )
            self.assertNotIn("trace_summary_id", proof)
            devobs = json.loads(
                (
                    Path(tmp)
                    / f"{proof['receipt_ids']['development_latency_receipt_id']}.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(devobs["latency"]["status"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
