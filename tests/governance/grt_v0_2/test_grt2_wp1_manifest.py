from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "docs/programmes/grt-v0-2/wp1/GRT2_WP1_ARTIFACT_MANIFEST.json"


class GRT2WP1ArtifactManifestTests(unittest.TestCase):
    def test_manifest_hashes_every_declared_wp1_artifact(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["packet_id"], "GRT2-WP1")
        self.assertEqual(manifest["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(manifest["activation"], "INACTIVE")
        self.assertEqual(manifest["artifact_count"], len(manifest["artifacts"]))
        paths = [entry["path"] for entry in manifest["artifacts"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertNotIn(
            "docs/programmes/grt-v0-2/wp1/GRT2_WP1_ARTIFACT_MANIFEST.json",
            paths,
        )
        for entry in manifest["artifacts"]:
            payload = (ROOT / entry["path"]).read_bytes()
            self.assertEqual(len(payload), entry["byte_size"], entry["path"])
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(),
                entry["sha256"],
                entry["path"],
            )

    def test_manifest_covers_all_wp1_contract_schema_registry_and_fixture_files(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        declared = {entry["path"] for entry in manifest["artifacts"]}
        for prefix in (
            "contracts/governance/grt_v0_2",
            "schemas/governance/grt_v0_2",
            "registries/governance/grt_v0_2",
            "fixtures/governance/grt_v0_2/wp1",
        ):
            actual = {
                str(path.relative_to(ROOT)).replace("\\", "/")
                for path in (ROOT / prefix).rglob("*")
                if path.is_file()
            }
            self.assertTrue(actual)
            self.assertTrue(actual <= declared, (prefix, sorted(actual - declared)))


if __name__ == "__main__":
    unittest.main()
