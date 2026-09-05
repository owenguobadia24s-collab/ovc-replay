from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.ci.vit_publish_completion_receipts import (
    RemoteReceiptPublishError,
    publish_receipt_tree,
)


class FakeRclone:
    def __init__(self, *, missing_stat: str = "null") -> None:
        self.remote: dict[str, bytes] = {}
        self.commands: list[list[str]] = []
        self.missing_stat = missing_stat

    def __call__(self, args, *, check, stdout, stderr):
        argv = list(args)
        self.commands.append(argv)
        command = argv[1]
        remote_ref = argv[-1]
        if command == "lsjson":
            if "--stat" not in argv or "--files-only" not in argv:
                raise AssertionError(f"receipt object probe must be file-only stat: {argv}")
            if remote_ref not in self.remote:
                if self.missing_stat == "directory":
                    payload = json.dumps({"IsDir": True, "Size": -1}).encode()
                    return subprocess.CompletedProcess(argv, 0, payload, b"")
                if self.missing_stat == "exit4":
                    return subprocess.CompletedProcess(argv, 4, b"", b"file not found")
                return subprocess.CompletedProcess(argv, 0, b"null", b"")
            payload = json.dumps({"IsDir": False, "Size": len(self.remote[remote_ref])}).encode()
            return subprocess.CompletedProcess(argv, 0, payload, b"")
        if command == "cat":
            if remote_ref not in self.remote:
                error = subprocess.CalledProcessError(4, argv, output=b"", stderr=b"file not found")
                if check:
                    raise error
                return subprocess.CompletedProcess(argv, 4, b"", b"file not found")
            return subprocess.CompletedProcess(argv, 0, self.remote[remote_ref], b"")
        if command == "copyto":
            local_path = Path(argv[-2])
            payload = local_path.read_bytes()
            if remote_ref in self.remote and self.remote[remote_ref] != payload:
                error = subprocess.CalledProcessError(1, argv, output=b"", stderr=b"immutable collision")
                if check:
                    raise error
                return subprocess.CompletedProcess(argv, 1, b"", b"immutable collision")
            self.remote[remote_ref] = payload
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        raise AssertionError(argv)


class RemoteReceiptPublisherTests(unittest.TestCase):
    def _root(self, base: Path) -> Path:
        root = base / "receipts"
        (root / "proofs").mkdir(parents=True)
        (root / "abc.json").write_text('{"a":1}', encoding="utf-8")
        (root / "proofs" / "proof.json").write_text('{"proof":true}', encoding="utf-8")
        return root

    def test_upload_then_identical_replay_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            fake = FakeRclone()
            first = publish_receipt_tree(
                local_root=root,
                remote="ovc_r2",
                prefix="ovc-evidence/development/vit-completion-receipts/v1",
                runner=fake,
            )
            self.assertEqual(first["object_count"], 2)
            self.assertEqual({row["mode"] for row in first["objects"]}, {"UPLOADED_AND_VERIFIED"})
            second = publish_receipt_tree(
                local_root=root,
                remote="ovc_r2",
                prefix="ovc-evidence/development/vit-completion-receipts/v1",
                runner=fake,
            )
            self.assertEqual({row["mode"] for row in second["objects"]}, {"EXISTING_IDENTICAL"})
            verbs = {argv[1] for argv in fake.commands}
            self.assertNotIn("delete", verbs)
            self.assertNotIn("purge", verbs)
            self.assertNotIn("move", verbs)

    def test_bucket_backend_missing_object_directory_sentinel_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            fake = FakeRclone(missing_stat="directory")
            report = publish_receipt_tree(
                local_root=root,
                remote="ovc_r2",
                prefix="ovc-evidence/development/vit-completion-receipts/v1",
                runner=fake,
            )
            self.assertEqual(report["object_count"], 2)
            self.assertEqual({row["mode"] for row in report["objects"]}, {"UPLOADED_AND_VERIFIED"})
            self.assertTrue(all("--files-only" in argv for argv in fake.commands if argv[1] == "lsjson"))

    def test_file_not_found_exit_code_four_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            fake = FakeRclone(missing_stat="exit4")
            report = publish_receipt_tree(
                local_root=root,
                remote="ovc_r2",
                prefix="ovc-evidence/development/vit-completion-receipts/v1",
                runner=fake,
            )
            self.assertEqual({row["mode"] for row in report["objects"]}, {"UPLOADED_AND_VERIFIED"})

    def test_existing_different_remote_object_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            fake = FakeRclone()
            ref = "ovc_r2:ovc-evidence/development/vit-completion-receipts/v1/abc.json"
            fake.remote[ref] = b"different"
            with self.assertRaisesRegex(RemoteReceiptPublishError, "REMOTE_RECEIPT_COLLISION"):
                publish_receipt_tree(
                    local_root=root,
                    remote="ovc_r2",
                    prefix="ovc-evidence/development/vit-completion-receipts/v1",
                    runner=fake,
                )

    def test_symlink_is_never_published(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            target = root / "abc.json"
            link = root / "linked.json"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlinks unavailable on this platform")
            with self.assertRaisesRegex(RemoteReceiptPublishError, "REMOTE_RECEIPT_SYMLINK_FORBIDDEN"):
                publish_receipt_tree(
                    local_root=root,
                    remote="ovc_r2",
                    prefix="ovc-evidence/development/vit-completion-receipts/v1",
                    runner=FakeRclone(),
                )

    def test_invalid_prefix_fails_before_remote_access(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            fake = FakeRclone()
            with self.assertRaisesRegex(RemoteReceiptPublishError, "REMOTE_RECEIPT_PREFIX_INVALID"):
                publish_receipt_tree(
                    local_root=root,
                    remote="ovc_r2",
                    prefix="../escape",
                    runner=fake,
                )
            self.assertEqual(fake.commands, [])


if __name__ == "__main__":
    unittest.main()
