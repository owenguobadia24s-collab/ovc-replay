from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from ovc.development.skills.vit_core import (
    DependencyFrontier,
    IntegrationAuthorityManifest,
    PacketIntegrationPayload,
    VitContractError,
)
from ovc.development.skills.vit_materialisation import ReceiptStore
from ovc.development.skills.vit_rehearsal import run_isolated_rehearsal


class DsaiVitV03Wp9Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "q5@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Q5 Fixture"], check=True)
        (self.repo / "a.txt").write_text("a\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "a.txt"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", "base"], check=True)
        self.base = subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True).strip()
        self.blob = subprocess.check_output(
            ["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"],
            input="b\n",
            text=True,
        ).strip()
        auth = IntegrationAuthorityManifest(
            "PLAN",
            "WP9",
            "G9",
            "AUTO_EXECUTABLE",
            "NONE",
            ("ratified-plan",),
            ("DSAI3V-G-VIT-PILOT",),
        )
        dep = DependencyFrontier((), "NONE")
        self.payload = PacketIntegrationPayload(
            "P",
            "WP9",
            ({"op": "ADD", "path": "b.txt", "blob_sha": self.blob, "mode": "100644"},),
            auth,
            dep,
            {"next_packet": "DSAI3V-G-VIT-PILOT"},
        )
        self.receipts = ReceiptStore(Path(self.tmp.name) / "receipts")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_isolated_rehearsal_materialises_exact_tree_and_receipts(self) -> None:
        result = run_isolated_rehearsal(self.repo, self.base, self.payload, self.receipts)
        self.assertEqual(result.outcome, "MATERIALISED_EQUIVALENT")
        self.assertEqual(result.predicted_result_tree, result.observed_tree)
        self.assertIsNotNone(result.materialisation_receipt_id)
        self.assertIsNotNone(result.completion_receipt_id)
        self.assertIsNotNone(result.vit_generation_id)
        self.assertEqual(result.gateway_disposition, "SIQ_GATEWAY_ISOLATED_LEASE_VALID")
        self.assertFalse(result.physical_main_touched)
        self.assertFalse(result.closeout_churn_detected)

    def test_crash_before_and_after_write_are_deterministically_recoverable(self) -> None:
        before = run_isolated_rehearsal(
            self.repo,
            self.base,
            self.payload,
            self.receipts,
            crash_point="BEFORE_WRITE",
        )
        self.assertEqual(before.recovery_disposition, "WRITE_NOT_EFFECTIVE_RETRYABLE")
        after = run_isolated_rehearsal(
            self.repo,
            self.base,
            self.payload,
            self.receipts,
            crash_point="POST_WRITE_PRE_RECEIPT",
        )
        self.assertEqual(after.recovery_disposition, "WRITE_EFFECTIVE_RECEIPT_RECOVERY_REQUIRED")
        self.assertEqual(after.predicted_result_tree, after.observed_tree)

    def test_receipt_store_loss_stops_before_successor(self) -> None:
        result = run_isolated_rehearsal(
            self.repo,
            self.base,
            self.payload,
            self.receipts,
            receipt_store_available=False,
        )
        self.assertEqual(result.outcome, "RECEIPT_STORE_UNAVAILABLE_STOP")
        self.assertEqual(result.recovery_disposition, "STOP_BEFORE_NEXT_TRANSACTION")
        self.assertIsNone(result.completion_receipt_id)

    def test_grt_or_siq_failure_fails_closed(self) -> None:
        with self.assertRaisesRegex(VitContractError, "GRT_CONFORMANCE_FAIL"):
            run_isolated_rehearsal(self.repo, self.base, self.payload, self.receipts, grt_pass=False)
        with self.assertRaisesRegex(VitContractError, "LEASE_UNAVAILABLE"):
            run_isolated_rehearsal(self.repo, self.base, self.payload, self.receipts, siq_ready=False)

    def test_retry_is_idempotent_and_does_not_duplicate_effective_write(self) -> None:
        first = run_isolated_rehearsal(self.repo, self.base, self.payload, self.receipts)
        second = run_isolated_rehearsal(self.repo, self.base, self.payload, self.receipts)
        self.assertEqual(first.observed_commit, second.observed_commit)
        self.assertEqual(first.observed_tree, second.observed_tree)
        self.assertEqual(first.materialisation_receipt_id, second.materialisation_receipt_id)
        self.assertEqual(first.completion_receipt_id, second.completion_receipt_id)
        self.assertEqual(first.vit_generation_id, second.vit_generation_id)
        self.assertFalse(first.physical_main_touched)
        self.assertFalse(second.physical_main_touched)

    def test_post_receipt_crash_retries_without_lost_or_phantom_completion(self) -> None:
        crashed = run_isolated_rehearsal(
            self.repo,
            self.base,
            self.payload,
            self.receipts,
            crash_point="POST_RECEIPT_PRE_SUCCESSOR",
        )
        self.assertEqual(crashed.outcome, "CRASH_POST_RECEIPT_PRE_SUCCESSOR")
        self.assertIsNotNone(crashed.materialisation_receipt_id)
        self.assertIsNone(crashed.completion_receipt_id)
        self.assertEqual(crashed.recovery_disposition, "RECEIPT_RECOVERABLE")

        recovered = run_isolated_rehearsal(self.repo, self.base, self.payload, self.receipts)
        self.assertEqual(crashed.materialisation_receipt_id, recovered.materialisation_receipt_id)
        self.assertIsNotNone(recovered.completion_receipt_id)
        index = self.receipts.rebuild_index()
        completion_key = self.receipts.packet_completion_generation_index_key(
            programme_id=self.payload.programme_id,
            packet_id=self.payload.packet_id,
            vit_generation_id=str(recovered.vit_generation_id),
        )
        self.assertIn(completion_key, index)

    def test_closeout_uses_receipt_path_without_second_branch_churn(self) -> None:
        result = run_isolated_rehearsal(self.repo, self.base, self.payload, self.receipts)
        self.assertEqual(result.outcome, "MATERIALISED_EQUIVALENT")
        current_head = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True
        ).strip()
        refs = subprocess.check_output(
            ["git", "-C", str(self.repo), "for-each-ref", "--format=%(refname)", "refs/heads"],
            text=True,
        ).splitlines()
        self.assertEqual(current_head, self.base)
        self.assertIn("refs/heads/vit-q5-isolated", refs)
        self.assertFalse(any("closeout" in ref.lower() for ref in refs))
        self.assertFalse(result.closeout_churn_detected)


if __name__ == "__main__":
    unittest.main()
