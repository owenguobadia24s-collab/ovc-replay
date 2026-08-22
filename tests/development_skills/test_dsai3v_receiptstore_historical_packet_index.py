from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import PacketCompletionReceipt, ReceiptStore


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = (
    ROOT / "fixtures/development_skills/receipt_store_historical_packet_collision"
)


class ReceiptStoreHistoricalPacketIndexTests(unittest.TestCase):
    def test_historical_packet_completions_are_valid_and_generation_qualified(self) -> None:
        fixtures: list[tuple[Path, PacketCompletionReceipt]] = []
        for source in sorted(FIXTURE_ROOT.glob("*.json")):
            raw = json.loads(source.read_bytes())
            receipt = PacketCompletionReceipt(**raw)
            self.assertEqual(receipt.receipt_id, source.stem)
            self.assertEqual(canonical_sha256(raw), source.stem)
            self.assertEqual(
                source.read_text(encoding="utf-8").rstrip("\n"),
                json.dumps(raw, sort_keys=True, separators=(",", ":")),
            )
            fixtures.append((source, receipt))

        self.assertEqual(len(fixtures), 2)
        left, right = (receipt for _, receipt in fixtures)
        self.assertEqual(left.programme_id, right.programme_id)
        self.assertEqual(left.packet_id, right.packet_id)
        self.assertNotEqual(left.payload_id, right.payload_id)
        self.assertNotEqual(left.vit_generation_id, right.vit_generation_id)
        self.assertNotEqual(left.implementation_ref, right.implementation_ref)
        self.assertNotEqual(left.qa_ref, right.qa_ref)
        self.assertNotEqual(left.gate_decision_ref, right.gate_decision_ref)
        self.assertNotEqual(left.materialisation_receipt_id, right.materialisation_receipt_id)
        self.assertNotEqual(left.next_packet, right.next_packet)

        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            for _, receipt in fixtures:
                store.put(receipt, receipt.receipt_id)
            index = store.rebuild_index()

            self.assertNotIn(f"packet_id:{left.packet_id}", index)
            for source, receipt in fixtures:
                key = store.packet_completion_generation_index_key(
                    programme_id=receipt.programme_id,
                    packet_id=receipt.packet_id,
                    vit_generation_id=receipt.vit_generation_id,
                )
                self.assertEqual(index[key], source.name)

    def test_genuinely_unique_transaction_identity_collision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            for observed_commit in ("a" * 40, "b" * 40):
                record = {
                    "transaction_id": "transaction:unique",
                    "observed_commit": observed_commit,
                }
                store.put_record(record, canonical_sha256(record))

            with self.assertRaisesRegex(VitContractError, "VIT_LEDGER_INTEGRITY_FAIL"):
                store.rebuild_index()

    def test_same_generation_qualified_completion_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            for payload_id in ("payload:a", "payload:b"):
                receipt = PacketCompletionReceipt(
                    programme_id="programme",
                    packet_id="packet",
                    implementation_ref=f"implementation:{payload_id}",
                    qa_ref="qa",
                    gate_decision_ref="gate",
                    payload_id=payload_id,
                    vit_generation_id="generation:unique",
                    materialisation_receipt_id=f"materialisation:{payload_id}",
                    next_packet=None,
                )
                store.put(receipt, receipt.receipt_id)

            with self.assertRaisesRegex(VitContractError, "VIT_LEDGER_INTEGRITY_FAIL"):
                store.rebuild_index()

    def test_attachment_identity_collisions_remain_fail_closed(self) -> None:
        for shared_field in (
            "completion_receipt_id",
            "development_latency_receipt_id",
        ):
            with self.subTest(shared_field=shared_field), tempfile.TemporaryDirectory() as tmp:
                store = ReceiptStore(tmp)
                for suffix in ("a", "b"):
                    record = {
                        "schema": "ovc-dsai3v-completion-observability-attachment/v1",
                        "completion_receipt_id": f"completion:{suffix}",
                        "development_latency_receipt_id": f"latency:{suffix}",
                    }
                    record[shared_field] = "shared-genuinely-unique-identity"
                    store.put_record(record, canonical_sha256(record))

                with self.assertRaisesRegex(VitContractError, "VIT_LEDGER_INTEGRITY_FAIL"):
                    store.rebuild_index()


if __name__ == "__main__":
    unittest.main()
