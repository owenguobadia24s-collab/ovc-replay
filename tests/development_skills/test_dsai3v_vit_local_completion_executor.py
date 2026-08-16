from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.development.skills.vit_local_completion_executor import (
    build_live_transaction_freeze,
    complete_frozen_transaction,
    decode_freeze_marker,
    encode_freeze_marker,
)
from ovc.development.skills.vit_materialisation import ReceiptStore
from ovc.development.skills.vit_routing import build_vit_lineage_record


class Dsai3vVitLocalCompletionExecutorTests(unittest.TestCase):
    def _lineage(self):
        return build_vit_lineage_record(
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

    def _freeze(self):
        return build_live_transaction_freeze(
            lineage_record=self._lineage(),
            pr_number=123,
            base_sha="e" * 40,
            head_sha="f" * 40,
            base_tree="c" * 40,
            head_tree="d" * 40,
            workflow_run_id="9001",
            run_attempt="1",
        )

    def test_freeze_marker_round_trip_is_exact_and_deterministic(self) -> None:
        first = self._freeze()
        second = self._freeze()
        self.assertEqual(first, second)
        self.assertEqual(first["transaction_id"], second["transaction_id"])
        decoded = decode_freeze_marker(encode_freeze_marker(first))
        self.assertEqual(dict(decoded), first)
        self.assertEqual(
            first["transaction"]["materialisation_profile"], "LIVE_PHYSICAL_MAIN"
        )
        self.assertEqual(
            first["transaction"]["expected_result_tree"], "d" * 40
        )

    def test_post_merge_recovery_persists_and_proves_four_receipts(self) -> None:
        freeze = self._freeze()
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            proof = complete_frozen_transaction(
                freeze=freeze,
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
            )
            self.assertTrue(proof["exact_tree_equal"])
            self.assertTrue(proof["four_content_addressed_receipts_present"])
            self.assertEqual(len(set(proof["receipt_ids"].values())), 4)
            for receipt_id in proof["receipt_ids"].values():
                self.assertTrue((Path(tmp) / f"{receipt_id}.json").is_file())
            devobs = json.loads(
                (
                    Path(tmp)
                    / f"{proof['receipt_ids']['development_latency_receipt_id']}.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(devobs["latency"]["status"], "UNAVAILABLE")
            self.assertEqual(devobs["async_assurance"]["status"], "UNAVAILABLE")
            self.assertEqual(devobs["siq"]["ready_pass_count"], 1)
            self.assertTrue(
                (Path(tmp) / "transactions" / f"{proof['transaction_id']}.json").is_file()
            )
            self.assertTrue(
                (Path(tmp) / "proofs" / f"{proof['proof_id']}.json").is_file()
            )

    def test_freeze_rejects_tree_drift(self) -> None:
        with self.assertRaisesRegex(Exception, "LIVE_COMPLETION_RESULT_TREE_MISMATCH"):
            build_live_transaction_freeze(
                lineage_record=self._lineage(),
                pr_number=123,
                base_sha="e" * 40,
                head_sha="f" * 40,
                base_tree="c" * 40,
                head_tree="0" * 40,
                workflow_run_id="9001",
                run_attempt="1",
            )


if __name__ == "__main__":
    unittest.main()
