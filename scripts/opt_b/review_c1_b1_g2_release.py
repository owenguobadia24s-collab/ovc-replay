from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

B1_G1_COMMIT = "29718a526235ef7268a3226173352951072c35e8"
WP4F_RUN_ID = 30187276514
SOURCE_INVENTORY_SHA256 = "39f55e923fa0a8302024f02d862d294ad9d8448fe197a9849ee9ec0f15d4a383"

EXPECTED: dict[str, dict[str, Any]] = {
    "DISCOVERY": {
        "release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
        "manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1.r1",
        "manifest_sha256": "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2",
        "descriptor_sha256": "c965d76d9888b045f0e57ef058726ca320628725d517b73923ab4a9cbef80e81",
        "manifest_file_count": 145,
        "record_file_count": 144,
        "payload_bytes": 27451233,
        "record_count": 159892,
    },
    "DEVELOPMENT": {
        "release_id": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1",
        "manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1.r1",
        "manifest_sha256": "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017",
        "descriptor_sha256": "d85b59f021b15c353c28ae3dc7feb4f88930af2eb4faa07a9e884a4654eb3f10",
        "manifest_file_count": 49,
        "record_file_count": 48,
        "payload_bytes": 8719477,
        "record_count": 52872,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_release(root: Path, role: str) -> dict[str, Any]:
    expected = EXPECTED[role]
    manifest_path = root / "manifest.json"
    descriptor_path = root / "release-descriptor.json"
    if not manifest_path.is_file() or not descriptor_path.is_file():
        raise SystemExit(f"{role}: release descriptor or manifest missing")
    if sha256(manifest_path) != expected["manifest_sha256"]:
        raise SystemExit(f"{role}: manifest identity mismatch")
    if sha256(descriptor_path) != expected["descriptor_sha256"]:
        raise SystemExit(f"{role}: descriptor identity mismatch")

    manifest = load_json(manifest_path)
    descriptor = load_json(descriptor_path)
    required_manifest = {
        "schema": "ovc-c1-release-manifest/v1",
        "release_id": expected["release_id"],
        "manifest_id": expected["manifest_id"],
        "source_build_commit": B1_G1_COMMIT,
        "file_count": expected["manifest_file_count"],
        "record_file_count": expected["record_file_count"],
        "payload_bytes": expected["payload_bytes"],
    }
    for key, value in required_manifest.items():
        if manifest.get(key) != value:
            raise SystemExit(f"{role}: manifest field mismatch: {key}")

    required_descriptor = {
        "schema": "ovc-c1-release-descriptor/v1",
        "release_id": expected["release_id"],
        "role": role,
        "lifecycle_state": "RELEASE_FROZEN",
        "authority_state": "CANDIDATE",
        "availability_state": "LOCAL_ONLY",
        "publication_status": "NOT_ATTEMPTED",
        "formula_registry_id": "C1.FORMULAS.v0.1",
        "source_candidate_artifact_id": 8626942276,
        "source_inventory_sha256": SOURCE_INVENTORY_SHA256,
        "freeze_authority_commit": B1_G1_COMMIT,
        "selector_state": "NONE",
        "validation_consumption": "LOCKED_UNCONSUMED",
    }
    for key, value in required_descriptor.items():
        if descriptor.get(key) != value:
            raise SystemExit(f"{role}: descriptor field mismatch: {key}")

    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != expected["manifest_file_count"]:
        raise SystemExit(f"{role}: manifest inventory cardinality mismatch")
    listed_paths = [item.get("path") for item in files]
    if any(not isinstance(path, str) for path in listed_paths):
        raise SystemExit(f"{role}: invalid manifest path")
    if len(set(listed_paths)) != len(listed_paths):
        raise SystemExit(f"{role}: duplicate manifest path")
    if listed_paths != sorted(listed_paths):
        raise SystemExit(f"{role}: manifest inventory is not canonical")

    total_bytes = 0
    record_files = 0
    expected_files = {"manifest.json"}
    for item in files:
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise SystemExit(f"{role}: unsafe manifest path: {rel}")
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"{role}: missing or linked release file: {rel}")
        if path.stat().st_size != item.get("size_bytes"):
            raise SystemExit(f"{role}: size mismatch: {rel}")
        if sha256(path) != item.get("sha256"):
            raise SystemExit(f"{role}: SHA-256 mismatch: {rel}")
        total_bytes += path.stat().st_size
        expected_files.add(rel.as_posix())
        if rel.parts and rel.parts[0] == "records":
            record_files += 1

    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        raise SystemExit(f"{role}: unmanifested or missing release files")
    if total_bytes != expected["payload_bytes"]:
        raise SystemExit(f"{role}: payload-byte total mismatch")
    if record_files != expected["record_file_count"]:
        raise SystemExit(f"{role}: record-file count mismatch")

    return {
        "role": role,
        "release_id": expected["release_id"],
        "manifest_id": expected["manifest_id"],
        "manifest_sha256": expected["manifest_sha256"],
        "descriptor_sha256": expected["descriptor_sha256"],
        "manifest_file_count": expected["manifest_file_count"],
        "record_file_count": expected["record_file_count"],
        "record_count": expected["record_count"],
        "verified_payload_bytes": total_bytes,
        "selector_state": "NONE",
        "publication_status": "NOT_ATTEMPTED",
    }


def verify_freeze_report(path: Path) -> None:
    report = load_json(path)
    if report.get("schema") != "ovc-c1-wp4f-freeze-report/v1" or report.get("status") != "PASS":
        raise SystemExit("WP4F freeze report is not PASS")
    releases = {item.get("release_id"): item for item in report.get("releases", [])}
    for expected in EXPECTED.values():
        item = releases.get(expected["release_id"])
        if not item:
            raise SystemExit("WP4F freeze report release missing")
        required = {
            "manifest_id": expected["manifest_id"],
            "manifest_sha256": expected["manifest_sha256"],
            "record_file_count": expected["record_file_count"],
            "verified_bytes": expected["payload_bytes"],
        }
        for key, value in required.items():
            if item.get(key) != value:
                raise SystemExit(f"WP4F freeze report mismatch: {expected['release_id']} {key}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery-root", type=Path, required=True)
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--freeze-report", type=Path, required=True)
    parser.add_argument("--remote-collision-state", choices=["PASS_ABSENT"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    verify_freeze_report(args.freeze_report)
    releases = [
        verify_release(args.discovery_root, "DISCOVERY"),
        verify_release(args.development_root, "DEVELOPMENT"),
    ]
    receipt = {
        "schema": "ovc-c1-b1-g2-publication-readiness-receipt/v1",
        "gate": "OPT-B.C1.v2.B1-G2",
        "status": "PASS",
        "source_wp4f_run_id": WP4F_RUN_ID,
        "source_inventory_sha256": SOURCE_INVENTORY_SHA256,
        "remote_collision_preflight": args.remote_collision_state,
        "releases": releases,
        "totals": {
            "release_count": len(releases),
            "record_file_count": sum(item["record_file_count"] for item in releases),
            "record_count": sum(item["record_count"] for item in releases),
            "verified_payload_bytes": sum(item["verified_payload_bytes"] for item in releases),
        },
        "authority": {
            "wp5_r2_publication": "AUTHORISED_EXACT_RELEASES_ONLY",
            "selector_activation": "NONE",
            "c2_consumption": "DENIED_PENDING_SEPARATE_HANDOFF_REVIEW",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "probability": "NONE",
            "exposure": "NONE",
            "trading": "NONE",
            "execution": "NONE",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
