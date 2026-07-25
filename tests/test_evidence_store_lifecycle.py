from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from ovc_evidence_store.external_root import resolve_external_root
from ovc_evidence_store.lifecycle import (
    PUBLICATION_APPROVAL_SCHEMA,
    build_workspace_inventory,
    freeze_release,
    init_workspace,
    manifest_sha256,
    validate_publication_approval,
    validate_supersession,
)
from ovc_evidence_store.manifest import EvidenceStoreError, build_manifest
from ovc_evidence_store.readiness import publication_readiness


SOURCE_COMMIT = "1" * 40


class EvidenceLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.repository = self.base / "repository"
        self.repository.mkdir()
        self.external = self.base / "external"
        self.external.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_external_root_requires_environment_variable(self) -> None:
        with self.assertRaisesRegex(EvidenceStoreError, "OVC_EXTERNAL_ARTIFACT_ROOT is not set"):
            resolve_external_root(repository_root=self.repository, environ={})

    def test_external_root_rejects_relative_and_repository_paths(self) -> None:
        with self.assertRaisesRegex(EvidenceStoreError, "absolute path"):
            resolve_external_root(
                repository_root=self.repository,
                environ={"OVC_EXTERNAL_ARTIFACT_ROOT": "relative/path"},
            )
        with self.assertRaisesRegex(EvidenceStoreError, "disjoint"):
            resolve_external_root(
                repository_root=self.repository,
                environ={"OVC_EXTERNAL_ARTIFACT_ROOT": str(self.repository / "payloads")},
                create=True,
            )

    def test_external_root_can_be_created_without_persisting_configuration(self) -> None:
        target = self.base / "new-external"
        resolved = resolve_external_root(
            repository_root=self.repository,
            environ={"OVC_EXTERNAL_ARTIFACT_ROOT": str(target)},
            create=True,
        )
        self.assertEqual(target.resolve(), resolved)
        self.assertTrue(resolved.is_dir())
        self.assertEqual([], list(self.repository.iterdir()))

    def test_init_workspace_creates_only_intake_and_workspace_planes(self) -> None:
        workspace = init_workspace(self.external, "workspace-001")
        self.assertTrue(workspace.is_dir())
        self.assertTrue((self.external / "intake").is_dir())
        self.assertTrue((self.external / "workspace").is_dir())
        self.assertFalse((self.external / "releases").exists())
        self.assertFalse((self.external / "receipts").exists())

    def test_init_workspace_rejects_duplicate_and_unsafe_ids(self) -> None:
        init_workspace(self.external, "workspace-001")
        with self.assertRaisesRegex(EvidenceStoreError, "already exists"):
            init_workspace(self.external, "workspace-001")
        for unsafe in ("../escape", "a/b", "", ".."):
            with self.subTest(identifier=unsafe):
                with self.assertRaises(EvidenceStoreError):
                    init_workspace(self.external, unsafe)

    def test_workspace_inventory_is_deterministic_and_byte_complete(self) -> None:
        workspace = init_workspace(self.external, "workspace-001")
        (workspace / "z.bin").write_bytes(b"\x00\xff")
        (workspace / "a").mkdir()
        (workspace / "a" / "x.txt").write_bytes(b"line\r\n")
        first = build_workspace_inventory(workspace, "workspace-001")
        second = build_workspace_inventory(workspace, "workspace-001")
        self.assertEqual(first, second)
        self.assertEqual(["a/x.txt", "z.bin"], [item["path"] for item in first["files"]])
        self.assertEqual([], first["unresolved"])

    def test_inventory_rejects_symlinks(self) -> None:
        workspace = init_workspace(self.external, "workspace-001")
        target = workspace / "target.txt"
        target.write_text("x", encoding="utf-8")
        link = workspace / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links unavailable")
        with self.assertRaisesRegex(EvidenceStoreError, "symbolic links"):
            build_workspace_inventory(workspace, "workspace-001")

    def test_freeze_release_requires_pass_and_exact_inventory(self) -> None:
        workspace = init_workspace(self.external, "workspace-001")
        (workspace / "payload.bin").write_bytes(b"payload")
        inventory = build_workspace_inventory(workspace, "workspace-001")
        with self.assertRaisesRegex(EvidenceStoreError, "qa-state PASS"):
            freeze_release(
                external_root=self.external,
                workspace_id="workspace-001",
                release_id="release-001",
                qa_state="WARN",
                inventory=inventory,
            )
        (workspace / "payload.bin").write_bytes(b"changed")
        with self.assertRaisesRegex(EvidenceStoreError, "approved inventory"):
            freeze_release(
                external_root=self.external,
                workspace_id="workspace-001",
                release_id="release-001",
                qa_state="PASS",
                inventory=inventory,
            )

    def test_freeze_release_copies_exact_bytes_and_refuses_overwrite(self) -> None:
        workspace = init_workspace(self.external, "workspace-001")
        (workspace / "nested").mkdir()
        (workspace / "nested" / "payload.bin").write_bytes(b"payload")
        inventory = build_workspace_inventory(workspace, "workspace-001")
        release, receipt_path, receipt = freeze_release(
            external_root=self.external,
            workspace_id="workspace-001",
            release_id="release-001",
            qa_state="PASS",
            inventory=inventory,
        )
        self.assertEqual(b"payload", (release / "nested" / "payload.bin").read_bytes())
        self.assertTrue(receipt_path.is_file())
        self.assertEqual(1, receipt["file_count"])
        self.assertEqual("DENIED", receipt["overwrite_policy"])
        with self.assertRaisesRegex(EvidenceStoreError, "already exists"):
            freeze_release(
                external_root=self.external,
                workspace_id="workspace-001",
                release_id="release-001",
                qa_state="PASS",
                inventory=inventory,
            )

    def test_supersession_validator_blocks_identity_reuse(self) -> None:
        existing = {"OPT-A.GBPUSD.2026H1.v1"}
        validate_supersession(
            new_release_id="OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
            predecessor_release_id="OPT-A.GBPUSD.2026H1.v1",
            existing_release_ids=existing,
            predecessor_disposition="SUPERSEDED_UNPUBLISHED",
        )
        with self.assertRaisesRegex(EvidenceStoreError, "reuse"):
            validate_supersession(
                new_release_id="OPT-A.GBPUSD.2026H1.v1",
                predecessor_release_id="OPT-A.GBPUSD.2026H1.v1",
                existing_release_ids=existing,
                predecessor_disposition="SUPERSEDED_UNPUBLISHED",
            )

    def _manifest_and_approval(self) -> tuple[Path, Path, Path, dict[str, object]]:
        release = self.base / "release"
        release.mkdir()
        (release / "payload.bin").write_bytes(b"payload")
        manifest_path = self.base / "manifest.json"
        manifest = build_manifest(
            root=release,
            output=manifest_path,
            release_id="OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
            manifest_id="MANIFEST.DISCOVERY.001",
            bucket="ovc-evidence",
            prefix="canonical",
            authority_state="CANDIDATE",
            repository_commit=SOURCE_COMMIT,
            source_ref="refs/heads/build/opt-a-v2-discovery-release",
        )
        approval = {
            "schema": PUBLICATION_APPROVAL_SCHEMA,
            "approval_id": "PUBAPP.DISCOVERY.001",
            "decision": "APPROVE",
            "release_id": manifest["release_id"],
            "manifest_id": manifest["manifest_id"],
            "manifest_sha256": manifest_sha256(manifest_path),
            "source_commit": SOURCE_COMMIT,
            "operator": "OVC operator",
            "decision_recorded_at": "2026-07-25T20:00:00Z",
            "rollback_note": "Do not activate selectors; stop on collision.",
        }
        approval_path = self.base / "approval.json"
        approval_path.write_text(json.dumps(approval), encoding="utf-8")
        return release, manifest_path, approval_path, manifest

    def test_publication_approval_binds_exact_manifest_and_source_commit(self) -> None:
        _, manifest_path, _, manifest = self._manifest_and_approval()
        approval = {
            "schema": PUBLICATION_APPROVAL_SCHEMA,
            "approval_id": "PUBAPP.DISCOVERY.001",
            "decision": "APPROVE",
            "release_id": manifest["release_id"],
            "manifest_id": manifest["manifest_id"],
            "manifest_sha256": manifest_sha256(manifest_path),
            "source_commit": SOURCE_COMMIT,
            "operator": "OVC operator",
            "decision_recorded_at": "2026-07-25T20:00:00Z",
            "rollback_note": "Stop without selector activation.",
        }
        validate_publication_approval(approval, manifest=manifest, manifest_path=manifest_path)
        approval["manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(EvidenceStoreError, "SHA-256 mismatch"):
            validate_publication_approval(approval, manifest=manifest, manifest_path=manifest_path)

    def test_readiness_can_reach_ready_without_remote_writes(self) -> None:
        release, manifest_path, approval_path, _ = self._manifest_and_approval()
        calls: list[list[str]] = []

        def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            calls.append(args)
            if args[:3] == ["git", "rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(args, 0, f"{SOURCE_COMMIT}\n".encode(), b"")
            if args[:2] == ["git", "status"]:
                return subprocess.CompletedProcess(args, 0, b"", b"")
            if args == ["rclone", "listremotes"]:
                return subprocess.CompletedProcess(args, 0, b"ovc_r2:\n", b"")
            if args[:2] == ["rclone", "lsjson"]:
                return subprocess.CompletedProcess(args, 3, b"", b"object not found")
            raise AssertionError(args)

        result = publication_readiness(
            release_root=release,
            manifest_path=manifest_path,
            approval_path=approval_path,
            repository_root=self.repository,
            remote="ovc_r2",
            bucket_lock_visible=True,
            runner=runner,
        )
        self.assertEqual("READY", result["overall_status"])
        self.assertFalse(result["side_effects_performed"])
        self.assertTrue(all("copyto" not in call for call in calls))
        self.assertTrue(all("upload" not in call for call in calls))

    def test_readiness_is_not_evaluable_without_remote_configuration(self) -> None:
        release, manifest_path, approval_path, _ = self._manifest_and_approval()

        def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            if args[:3] == ["git", "rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(args, 0, f"{SOURCE_COMMIT}\n".encode(), b"")
            if args[:2] == ["git", "status"]:
                return subprocess.CompletedProcess(args, 0, b"", b"")
            raise AssertionError(args)

        result = publication_readiness(
            release_root=release,
            manifest_path=manifest_path,
            approval_path=approval_path,
            repository_root=self.repository,
            remote=None,
            bucket_lock_visible=None,
            runner=runner,
        )
        self.assertEqual("NOT_EVALUABLE", result["overall_status"])
        self.assertEqual("NOT_EVALUABLE", result["checks"]["rclone_remote"])
        self.assertFalse(result["side_effects_performed"])

    def test_readiness_blocks_unmanifested_file_and_dirty_worktree(self) -> None:
        release, manifest_path, approval_path, _ = self._manifest_and_approval()
        (release / "extra.bin").write_bytes(b"extra")

        def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            if args[:3] == ["git", "rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(args, 0, f"{SOURCE_COMMIT}\n".encode(), b"")
            if args[:2] == ["git", "status"]:
                return subprocess.CompletedProcess(args, 0, b" M file.py\n", b"")
            raise AssertionError(args)

        result = publication_readiness(
            release_root=release,
            manifest_path=manifest_path,
            approval_path=approval_path,
            repository_root=self.repository,
            runner=runner,
        )
        self.assertEqual("BLOCKED", result["overall_status"])
        self.assertEqual("BLOCK", result["checks"]["inventory"])
        self.assertEqual("BLOCK", result["checks"]["git_worktree"])

    def test_readiness_detects_exact_remote_collision(self) -> None:
        release, manifest_path, approval_path, _ = self._manifest_and_approval()

        def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            if args[:3] == ["git", "rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(args, 0, f"{SOURCE_COMMIT}\n".encode(), b"")
            if args[:2] == ["git", "status"]:
                return subprocess.CompletedProcess(args, 0, b"", b"")
            if args == ["rclone", "listremotes"]:
                return subprocess.CompletedProcess(args, 0, b"ovc_r2:\n", b"")
            if args[:2] == ["rclone", "lsjson"]:
                return subprocess.CompletedProcess(args, 0, b"{}", b"")
            raise AssertionError(args)

        result = publication_readiness(
            release_root=release,
            manifest_path=manifest_path,
            approval_path=approval_path,
            repository_root=self.repository,
            remote="ovc_r2",
            bucket_lock_visible=True,
            runner=runner,
        )
        self.assertEqual("BLOCKED", result["overall_status"])
        self.assertEqual("BLOCK", result["checks"]["canonical_collision"])

    def test_no_function_writes_repository_or_remote_credentials(self) -> None:
        with patch.dict(os.environ, {"OVC_EXTERNAL_ARTIFACT_ROOT": str(self.external)}, clear=True):
            resolve_external_root(repository_root=self.repository)
            init_workspace(self.external, "workspace-001")
        self.assertFalse((self.repository / ".env").exists())
        self.assertFalse((self.repository / "rclone.conf").exists())
        self.assertFalse((self.repository / "credentials.json").exists())


if __name__ == "__main__":
    unittest.main()
