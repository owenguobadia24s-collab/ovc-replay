from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.development.skills.vit_completion_closeout import (
    persist_non_churning_completion_closeout,
)
from ovc.development.skills.vit_completion_runtime import persist_physical_completion
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import (
    PhysicalMaterialisationTransaction,
    ReceiptStore,
)


class Dsai3vVitCompletionCloseoutTests(unittest.TestCase):
    def _transaction(self, *, generation: str = "generation-1") -> PhysicalMaterialisationTransaction:
        return PhysicalMaterialisationTransaction(
            vit_generation_id=generation,
            ticket_id="ticket-1",
            train_generation_id="train-1",
            expected_predecessor_commit="a" * 40,
            expected_predecessor_tree="b" * 40,
            expected_result_tree="c" * 40,
            authority_frontier_id="authority-1",
            assurance_frontier_id="assurance-1",
            materialisation_profile="LIVE_PHYSICAL_MAIN",
        )

    def _proof(self, store: ReceiptStore, *, next_packet: str | None = "WP2", generation: str = "generation-1") -> dict[str, object]:
        transaction = self._transaction(generation=generation)
        result = persist_physical_completion(
            transaction=transaction,
            observed_commit="d" * 40,
            observed_tree="c" * 40,
            programme_id="OVC-TEST-PROGRAMME",
            packet_id="WP1",
            implementation_ref="impl-ref",
            qa_ref="qa-ref",
            gate_decision_ref="gate-ref",
            payload_id="payload-1",
            next_packet=next_packet,
            receipt_store=store,
        )
        return {
            "transaction_id": transaction.transaction_id,
            "exact_tree_equal": True,
            "four_content_addressed_receipts_present": True,
            "receipt_ids": {
                "materialisation_receipt_id": result["materialisation_receipt_id"],
                "completion_receipt_id": result["completion_receipt_id"],
                "development_latency_receipt_id": result["development_latency_receipt_id"],
                "attachment_id": result["attachment_id"],
            },
        }

    def test_successful_physical_completion_becomes_effectively_completed_without_git_closeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            closeout = persist_non_churning_completion_closeout(
                receipt_store=store,
                proof=self._proof(store),
            )
            self.assertEqual(closeout["status"], "COMPLETED")
            self.assertFalse(closeout["ordinary_closeout_pr_required"])
            self.assertFalse(closeout["canonical_git_state_mutated"])
            state_path = Path(tmp) / "completion-state" / f"{closeout['completion_state_id']}.json"
            self.assertTrue(state_path.is_file())
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "COMPLETED")
            self.assertFalse(state["ordinary_closeout_pr_required"])

    def test_repeated_completion_and_successor_release_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            proof = self._proof(store)
            first = persist_non_churning_completion_closeout(receipt_store=store, proof=proof)
            second = persist_non_churning_completion_closeout(receipt_store=store, proof=proof)
            self.assertEqual(first, second)
            self.assertEqual(first["successor_release_status"], "RELEASED_TO_AUTHORITY_RESOLVER")
            releases = list((Path(tmp) / "successor-releases").glob("*.json"))
            self.assertEqual(len(releases), 1)
            release = json.loads(releases[0].read_text(encoding="utf-8"))
            self.assertFalse(release["execution_started"])
            self.assertFalse(release["authority_inferred"])

    def test_terminal_packet_creates_no_successor_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            closeout = persist_non_churning_completion_closeout(
                receipt_store=store,
                proof=self._proof(store, next_packet=None),
            )
            self.assertEqual(closeout["successor_release_status"], "PROGRAMME_TERMINAL")
            self.assertIsNone(closeout["successor_release_id"])
            self.assertFalse((Path(tmp) / "successor-releases").exists())

    def test_duplicate_effective_packet_completion_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            first = self._proof(store, generation="generation-1")
            persist_non_churning_completion_closeout(receipt_store=store, proof=first)
            second = self._proof(store, generation="generation-2")
            with self.assertRaisesRegex(VitContractError, "VIT_DUPLICATE_EFFECTIVE_PACKET_COMPLETION"):
                persist_non_churning_completion_closeout(receipt_store=store, proof=second)

    def test_unverified_tree_cannot_advance_effective_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            proof = self._proof(store)
            proof["exact_tree_equal"] = False
            with self.assertRaisesRegex(VitContractError, "POST_WRITE_TREE_MISMATCH"):
                persist_non_churning_completion_closeout(receipt_store=store, proof=proof)
            self.assertFalse((Path(tmp) / "completion-state").exists())


if __name__ == "__main__":
    unittest.main()
