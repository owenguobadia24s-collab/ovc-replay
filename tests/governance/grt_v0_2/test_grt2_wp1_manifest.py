from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "docs/programmes/grt-v0-2/wp1/GRT2_WP1_ARTIFACT_MANIFEST.json"
CORRECTION_PATH = ROOT / "docs/programmes/grt-v0-2/wp1/GRT2_WP1_MANIFEST_IDENTITY_CORR1.json"
WP1_CANDIDATE = "1c213f4573bd3715ef0dfed801806cad213e9b0a"
KNOWN_MISMATCH_PATH = "contracts/governance/grt_v0_2/GRT_BOOTSTRAP_VALIDATION_CONTRACT_v0_1.md"


def _git_blob(commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"unable to read historical WP1 blob {commit}:{path}: "
            + completed.stderr.decode("utf-8", "replace")
        )
    return completed.stdout


class GRT2WP1ArtifactManifestTests(unittest.TestCase):
    def test_historical_manifest_identity_defect_is_explicitly_quarantined(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        correction = json.loads(CORRECTION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["packet_id"], "GRT2-WP1")
        self.assertEqual(manifest["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(manifest["activation"], "INACTIVE")
        self.assertEqual(correction["supersedes_manifest"], str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"))
        self.assertEqual(correction["status"], "QUARANTINED_NONREPRODUCIBLE_BYTE_IDENTITY")
        self.assertEqual(correction["authority_effect"], "NONE_INTEGRITY_CORRECTION")
        self.assertEqual(correction["historical_candidate_commit"], WP1_CANDIDATE)

        declared = {entry["path"]: entry for entry in manifest["artifacts"]}
        entry = declared[KNOWN_MISMATCH_PATH]
        payload = _git_blob(WP1_CANDIDATE, KNOWN_MISMATCH_PATH)
        actual = {
            "path": KNOWN_MISMATCH_PATH,
            "declared_byte_size": entry["byte_size"],
            "declared_sha256": entry["sha256"],
            "git_blob_byte_size": len(payload),
            "git_blob_sha256": hashlib.sha256(payload).hexdigest(),
        }
        self.assertNotEqual(actual["declared_byte_size"], actual["git_blob_byte_size"])
        self.assertNotEqual(actual["declared_sha256"], actual["git_blob_sha256"])
        self.assertEqual(correction["witness_mismatch"], actual)
        self.assertFalse(correction["original_manifest_rewritten"])
        self.assertTrue(correction["original_manifest_preserved_as_historical_evidence"])

    def test_historical_manifest_freezes_wp1_owned_paths_without_claiming_future_shared_roots(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        declared = {entry["path"] for entry in manifest["artifacts"]}
        self.assertEqual(manifest["artifact_count"], len(declared))
        self.assertTrue(any(path.startswith("contracts/governance/grt_v0_2/") for path in declared))
        self.assertTrue(any(path.startswith("schemas/governance/grt_v0_2/") for path in declared))
        self.assertTrue(any(path.startswith("registries/governance/grt_v0_2/") for path in declared))
        self.assertTrue(any(path.startswith("fixtures/governance/grt_v0_2/wp1/") for path in declared))
        self.assertFalse(any("/baseline/" in path for path in declared))
        self.assertFalse(any("/wp2/" in path for path in declared))


if __name__ == "__main__":
    unittest.main()
