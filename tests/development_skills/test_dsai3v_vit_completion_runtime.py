from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.development.skills.vit_completion_runtime import (
    EXTERNAL_ARTIFACT_ROOT_ENV,
    EXTERNAL_RECEIPTS_RELATIVE_ROOT,
    RECEIPT_STORE_ROOT_ENV,
    persist_physical_completion,
    recover_effective_write_completion,
    resolve_receipt_store,
)
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import (
    PhysicalMaterialisationTransaction,
    ReceiptStore,
    materialisation_receipt,
)


class Dsai3vVitCompletionRuntimeTests(unittest.TestCase):
    def _transaction(self) -> PhysicalMaterialisationTransaction:
        return PhysicalMaterialisationTransaction(
            vit_generation_id="generation-1",
            ticket_id="ticket-1",
            train_generation_id="train-1",
            expected_predecessor_commit="a" * 40,
            expected_predecessor_tree="b" * 40,
            expected_result_tree="c" * 40,
            authority_frontier_id="authority-1",
            assurance_frontier_id="assurance-1",
            materialisation_profile="LIVE_PHYSICAL_MAIN",
        )

    def _kwargs(self, store: ReceiptStore) -> dict[str, object]:
        return {
            "programme_id": "OVC-TEST-PROGRAMME",
            "packet_id": "TEST-PACKET",
            "implementation_ref": "impl-ref",
            "qa_ref": "qa-ref",
            "gate_decision_ref": "gate-ref",
            "payload_id": "payload-1",
            "next_packet": None,
            "receipt_store": store,
            "siq_receipts": ({"schema": "siq/v1", "record_id": "siq-1", "status": "SIQ_READY"},),
        }

    def test_exact_live_completion_persists_materialisation_completion_devobs_and_attachment(self) -> None:
        transaction = self._transaction()
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            result = persist_physical_completion(
                transaction=transaction,
                observed_commit="d" * 40,
                observed_tree="c" * 40,
                **self._kwargs(store),
            )
            self.assertTrue(result["exact_tree_equal"])
            self.assertEqual(result["controller"], "DSAI_VIT_PHYSICAL_CONTROLLER")
            self.assertEqual(result["physical_gateway"], "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY")
            files = list(Path(tmp).glob("*.json"))
            self.assertEqual(len(files), 6)
            devobs = json.loads((Path(tmp) / f"{result['development_latency_receipt_id']}.json").read_text(encoding="utf-8"))
            self.assertEqual(devobs["latency"]["status"], "UNAVAILABLE")
            self.assertEqual(devobs["vit"]["exact_tree_equal_count"], 1)
            self.assertEqual(devobs["siq"]["ready_pass_count"], 1)

    def test_retry_is_idempotent(self) -> None:
        transaction = self._transaction()
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            first = persist_physical_completion(
                transaction=transaction,
                observed_commit="d" * 40,
                observed_tree="c" * 40,
                **self._kwargs(store),
            )
            second = persist_physical_completion(
                transaction=transaction,
                observed_commit="d" * 40,
                observed_tree="c" * 40,
                **self._kwargs(store),
            )
            self.assertEqual(first, second)
            self.assertEqual(len(list(Path(tmp).glob("*.json"))), 6)

    def test_recover_after_effective_write_and_partial_receipt_persistence(self) -> None:
        transaction = self._transaction()
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            materialisation = materialisation_receipt(transaction, "d" * 40, "c" * 40)
            store.put(materialisation, materialisation.receipt_id)
            result = recover_effective_write_completion(
                transaction=transaction,
                observed_commit="d" * 40,
                observed_tree="c" * 40,
                **self._kwargs(store),
            )
            self.assertEqual(result["status"], "WRITE_EFFECTIVE_RECEIPT_RECOVERED")
            self.assertEqual(result["materialisation_receipt_id"], materialisation.receipt_id)
            self.assertEqual(len(list(Path(tmp).glob("*.json"))), 6)

    def test_tree_mismatch_is_evidenced_and_fails_before_completion(self) -> None:
        transaction = self._transaction()
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            with self.assertRaisesRegex(VitContractError, "POST_WRITE_TREE_MISMATCH"):
                persist_physical_completion(
                    transaction=transaction,
                    observed_commit="d" * 40,
                    observed_tree="e" * 40,
                    **self._kwargs(store),
                )
            files = list(Path(tmp).glob("*.json"))
            self.assertEqual(len(files), 1)
            record = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(record["outcome"], "POST_WRITE_TREE_MISMATCH")

    def test_controller_and_gateway_are_not_replaceable_by_completion_binding(self) -> None:
        transaction = self._transaction()
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            with self.assertRaisesRegex(VitContractError, "PHYSICAL_MAIN_WRITER_IDENTITY_INVALID"):
                persist_physical_completion(
                    transaction=transaction,
                    observed_commit="d" * 40,
                    observed_tree="c" * 40,
                    controller="OTHER_WRITER",
                    **self._kwargs(store),
                )
            with self.assertRaisesRegex(VitContractError, "PHYSICAL_GATEWAY_INVALID"):
                persist_physical_completion(
                    transaction=transaction,
                    observed_commit="d" * 40,
                    observed_tree="c" * 40,
                    physical_gateway="OTHER_GATEWAY",
                    **self._kwargs(store),
                )

    def test_store_root_reuses_existing_external_receipts_namespace(self) -> None:
        with self.assertRaisesRegex(VitContractError, "DSAI3V_RECEIPT_STORE_ROOT_UNBOUND"):
            resolve_receipt_store(env={})
        with tempfile.TemporaryDirectory() as tmp:
            store = resolve_receipt_store(env={EXTERNAL_ARTIFACT_ROOT_ENV: tmp})
            self.assertEqual(store.root, Path(tmp) / EXTERNAL_RECEIPTS_RELATIVE_ROOT)
            self.assertTrue(store.root.is_dir())

    def test_dedicated_existing_runtime_binding_has_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as external_tmp, tempfile.TemporaryDirectory() as dedicated_tmp:
            store = resolve_receipt_store(
                env={
                    EXTERNAL_ARTIFACT_ROOT_ENV: external_tmp,
                    RECEIPT_STORE_ROOT_ENV: dedicated_tmp,
                }
            )
            self.assertEqual(store.root, Path(dedicated_tmp))


if __name__ == "__main__":
    unittest.main()
