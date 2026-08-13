from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "docs/programmes/grt-v0-2/wp1/GRT2_WP1_ARTIFACT_MANIFEST.json"
WP1_CANDIDATE = "1c213f4573bd3715ef0dfed801806cad213e9b0a"


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
    def test_historical_manifest_hashes_its_exact_candidate_blobs(self) -> None:
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
            payload = _git_blob(WP1_CANDIDATE, entry["path"])
            self.assertEqual(len(payload), entry["byte_size"], entry["path"])
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(),
                entry["sha256"],
                entry["path"],
            )

    def test_historical_manifest_freezes_wp1_owned_paths_without_claiming_future_shared_roots(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        declared = {entry["path"] for entry in manifest["artifacts"]}
        self.assertTrue(any(path.startswith("contracts/governance/grt_v0_2/") for path in declared))
        self.assertTrue(any(path.startswith("schemas/governance/grt_v0_2/") for path in declared))
        self.assertTrue(any(path.startswith("registries/governance/grt_v0_2/") for path in declared))
        self.assertTrue(any(path.startswith("fixtures/governance/grt_v0_2/wp1/") for path in declared))
        self.assertFalse(any("/baseline/" in path for path in declared))
        self.assertFalse(any("/wp2/" in path for path in declared))


if __name__ == "__main__":
    unittest.main()
