from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "docs/programmes/grt-v0-2/wp1/GRT2_WP1_ARTIFACT_MANIFEST.json"
RECONCILIATION_PATH = ROOT / "docs/programmes/grt-v0-2/wp1/GRT2_WP1_MANIFEST_RECONCILIATION.json"
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
        raise AssertionError(completed.stderr.decode("utf-8", "replace"))
    return completed.stdout


class GRT2WP1ArtifactManifestTests(unittest.TestCase):
    def test_historical_manifest_identity_defect_has_exact_reconciliation_evidence(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        reconciliation = json.loads(RECONCILIATION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["packet_id"], "GRT2-WP1")
        self.assertEqual(manifest["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(manifest["activation"], "INACTIVE")
        self.assertEqual(reconciliation["original_manifest"], str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"))
        self.assertEqual(reconciliation["historical_candidate_commit"], WP1_CANDIDATE)
        self.assertEqual(reconciliation["authority_effect"], "NONE_INTEGRITY_EVIDENCE_ONLY")
        self.assertFalse(reconciliation["original_manifest_modified"])

        declared = {entry["path"]: entry for entry in manifest["artifacts"]}
        entry = declared[KNOWN_MISMATCH_PATH]
        payload = _git_blob(WP1_CANDIDATE, KNOWN_MISMATCH_PATH)
        witness = {
            "path": KNOWN_MISMATCH_PATH,
            "manifest_byte_size": entry["byte_size"],
            "manifest_sha256": entry["sha256"],
            "committed_blob_byte_size": len(payload),
            "committed_blob_sha256": hashlib.sha256(payload).hexdigest(),
        }
        self.assertNotEqual(witness["manifest_byte_size"], witness["committed_blob_byte_size"])
        self.assertNotEqual(witness["manifest_sha256"], witness["committed_blob_sha256"])
        self.assertEqual(reconciliation["witness"], witness)
        self.assertEqual(reconciliation["active_enforcement"], "NONE")

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
