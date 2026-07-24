from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from ovc_evidence_store.__main__ import main
from ovc_evidence_store.manifest import (
    EvidenceStoreError,
    build_manifest,
    canonical_json_bytes,
    load_manifest,
    remote_keys,
    validate_manifest,
    verify_local,
)
from ovc_evidence_store.remote import upload, verify_remote


class EvidenceStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.root = self.base / "release"
        self.root.mkdir()
        self.manifest_path = self.base / "release-manifest.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def build(self, **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "root": self.root,
            "output": self.manifest_path,
            "release_id": "release-2026-07",
            "manifest_id": "manifest-001",
            "bucket": "ovc-evidence",
            "prefix": "locked/ovc",
            "authority_state": "ratified",
            "repository_commit": "0123456789abcdef",
            "source_ref": "refs/heads/main",
        }
        arguments.update(overrides)
        return build_manifest(**arguments)  # type: ignore[arg-type]

    def test_build_is_deterministic_and_records_full_bytes(self) -> None:
        (self.root / "z.bin").write_bytes(b"\x00\xff")
        nested = self.root / "a"
        nested.mkdir()
        (nested / "first.txt").write_bytes(b"first\r\n")
        first = self.build()
        first_bytes = self.manifest_path.read_bytes()
        second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(first_bytes, self.manifest_path.read_bytes())
        self.assertEqual([item["path"] for item in first["files"]], ["a/first.txt", "z.bin"])
        self.assertEqual(first["files"][0]["size"], 7)
        self.assertEqual(
            first["files"][0]["sha256"], hashlib.sha256(b"first\r\n").hexdigest()
        )
        self.assertEqual(first_bytes, canonical_json_bytes(first))
        self.assertFalse(any(self.base.glob(".release-manifest.json.*.tmp")))

    def test_output_inside_root_is_not_included(self) -> None:
        self.manifest_path = self.root / "manifest.json"
        (self.root / "evidence.txt").write_text("evidence", encoding="utf-8")
        self.build()
        rebuilt = self.build()
        self.assertEqual([item["path"] for item in rebuilt["files"]], ["evidence.txt"])

    def test_empty_release_is_valid(self) -> None:
        document = self.build()
        self.assertEqual(document["files"], [])
        verify_local(document, self.root)

    def test_unicode_nfc_name_round_trips(self) -> None:
        name = "café-東京.txt"
        (self.root / name).write_text("évidence", encoding="utf-8")
        document = self.build()
        self.assertEqual(document["files"][0]["path"], name)
        self.assertEqual(load_manifest(self.manifest_path), document)
        verify_local(document, self.root)

    def test_local_tampering_is_detected(self) -> None:
        target = self.root / "evidence.bin"
        target.write_bytes(b"original")
        document = self.build()
        target.write_bytes(b"tampered")
        with self.assertRaisesRegex(EvidenceStoreError, "mismatch"):
            verify_local(document, self.root)

    def test_missing_local_file_is_detected(self) -> None:
        target = self.root / "evidence.bin"
        target.write_bytes(b"original")
        document = self.build()
        target.unlink()
        with self.assertRaisesRegex(EvidenceStoreError, "missing|inaccessible"):
            verify_local(document, self.root)

    def test_duplicate_paths_are_rejected(self) -> None:
        digest = hashlib.sha256(b"x").hexdigest()
        document = self.build()
        document["files"] = [
            {"path": "A.txt", "sha256": digest, "size": 1},
            {"path": "a.txt", "sha256": digest, "size": 1},
        ]
        with self.assertRaisesRegex(EvidenceStoreError, "duplicate/colliding"):
            validate_manifest(document)

    def test_path_traversal_and_noncanonical_paths_are_rejected(self) -> None:
        digest = hashlib.sha256(b"x").hexdigest()
        for unsafe in ("../x", "a/../x", "/absolute", "C:/x", r"a\x"):
            with self.subTest(path=unsafe):
                document = self.build()
                document["files"] = [{"path": unsafe, "sha256": digest, "size": 1}]
                with self.assertRaises(EvidenceStoreError):
                    validate_manifest(document)

    def test_non_nfc_path_is_rejected(self) -> None:
        document = self.build()
        document["files"] = [{
            "path": "cafe\u0301.txt",
            "sha256": hashlib.sha256(b"").hexdigest(),
            "size": 0,
        }]
        with self.assertRaisesRegex(EvidenceStoreError, "NFC"):
            validate_manifest(document)

    def test_remote_layout_is_collision_bounded(self) -> None:
        (self.root / "nested").mkdir()
        (self.root / "nested" / "x.txt").write_bytes(b"x")
        document = self.build()
        manifest_key, keys = remote_keys(document)
        base = "locked/ovc/releases/release-2026-07/manifest-001"
        self.assertEqual(manifest_key, f"{base}/manifest.json")
        self.assertEqual(keys["nested/x.txt"], f"{base}/files/nested/x.txt")

    def test_upload_verifies_local_then_uses_immutable_copyto(self) -> None:
        target = self.root / "x.txt"
        target.write_bytes(b"x")
        document = self.build()
        calls: list[list[str]] = []

        def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, b"", b"")

        upload(document, self.manifest_path, self.root, "r2", runner=runner)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0:3], ["rclone", "copyto", "--immutable"])
        self.assertTrue(calls[0][-1].startswith("r2:locked/ovc/releases/"))
        self.assertTrue(calls[1][-1].endswith("/manifest.json"))

    def test_upload_does_not_call_rclone_after_local_tampering(self) -> None:
        target = self.root / "x.txt"
        target.write_bytes(b"x")
        document = self.build()
        target.write_bytes(b"y")
        with patch("subprocess.run") as runner:
            with self.assertRaises(EvidenceStoreError):
                upload(document, self.manifest_path, self.root, "r2", runner=runner)
        runner.assert_not_called()

    def test_remote_full_readback_succeeds(self) -> None:
        target = self.root / "x.bin"
        target.write_bytes(b"\x00remote\xff")
        document = self.build()
        objects = [
            self.manifest_path.read_bytes(),
            target.read_bytes(),
        ]

        def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(args, 0, objects.pop(0), b"")

        verify_remote(document, self.manifest_path, "r2:", runner=runner)
        self.assertEqual(objects, [])

    def test_remote_hash_mismatch_is_detected(self) -> None:
        (self.root / "x.txt").write_bytes(b"good")
        document = self.build()
        objects = [self.manifest_path.read_bytes(), b"evil"]

        def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(args, 0, objects.pop(0), b"")

        with self.assertRaisesRegex(EvidenceStoreError, "remote SHA-256 mismatch"):
            verify_remote(document, self.manifest_path, "r2", runner=runner)

    def test_rclone_failure_has_clear_error(self) -> None:
        document = self.build()

        def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(args, 9, b"", b"remote unavailable")

        with self.assertRaisesRegex(EvidenceStoreError, "exit code 9.*remote unavailable"):
            verify_remote(document, self.manifest_path, "r2", runner=runner)

    def test_cli_returns_nonzero_for_failure(self) -> None:
        exit_code = main([
            "verify-local",
            "--manifest", str(self.base / "missing.json"),
            "--root", str(self.root),
        ])
        self.assertNotEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
