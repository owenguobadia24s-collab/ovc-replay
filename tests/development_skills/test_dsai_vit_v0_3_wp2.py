from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from ovc.development.skills.vit_apply import (
    AuthorizedExternalMainAdvanceReceipt,
    apply_payload_reference,
    tree_content_diagnostic_fingerprint,
    validate_external_main_advance,
)
from ovc.development.skills.vit_core import AuthorizedMainWriter, DependencyFrontier, IntegrationAuthorityManifest, PacketIntegrationPayload

class DsaiVitV03Wp2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        subprocess.run(["git","init","-q",str(self.repo)], check=True)
        subprocess.run(["git","-C",str(self.repo),"config","user.email","vit@example.invalid"], check=True)
        subprocess.run(["git","-C",str(self.repo),"config","user.name","VIT Fixture"], check=True)
        (self.repo/"a.txt").write_text("a\n", encoding="utf-8")
        subprocess.run(["git","-C",str(self.repo),"add","a.txt"], check=True)
        subprocess.run(["git","-C",str(self.repo),"commit","-q","-m","base"], check=True)
        self.base_commit = subprocess.check_output(["git","-C",str(self.repo),"rev-parse","HEAD"], text=True).strip()
        self.base_tree = subprocess.check_output(["git","-C",str(self.repo),"rev-parse","HEAD^{tree}"], text=True).strip()
        self.auth = IntegrationAuthorityManifest("PLAN","WP2","G2","AUTO_EXECUTABLE","NONE",("source",))
        self.dep = DependencyFrontier((), "NONE")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _blob(self, content: str) -> str:
        return subprocess.check_output(["git","-C",str(self.repo),"hash-object","-w","--stdin"], input=content, text=True).strip()

    def _pip(self, changes):
        return PacketIntegrationPayload("P","WP2",tuple(changes),self.auth,self.dep,{})

    def test_reference_add_modify_delete_is_deterministic(self) -> None:
        b = self._blob("b\n")
        receipt1 = apply_payload_reference(self.repo, self.base_tree, self._pip(({"op":"ADD","path":"b.txt","blob_sha":b,"mode":"100644"},)))
        receipt2 = apply_payload_reference(self.repo, self.base_tree, self._pip(({"op":"ADD","path":"b.txt","blob_sha":b,"mode":"100644"},)))
        self.assertFalse(receipt1.failures)
        self.assertEqual(receipt1.result_tree, receipt2.result_tree)
        self.assertEqual(receipt1.receipt_id, receipt2.receipt_id)

    def test_duplicate_and_unsafe_path_fail_closed(self) -> None:
        b = self._blob("b\n")
        receipt = apply_payload_reference(self.repo, self.base_tree, self._pip((
            {"op":"ADD","path":"../escape","blob_sha":b,"mode":"100644"},
            {"op":"ADD","path":"x","blob_sha":b,"mode":"100644"},
            {"op":"MODIFY","path":"x","blob_sha":b,"mode":"100644"},
        )))
        self.assertIsNone(receipt.result_tree)
        self.assertEqual({f.reason_code for f in receipt.failures}, {"INPUT_PRECONDITION_MISMATCH","CONTENT_CONFLICT"})

    def test_diagnostic_fingerprint_tracks_tree_content_not_commit_metadata(self) -> None:
        first = tree_content_diagnostic_fingerprint(self.repo, "HEAD^{tree}")
        subprocess.run(["git","-C",str(self.repo),"commit","--allow-empty","-q","-m","metadata"], check=True)
        second = tree_content_diagnostic_fingerprint(self.repo, "HEAD^{tree}")
        self.assertEqual(first, second)

    def test_external_main_receipt_requires_exact_registered_authority(self) -> None:
        writer = AuthorizedMainWriter("SIQ", ("GOVERNED_EXTERNAL_INTEGRATION",), ("AUTH",), True)
        receipt = AuthorizedExternalMainAdvanceReceipt("SIQ","AUTH",self.base_commit,self.base_tree,"b"*40,"c"*40,"GOVERNED_EXTERNAL_INTEGRATION",(),"now","sig")
        self.assertEqual(validate_external_main_advance(receipt, (writer,), self.base_commit, self.base_tree), "EXTERNAL_MAIN_REANCHOR")
        stale = AuthorizedExternalMainAdvanceReceipt("SIQ","AUTH","d"*40,self.base_tree,"b"*40,"c"*40,"GOVERNED_EXTERNAL_INTEGRATION",(),"now","sig")
        self.assertEqual(validate_external_main_advance(stale, (writer,), self.base_commit, self.base_tree), "REPOSITORY_INTEGRITY_INCIDENT")
        unknown = AuthorizedExternalMainAdvanceReceipt("OTHER","AUTH",self.base_commit,self.base_tree,"b"*40,"c"*40,"GOVERNED_EXTERNAL_INTEGRATION",(),"now","sig")
        self.assertEqual(validate_external_main_advance(unknown, (writer,), self.base_commit, self.base_tree), "REPOSITORY_INTEGRITY_INCIDENT")

if __name__ == "__main__":
    unittest.main()
