from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest, PacketIntegrationPayload, VitContractError
from ovc.development.skills.vit_materialisation import ReceiptStore
from ovc.development.skills.vit_rehearsal import run_isolated_rehearsal


class DsaiVitV03Wp9Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        subprocess.run(["git","init","-q",str(self.repo)],check=True)
        subprocess.run(["git","-C",str(self.repo),"config","user.email","q5@example.invalid"],check=True)
        subprocess.run(["git","-C",str(self.repo),"config","user.name","Q5 Fixture"],check=True)
        (self.repo/"a.txt").write_text("a\n",encoding="utf-8")
        subprocess.run(["git","-C",str(self.repo),"add","a.txt"],check=True)
        subprocess.run(["git","-C",str(self.repo),"commit","-q","-m","base"],check=True)
        self.base = subprocess.check_output(["git","-C",str(self.repo),"rev-parse","HEAD"],text=True).strip()
        self.blob = subprocess.check_output(["git","-C",str(self.repo),"hash-object","-w","--stdin"],input="b\n",text=True).strip()
        auth = IntegrationAuthorityManifest("PLAN","WP9","G9","AUTO_EXECUTABLE","NONE",("ratified-plan",))
        dep = DependencyFrontier((),"NONE")
        self.payload = PacketIntegrationPayload("P","WP9",({"op":"ADD","path":"b.txt","blob_sha":self.blob,"mode":"100644"},),auth,dep,{"next_packet":"G-VIT-PILOT"})
        self.receipts = ReceiptStore(Path(self.tmp.name)/"receipts")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_isolated_rehearsal_materialises_exact_tree_and_receipts(self) -> None:
        result = run_isolated_rehearsal(self.repo,self.base,self.payload,self.receipts)
        self.assertEqual(result.outcome,"MATERIALISED_EQUIVALENT")
        self.assertEqual(result.predicted_result_tree,result.observed_tree)
        self.assertIsNotNone(result.materialisation_receipt_id)
        self.assertIsNotNone(result.completion_receipt_id)
        self.assertFalse(result.physical_main_touched)

    def test_crash_before_and_after_write_are_deterministically_recoverable(self) -> None:
        before = run_isolated_rehearsal(self.repo,self.base,self.payload,self.receipts,crash_point="BEFORE_WRITE")
        self.assertEqual(before.recovery_disposition,"WRITE_NOT_EFFECTIVE_RETRYABLE")
        after = run_isolated_rehearsal(self.repo,self.base,self.payload,self.receipts,crash_point="POST_WRITE_PRE_RECEIPT")
        self.assertEqual(after.recovery_disposition,"WRITE_EFFECTIVE_RECEIPT_RECOVERY_REQUIRED")
        self.assertEqual(after.predicted_result_tree,after.observed_tree)

    def test_receipt_store_loss_stops_before_successor(self) -> None:
        result = run_isolated_rehearsal(self.repo,self.base,self.payload,self.receipts,receipt_store_available=False)
        self.assertEqual(result.outcome,"RECEIPT_STORE_UNAVAILABLE_STOP")
        self.assertEqual(result.recovery_disposition,"STOP_BEFORE_NEXT_TRANSACTION")
        self.assertIsNone(result.completion_receipt_id)

    def test_grt_or_siq_failure_fails_closed(self) -> None:
        with self.assertRaises(VitContractError):
            run_isolated_rehearsal(self.repo,self.base,self.payload,self.receipts,grt_pass=False)
        with self.assertRaises(VitContractError):
            run_isolated_rehearsal(self.repo,self.base,self.payload,self.receipts,siq_ready=False)


if __name__ == "__main__":
    unittest.main()
