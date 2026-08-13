from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def build(repository_root: Path, output: Path) -> dict[str, object]:
    root = repository_root.resolve()
    source = root / "docs/programmes/grt-v0-2/wp1/GRT2_WP1_ARTIFACT_MANIFEST.json"
    original = json.loads(source.read_text(encoding="utf-8"))
    artifacts = []
    for entry in original["artifacts"]:
        relative = str(entry["path"])
        payload = (root / relative).read_bytes()
        artifacts.append(
            {
                "path": relative,
                "byte_size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest = {
        "schema": "ovc-grt2-wp1-artifact-manifest-corr1/v1",
        "programme_id": "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE",
        "packet_id": "GRT2-WP1-CORR1",
        "supersedes_manifest": "docs/programmes/grt-v0-2/wp1/GRT2_WP1_ARTIFACT_MANIFEST.json",
        "supersession_reason": "ORIGINAL_MANIFEST_CAPTURED_PRE_COMMIT_WORKTREE_BYTES_AND_IS_NOT_REPRODUCIBLE_FROM_GIT_BLOBS",
        "source_path_set": "EXACT_ORIGINAL_WP1_DECLARED_PATH_SET",
        "constitution_status": "PROPOSED_UNADMITTED",
        "activation": "INACTIVE",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "authority_effect": "NONE_INTEGRITY_CORRECTION",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = build(Path(args.repository_root), Path(args.output))
    print(json.dumps({"artifact_count": manifest["artifact_count"], "authority_effect": manifest["authority_effect"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
