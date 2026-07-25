from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ovc_evidence_store.manifest import build_manifest


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest spec must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--releases-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    spec = _load(args.spec)
    args.output_root.mkdir(parents=True, exist_ok=True)
    for role, record in spec["roles"].items():
        root = args.releases_root / role
        output = args.output_root / f"{role}.json"
        manifest = build_manifest(
            root=root,
            output=output,
            release_id=record["release_id"],
            manifest_id=record["manifest_id"],
            bucket=spec["bucket"],
            prefix=spec["prefix"],
            authority_state=spec["authority_state"],
            repository_commit=spec["source_commit"],
            source_ref=spec["source_ref"],
        )
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        count = len(manifest["files"])
        size = sum(int(item["size"]) for item in manifest["files"])
        if digest != record["expected_manifest_sha256"]:
            raise ValueError(f"manifest identity mismatch for {role}: {digest}")
        if count != record["expected_file_count"]:
            raise ValueError(f"file-count mismatch for {role}: {count}")
        if size != record["expected_total_size_bytes"]:
            raise ValueError(f"byte-size mismatch for {role}: {size}")
        if role == "validation":
            descriptor = json.loads((root / "release-descriptor.json").read_text(encoding="utf-8"))
            if descriptor.get("validation_consumption") != "LOCKED_UNCONSUMED":
                raise ValueError("validation lock is missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
