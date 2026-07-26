from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations import (
    ApprovedPathRegistry,
    ArtifactCatalogueBuilder,
    ResearchOperationsConfig,
    UnsafePathError,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ROWP2CatalogueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.external = Path(self.tmp.name) / "external"
        self.repo.mkdir()
        self.external.mkdir()
        (self.repo / "contracts").mkdir()
        (self.repo / "contracts" / "a.txt").write_text("alpha", encoding="utf-8")
        self.registry_file = self.repo / "paths.json"
        self.registry_file.write_text(json.dumps({
            "roots": [
                {"alias": "repo_contracts", "path_template": "${REPO_ROOT}/contracts", "read_only": True, "required": True},
                {"alias": "external", "path_template": "${EXTERNAL_ROOT}", "read_only": True, "required": True},
            ]
        }), encoding="utf-8")
        config = ResearchOperationsConfig.from_environment(
            repository_root=self.repo,
            env={"OVC_EXTERNAL_ARTIFACT_ROOT": str(self.external), "OVC_RESEARCH_OPERATOR_ID": "fixture"},
        )
        self.registry = ApprovedPathRegistry.from_json(self.registry_file, config)
        self.builder = ArtifactCatalogueBuilder(self.registry)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_rebuild_is_logically_deterministic(self) -> None:
        first = self.builder.scan(aliases=["repo_contracts"], generated_at="2026-07-26T00:00:00Z", source_commit="abc")
        second = self.builder.scan(aliases=["repo_contracts"], generated_at="2026-07-26T00:01:00Z", source_commit="abc")
        self.assertEqual(first.logical_inventory_sha256, second.logical_inventory_sha256)
        self.assertEqual(first.nodes, second.nodes)
        self.assertNotIn(str(self.repo), json.dumps(first.to_dict()))

    def test_changed_missing_expired_and_orphan_are_detected(self) -> None:
        target = self.external / "payload.bin"
        target.write_bytes(b"payload")
        declarations = [
            {
                "artifact_id": "artifact:payload",
                "artifact_type": "FILE",
                "source_kind": "LOCAL",
                "location": {"root_alias": "external", "relative_path": "payload.bin"},
                "sha256": "0" * 64,
                "size_bytes": target.stat().st_size,
                "media_type": "application/octet-stream",
            },
            {
                "artifact_id": "artifact:missing",
                "artifact_type": "FILE",
                "source_kind": "LOCAL",
                "location": {"root_alias": "external", "relative_path": "missing.bin"},
                "sha256": "1" * 64,
                "size_bytes": 1,
            },
            {
                "artifact_id": "artifact:ci",
                "artifact_type": "BUNDLE",
                "source_kind": "GITHUB_ACTIONS",
                "availability": "REMOTE_PRESENT",
                "expires_at": "2026-07-25T00:00:00Z",
                "locations": [{"root_alias": "github_actions", "relative_path": "artifact/123"}],
            },
            {
                "artifact_id": "artifact:manifest",
                "artifact_type": "MANIFEST",
                "source_kind": "R2",
                "availability": "REMOTE_VERIFIED",
                "locations": [{"root_alias": "r2", "relative_path": "canonical/manifest.json"}],
                "dependencies": [],
            },
        ]
        catalogue = self.builder.verify_declarations(declarations, generated_at="2026-07-26T00:00:00Z", source_commit="abc")
        codes = {issue.code for issue in catalogue.issues}
        self.assertTrue({"HASH_MISMATCH", "MISSING_ARTIFACT", "EXPIRED_CI_ARTIFACT", "ORPHAN_MANIFEST"}.issubset(codes))

    def test_path_escape_and_symlink_are_denied(self) -> None:
        with self.assertRaises(UnsafePathError):
            self.registry.resolve("external", "../escape")
        if hasattr(os, "symlink"):
            outside = Path(self.tmp.name) / "outside.txt"
            outside.write_text("x", encoding="utf-8")
            link = self.external / "link.txt"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("symlink creation not permitted")
            with self.assertRaises(UnsafePathError):
                self.registry.safe_files("external")


if __name__ == "__main__":
    unittest.main()
