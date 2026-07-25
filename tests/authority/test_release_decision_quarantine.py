from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "legacy/quarantine/abcd-engine-v1-c0ad7ba/R0_7_RELEASE_DECISION_QUARANTINE_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ReleaseDecisionQuarantineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_all_recorded_sources_are_absent_and_targets_present(self) -> None:
        for record in self.payload["records"]:
            self.assertFalse((ROOT / record["source_path"]).exists(), record["source_path"])
            self.assertTrue((ROOT / record["target_path"]).is_file(), record["target_path"])

    def test_all_targets_preserve_blob_and_sha256_identity(self) -> None:
        for record in self.payload["records"]:
            target = ROOT / record["target_path"]
            blob = subprocess.check_output(["git", "hash-object", "--", target], cwd=ROOT, text=True).strip()
            self.assertEqual(record["git_blob_sha1"], blob)
            self.assertEqual(record["sha256"], sha256(target))

    def test_old_active_roots_contain_markers_only(self) -> None:
        release_files = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "docs/history/releases").rglob("*") if path.is_file())
        decision_files = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "docs/decisions").rglob("*") if path.is_file())
        self.assertEqual(["docs/history/releases/README.md"], release_files)
        self.assertEqual(["docs/decisions/README.md"], decision_files)

    def test_quarantined_records_have_no_active_authority(self) -> None:
        self.assertEqual("HISTORICAL_QUARANTINED", self.payload["authority_state"])
        self.assertEqual("NONE", self.payload["market_authority"])
        self.assertFalse(self.payload["release_parent_eligible"])
        self.assertFalse(self.payload["selector_eligible"])
        self.assertFalse(self.payload["rollback_target_eligible"])
        self.assertFalse(self.payload["discovery_seed_eligible"])


if __name__ == "__main__":
    unittest.main()
