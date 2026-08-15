from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.development.dsai3v_completion_observability import (
    CANONICAL_COMPLETION_SCHEMA,
    build_canonical_completion_latency_receipt,
)
from ovc.development.skills.vit_materialisation import PacketCompletionReceipt, ReceiptStore


class Dsai3vCompletionObservabilityTests(unittest.TestCase):
    def _completion(self) -> PacketCompletionReceipt:
        return PacketCompletionReceipt(
            "OVC-DSAI-VIT-v0.3",
            "DSAI3V-TEST-PACKET",
            "impl-ref",
            "qa-ref",
            "gate-ref",
            "payload-id",
            "vit-generation-id",
            "materialisation-receipt-id",
            "NEXT-PACKET",
        )

    def test_canonical_receipt_joins_orch_vit_siq_without_inference(self) -> None:
        completion = self._completion()
        trace = {
            "schema": "ovc-development-observability-trace-summary/v1",
            "record_id": "trace-1",
            "total_wall_ms": 1000,
            "throughput": {"active_execution_ms": 400, "external_wait_ms": 300},
            "latency_decomposition": {"REMOTE_CI_EXECUTION": {"duration_ms": 250}},
        }
        context = {
            "schema": "ovc-development-latency-diagnostic-companion/v2",
            "record_id": "ctx-1",
            "task_profile": {"implementation_difficulty": "D2"},
            "assistant_configuration": {"reasoning_profile": "UNKNOWN"},
            "comparison_keys": {"implementation_difficulty": "D2"},
        }
        receipt = build_canonical_completion_latency_receipt(
            programme_id=completion.programme_id,
            packet_id=completion.packet_id,
            completion_receipt_id=completion.receipt_id,
            contextual_latency_receipt=context,
            trace_summary=trace,
            orch_receipts=({"schema": "orch/v2", "record_id": "o1", "decision_state": "DECISION_SELECTED", "execution_state": "EXECUTION_COMPLETED"},),
            vit_receipts=({"schema": "vit/v1", "receipt_id": "v1", "equality": True, "outcome": "MATERIALISED_EQUIVALENT"},),
            siq_receipts=({"schema": "siq/v1", "receipt_id": "s1", "status": "SIQ_READY"},),
        )
        self.assertEqual(receipt["schema"], CANONICAL_COMPLETION_SCHEMA)
        self.assertEqual(receipt["completion_receipt_id"], completion.receipt_id)
        self.assertEqual(receipt["orch"]["execution_completed_count"], 1)
        self.assertEqual(receipt["vit"]["exact_tree_equal_count"], 1)
        self.assertEqual(receipt["siq"]["ready_pass_count"], 1)
        self.assertEqual(receipt["latency"]["total_wall_ms"], 1000)
        self.assertEqual(receipt["async_assurance"]["status"], "UNAVAILABLE")
        self.assertIsNone(receipt["async_assurance"]["ci_development_overlap_ms"])
        self.assertEqual(receipt["authority_effect"], "NONE")

    def test_async_assurance_observed_metrics_are_preserved_without_inference(self) -> None:
        completion = self._completion()
        receipt = build_canonical_completion_latency_receipt(
            programme_id=completion.programme_id,
            packet_id=completion.packet_id,
            completion_receipt_id=completion.receipt_id,
            async_assurance_metrics={
                "background_ci_elapsed_ms": 4200,
                "ci_development_overlap_ms": 3100,
                "assurance_reuse_count": 2,
                "descendant_invalidation_count": 0,
            },
        )
        async_metrics = receipt["async_assurance"]
        self.assertEqual(async_metrics["status"], "OBSERVED")
        self.assertEqual(async_metrics["background_ci_elapsed_ms"], 4200)
        self.assertEqual(async_metrics["ci_development_overlap_ms"], 3100)
        self.assertEqual(async_metrics["assurance_reuse_count"], 2)
        self.assertEqual(async_metrics["descendant_invalidation_count"], 0)
        self.assertIsNone(async_metrics["foreground_ci_wait_ms"])
        self.assertEqual(receipt["authority_effect"], "NONE")

    def test_async_assurance_metrics_reject_unknown_or_negative_values(self) -> None:
        completion = self._completion()
        with self.assertRaises(ValueError):
            build_canonical_completion_latency_receipt(
                programme_id=completion.programme_id,
                packet_id=completion.packet_id,
                completion_receipt_id=completion.receipt_id,
                async_assurance_metrics={"invented_metric": 1},
            )
        with self.assertRaises(ValueError):
            build_canonical_completion_latency_receipt(
                programme_id=completion.programme_id,
                packet_id=completion.packet_id,
                completion_receipt_id=completion.receipt_id,
                async_assurance_metrics={"foreground_ci_wait_ms": -1},
            )

    def test_completion_store_persists_completion_devobs_and_attachment(self) -> None:
        completion = self._completion()
        receipt = build_canonical_completion_latency_receipt(
            programme_id=completion.programme_id,
            packet_id=completion.packet_id,
            completion_receipt_id=completion.receipt_id,
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(Path(tmp))
            ids = store.put_completion_with_devobs(completion, receipt)
            self.assertTrue((Path(tmp) / f"{completion.receipt_id}.json").is_file())
            self.assertTrue((Path(tmp) / f"{ids['development_latency_receipt_id']}.json").is_file())
            attachment = json.loads((Path(tmp) / f"{ids['attachment_id']}.json").read_text(encoding="utf-8"))
            self.assertEqual(attachment["completion_receipt_id"], completion.receipt_id)
            self.assertEqual(attachment["development_latency_receipt_id"], receipt["record_id"])
            self.assertEqual(attachment["authority_effect"], "NONE")

    def test_attachment_fails_closed_on_wrong_packet(self) -> None:
        completion = self._completion()
        receipt = build_canonical_completion_latency_receipt(
            programme_id=completion.programme_id,
            packet_id="WRONG-PACKET",
            completion_receipt_id=completion.receipt_id,
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(Path(tmp))
            with self.assertRaises(ValueError):
                store.put_completion_with_devobs(completion, receipt)


if __name__ == "__main__":
    unittest.main()
