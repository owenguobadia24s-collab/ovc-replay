from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROLES = {
    "discovery": ("OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1", "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1.r1"),
    "development": ("OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1", "MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1.r1"),
}
EXPECTED_INVENTORY_SHA256 = "39f55e923fa0a8302024f02d862d294ad9d8448fe197a9849ee9ec0f15d4a383"
PARENT_ARTIFACT_ID = 8626942276
B1_G1_COMMIT = "29718a526235ef7268a3226173352951072c35e8"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--candidate-root", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    args = p.parse_args()
    inventory_path = args.candidate_root / "WP4_INVENTORY.json"
    if sha256(inventory_path) != EXPECTED_INVENTORY_SHA256:
        raise SystemExit("candidate inventory identity mismatch")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    result = {"schema": "ovc-c1-wp4f-freeze-report/v1", "status": "PASS", "releases": []}
    for role, (release_id, manifest_id) in ROLES.items():
        root = args.output_root / release_id
        records = root / "records"
        records.mkdir(parents=True, exist_ok=False)
        selected = []
        for item in inventory["files"]:
            rel = Path(item["path"])
            parts = rel.parts
            try:
                idx = parts.index(role)
            except ValueError:
                continue
            source_rel = Path(*parts[idx:])
            src = args.candidate_root / source_rel
            if not src.is_file() or src.stat().st_size != item["size_bytes"] or sha256(src) != item["sha256"]:
                raise SystemExit(f"candidate byte mismatch: {source_rel}")
            target_rel = Path(*source_rel.parts[1:])
            dst = records / target_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            selected.append({"path": f"records/{target_rel.as_posix()}", "size_bytes": dst.stat().st_size, "sha256": sha256(dst)})
        selected.sort(key=lambda x: x["path"])
        descriptor = {
            "schema": "ovc-c1-release-descriptor/v1", "release_id": release_id,
            "role": role.upper(), "lifecycle_state": "RELEASE_FROZEN", "authority_state": "CANDIDATE",
            "availability_state": "LOCAL_ONLY", "publication_status": "NOT_ATTEMPTED",
            "formula_registry_id": "C1.FORMULAS.v0.1", "source_candidate_artifact_id": PARENT_ARTIFACT_ID,
            "source_inventory_sha256": EXPECTED_INVENTORY_SHA256, "freeze_authority_commit": B1_G1_COMMIT,
            "selector_state": "NONE", "validation_consumption": "LOCKED_UNCONSUMED"
        }
        (root / "release-descriptor.json").write_text(json.dumps(descriptor, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        files = selected + [{"path": "release-descriptor.json", "size_bytes": (root / "release-descriptor.json").stat().st_size, "sha256": sha256(root / "release-descriptor.json")}]
        manifest = {"schema": "ovc-c1-release-manifest/v1", "manifest_id": manifest_id, "release_id": release_id,
                    "source_build_commit": B1_G1_COMMIT, "files": files, "file_count": len(files),
                    "payload_bytes": sum(x["size_bytes"] for x in files), "record_file_count": len(selected)}
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        for item in files:
            path = root / item["path"]
            if path.stat().st_size != item["size_bytes"] or sha256(path) != item["sha256"]:
                raise SystemExit(f"post-freeze verification failure: {item['path']}")
        result["releases"].append({"release_id": release_id, "manifest_id": manifest_id, "manifest_sha256": sha256(manifest_path), "record_file_count": len(selected), "verified_bytes": sum(x["size_bytes"] for x in files)})
    (args.output_root / "WP4F_FREEZE_REPORT.json").write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
