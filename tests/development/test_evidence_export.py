from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from ovc.development.evidence_export import (
    EvidenceExportError,
    ExportFile,
    ExportRequest,
    build_plan,
    execute_export,
    load_profile,
    load_request,
)
from ovc.development.identity import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_EVIDENCE_EXPORT_PROFILE_v0_1.json"
PASS_FIXTURE = ROOT / "fixtures/development/evidence_export/export_request_pass_v0_1.json"
BLOCK_FIXTURE = ROOT / "fixtures/development/evidence_export/export_request_block_v0_1.json"
SOURCE_COMMIT = "544dc2f6477ce415321f9419a62586fcffa0d02c"


class EvidenceExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.external = self.base / "external"
        self.repo.mkdir()
        self.profile = load_profile(PROFILE_PATH)

    def write(self, logical_path: str, content: bytes) -> ExportFile:
        path = self.repo / logical_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return ExportFile(
            path=logical_path,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            role="PACKET",
        )

    def request(self, files: tuple[ExportFile, ...], *, export_id: str = "DA-EXPORT-TEST") -> ExportRequest:
        return ExportRequest(
            export_id=export_id,
            programme_id=self.profile.programme_id,
            profile_id=self.profile.profile_id,
            source_commit=SOURCE_COMMIT,
            files=files,
        )

    def assert_code(self, code: str, function, *args) -> EvidenceExportError:
        with self.assertRaises(EvidenceExportError) as caught:
            function(*args)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_closed_profile_and_request_fixtures(self) -> None:
        self.assertTrue(self.profile.active)
        self.assertEqual(self.profile.allowed_source_roots, (
            "docs/releases/development-acceleration-v0-1",
            "registries/development",
        ))
        passing = load_request(PASS_FIXTURE)
        self.assertEqual(passing.export_id, "DA-EXPORT-FIXTURE-PASS")
        self.assert_code("DUPLICATE_PATH", load_request, BLOCK_FIXTURE)

    def test_bundle_identity_and_manifest_ignore_request_order_and_export_label(self) -> None:
        first = self.write("docs/releases/development-acceleration-v0-1/test/b.json", b'{"b":2}\n')
        second = self.write("registries/development/a.yaml", b"a: 1\n")
        plan_a = build_plan(self.repo, self.external, self.request((first, second), export_id="DA-EXPORT-A"), self.profile)
        plan_b = build_plan(self.repo, self.external, self.request((second, first), export_id="DA-EXPORT-B"), self.profile)
        self.assertEqual(plan_a.bundle_id, plan_b.bundle_id)
        self.assertEqual(plan_a.manifest, plan_b.manifest)
        self.assertEqual([row["path"] for row in plan_a.manifest["files"]], sorted([first.path, second.path]))
        self.assertNotIn("export_id", plan_a.manifest)

    def test_exact_copy_canonical_manifest_and_source_preservation(self) -> None:
        content = b'{"status":"PASS"}\n'
        item = self.write("docs/releases/development-acceleration-v0-1/test/packet.json", content)
        source_before = (self.repo / item.path).read_bytes()
        plan = build_plan(self.repo, self.external, self.request((item,)), self.profile)
        result = execute_export(plan)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual((plan.destination / "files" / item.path).read_bytes(), content)
        self.assertEqual((self.repo / item.path).read_bytes(), source_before)
        manifest_bytes = (plan.destination / "manifest.json").read_bytes()
        self.assertEqual(manifest_bytes, canonical_json_bytes(plan.manifest) + b"\n")
        self.assertNotIn(str(self.repo).encode(), manifest_bytes)
        self.assertNotIn(str(self.external).encode(), manifest_bytes)

    def test_identical_retry_reuses_complete_bundle(self) -> None:
        item = self.write("registries/development/state.json", b'{"state":"READY"}\n')
        plan = build_plan(self.repo, self.external, self.request((item,)), self.profile)
        self.assertEqual(execute_export(plan)["status"], "PASS")
        self.assertEqual(execute_export(plan)["status"], "IDEMPOTENT_REUSE")

    def test_destination_mutation_or_manifest_change_blocks(self) -> None:
        item = self.write("registries/development/state.json", b'{"state":"READY"}\n')
        plan = build_plan(self.repo, self.external, self.request((item,)), self.profile)
        execute_export(plan)
        (plan.destination / "files" / item.path).write_bytes(b"mutated")
        self.assert_code("DESTINATION_COLLISION", execute_export, plan)

    def test_size_and_hash_mismatch_block_before_copy(self) -> None:
        item = self.write("registries/development/state.json", b"state: READY\n")
        wrong_size = replace(item, size_bytes=item.size_bytes + 1)
        wrong_hash = replace(item, sha256="0" * 64)
        self.assert_code("SIZE_MISMATCH", build_plan, self.repo, self.external, self.request((wrong_size,)), self.profile)
        self.assert_code("SHA256_MISMATCH", build_plan, self.repo, self.external, self.request((wrong_hash,)), self.profile)
        self.assertFalse(self.external.exists())

    def test_closed_request_rejects_traversal_extra_fields_and_boolean_size(self) -> None:
        base = {
            "schema": "ovc-compact-evidence-export-request/v1",
            "export_id": "DA-EXPORT-BAD",
            "programme_id": self.profile.programme_id,
            "profile_id": self.profile.profile_id,
            "source_commit": SOURCE_COMMIT,
            "files": [{"path": "../secret.json", "size_bytes": 0, "sha256": "0" * 64, "role": "PACKET"}],
        }
        request_path = self.base / "request.json"
        request_path.write_text(json.dumps(base))
        self.assert_code("UNSAFE_PATH", load_request, request_path)
        base["files"][0]["path"] = "registries/development/a.json"
        base["files"][0]["size_bytes"] = True
        request_path.write_text(json.dumps(base))
        self.assert_code("INVALID_SIZE", load_request, request_path)
        base["files"][0]["size_bytes"] = 0
        base["unexpected"] = True
        request_path.write_text(json.dumps(base))
        self.assert_code("CLOSED_SCHEMA_MISMATCH", load_request, request_path)

    def test_source_root_and_file_type_are_exactly_allowlisted(self) -> None:
        outside = self.write("docs/other/packet.json", b"{}\n")
        raw = self.write("docs/releases/development-acceleration-v0-1/test/population.jsonl", b"{}\n")
        self.assert_code("SOURCE_ROOT_NOT_ALLOWED", build_plan, self.repo, self.external, self.request((outside,)), self.profile)
        self.assert_code("FILE_TYPE_NOT_ALLOWED", build_plan, self.repo, self.external, self.request((raw,)), self.profile)

    def test_source_symlink_is_prohibited(self) -> None:
        target = self.repo / "target.json"
        target.write_bytes(b"{}\n")
        logical = "registries/development/link.json"
        link = self.repo / logical
        link.parent.mkdir(parents=True)
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        item = ExportFile(logical, target.stat().st_size, hashlib.sha256(target.read_bytes()).hexdigest(), "REGISTRY")
        self.assert_code("SYMLINK_PROHIBITED", build_plan, self.repo, self.external, self.request((item,)), self.profile)

    def test_external_root_must_be_absolute_and_outside_repository(self) -> None:
        item = self.write("registries/development/state.json", b"{}\n")
        self.assert_code("EXTERNAL_ROOT_NOT_ABSOLUTE", build_plan, self.repo, Path("relative"), self.request((item,)), self.profile)
        self.assert_code("EXTERNAL_ROOT_INSIDE_REPOSITORY", build_plan, self.repo, self.repo / "exports", self.request((item,)), self.profile)

    def test_credentials_and_private_absolute_paths_are_denied(self) -> None:
        secret = self.write("registries/development/secret.json", b'{"token":"Bearer abc"}\n')
        private = self.write("registries/development/path.json", b'{"path":"/home/alice/private/file"}\n')
        self.assert_code("DENIED_CONTENT", build_plan, self.repo, self.external, self.request((secret,)), self.profile)
        self.assert_code("PRIVATE_ABSOLUTE_PATH", build_plan, self.repo, self.external, self.request((private,)), self.profile)

    def test_per_file_and_total_capacity_fail_closed(self) -> None:
        first = self.write("registries/development/a.json", b"123456")
        second = self.write("registries/development/b.json", b"abcdef")
        file_limited = replace(self.profile, max_file_bytes=5, max_bundle_bytes=20)
        total_limited = replace(self.profile, max_file_bytes=10, max_bundle_bytes=10)
        self.assert_code("CAPACITY_EXCEEDED", build_plan, self.repo, self.external, self.request((first,)), file_limited)
        self.assert_code("CAPACITY_EXCEEDED", build_plan, self.repo, self.external, self.request((first, second)), total_limited)

    def test_stale_staging_is_quarantined_before_success(self) -> None:
        item = self.write("registries/development/state.json", b"{}\n")
        plan = build_plan(self.repo, self.external, self.request((item,)), self.profile)
        plan.staging.mkdir(parents=True)
        (plan.staging / "partial.txt").write_text("partial")
        self.assertEqual(execute_export(plan)["status"], "PASS")
        quarantine = plan.staging.parent / "quarantine" / f"{plan.bundle_id}.0001"
        self.assertEqual((quarantine / "partial.txt").read_text(), "partial")

    def test_source_change_after_plan_is_quarantined(self) -> None:
        item = self.write("registries/development/state.json", b"AAAA")
        plan = build_plan(self.repo, self.external, self.request((item,)), self.profile)
        (self.repo / item.path).write_bytes(b"BBBB")
        self.assert_code("COPY_VERIFICATION_FAILED", execute_export, plan)
        quarantine_root = plan.staging.parent / "quarantine"
        self.assertTrue(any(quarantine_root.iterdir()))
        self.assertFalse(plan.destination.exists())

    def test_module_has_no_network_process_or_destructive_bundle_deletion_surface(self) -> None:
        source = (ROOT / "src/ovc/development/evidence_export.py").read_text()
        for token in ("subprocess", "requests", "urllib", "httpx", "socket", "rclone", "boto3"):
            self.assertNotIn(token, source)
        for token in (".unlink(", "rmtree(", "os.remove(", "shutil.move("):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
