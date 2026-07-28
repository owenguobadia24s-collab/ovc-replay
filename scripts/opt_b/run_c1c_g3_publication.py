from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED: dict[str, dict[str, Any]] = {
    "discovery": {
        "role": "DISCOVERY",
        "release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2",
        "manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2.r1",
        "manifest_sha256": "c9b2eaa826419a510504c016d99072c6015c337a5c2ef435252d5f6ff1db93bf",
        "record_count": 159892,
        "file_count": 144,
    },
    "development": {
        "role": "DEVELOPMENT",
        "release_id": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2",
        "manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2.r1",
        "manifest_sha256": "e4f1a2d0af7064837003f1c7b56156966aba3b035cc9a7b8ebbdc8b6b181d73f",
        "record_count": 52872,
        "file_count": 48,
    },
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def logical_manifest_sha(manifest: dict[str, Any]) -> str:
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    raw = (
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")
    return sha256_bytes(raw)


def run(*args: str, capture: bool = False) -> bytes | None:
    if capture:
        return subprocess.check_output(args)
    subprocess.run(args, check=True)
    return None


def verify_local(role_key: str, root: Path) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    expected = EXPECTED[role_key]
    manifest_path = root / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)

    for key in ("release_id", "manifest_id", "manifest_sha256", "record_count", "file_count"):
        if manifest.get(key) != expected[key]:
            raise RuntimeError(
                f"{role_key} {key} mismatch: expected={expected[key]!r} actual={manifest.get(key)!r}"
            )
    calculated_logical = logical_manifest_sha(manifest)
    if calculated_logical != expected["manifest_sha256"]:
        raise RuntimeError(
            f"{role_key} logical manifest hash mismatch: "
            f"expected={expected['manifest_sha256']} actual={calculated_logical}"
        )
    if manifest.get("formula_registry_id") != "C1.FORMULAS.v0.1":
        raise RuntimeError(f"{role_key} formula registry mismatch")
    if manifest.get("implementation_id") != "C1.IMPLEMENTATION.v0.2":
        raise RuntimeError(f"{role_key} implementation identity mismatch")
    if len(manifest.get("files", [])) != expected["file_count"]:
        raise RuntimeError(f"{role_key} file inventory length mismatch")

    records = 0
    payload_bytes = 0
    seen: set[str] = set()
    for item in manifest["files"]:
        relative = str(item["path"])
        if relative in seen or not relative.startswith("records/"):
            raise RuntimeError(f"{role_key} invalid or duplicate path: {relative}")
        seen.add(relative)
        data = (root / relative).read_bytes()
        if len(data) != int(item["size_bytes"]):
            raise RuntimeError(f"{role_key} size mismatch: {relative}")
        if sha256_bytes(data) != item["sha256"]:
            raise RuntimeError(f"{role_key} hash mismatch: {relative}")
        records += int(item["record_count"])
        payload_bytes += len(data)
    if records != expected["record_count"]:
        raise RuntimeError(f"{role_key} record cardinality mismatch: {records}")

    verification = {
        "role": expected["role"],
        "release_id": expected["release_id"],
        "manifest_id": expected["manifest_id"],
        "manifest_sha256": expected["manifest_sha256"],
        "manifest_file_sha256": sha256_bytes(manifest_bytes),
        "record_count": records,
        "record_file_count": expected["file_count"],
        "payload_bytes": payload_bytes,
    }
    return manifest, manifest_bytes, verification


def remote_listing(prefix: str) -> set[str]:
    result = subprocess.run(
        ["rclone", "lsf", "--recursive", "--s3-no-check-bucket", prefix],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"REMOTE_PREFLIGHT_ERROR:{prefix}:{result.stderr.strip()}")
    return {
        line.rstrip("/")
        for line in result.stdout.splitlines()
        if line and not line.endswith("/")
    }


def publish_or_reverify(
    role_key: str,
    root: Path,
    manifest: dict[str, Any],
    manifest_bytes: bytes,
    bucket: str,
) -> dict[str, Any]:
    expected = EXPECTED[role_key]
    prefix = f"{bucket}/{manifest['release_id']}/{manifest['manifest_id']}"
    listing = remote_listing(prefix)
    expected_listing = {
        f"files/{item['path']}" for item in manifest["files"]
    } | {"manifest.json"}

    if listing:
        if listing != expected_listing:
            missing = sorted(expected_listing - listing)
            extra = sorted(listing - expected_listing)
            raise RuntimeError(
                f"REMOTE_COLLISION:{role_key}:missing={missing[:5]}:extra={extra[:5]}"
            )
        collision_state = "EXACT_EXISTING_REVERIFY"
    else:
        collision_state = "ABSENT_PUBLISH"
        for item in manifest["files"]:
            source = root / item["path"]
            target = f"{prefix}/files/{item['path']}"
            run(
                "rclone",
                "copyto",
                "--immutable",
                "--s3-no-check-bucket",
                str(source),
                target,
            )
        run(
            "rclone",
            "copyto",
            "--immutable",
            "--s3-no-check-bucket",
            str(root / "manifest.json"),
            f"{prefix}/manifest.json",
        )

    objects: list[dict[str, Any]] = []
    payload_bytes = 0
    for item in manifest["files"]:
        remote = f"{prefix}/files/{item['path']}"
        data = run("rclone", "cat", "--s3-no-check-bucket", remote, capture=True)
        assert isinstance(data, bytes)
        digest = sha256_bytes(data)
        if len(data) != int(item["size_bytes"]) or digest != item["sha256"]:
            raise RuntimeError(f"REMOTE_BYTE_MISMATCH:{remote}")
        payload_bytes += len(data)
        objects.append(
            {
                "key": remote.split(":", 1)[1],
                "size_bytes": len(data),
                "sha256": digest,
            }
        )

    remote_manifest = f"{prefix}/manifest.json"
    remote_manifest_bytes = run(
        "rclone", "cat", "--s3-no-check-bucket", remote_manifest, capture=True
    )
    assert isinstance(remote_manifest_bytes, bytes)
    local_manifest_file_sha = sha256_bytes(manifest_bytes)
    remote_manifest_file_sha = sha256_bytes(remote_manifest_bytes)
    if remote_manifest_bytes != manifest_bytes or remote_manifest_file_sha != local_manifest_file_sha:
        raise RuntimeError(f"REMOTE_MANIFEST_BYTE_MISMATCH:{remote_manifest}")
    remote_manifest_logical = json.loads(remote_manifest_bytes)["manifest_sha256"]
    if remote_manifest_logical != expected["manifest_sha256"]:
        raise RuntimeError(f"REMOTE_MANIFEST_LOGICAL_IDENTITY_MISMATCH:{remote_manifest}")
    objects.append(
        {
            "key": remote_manifest.split(":", 1)[1],
            "size_bytes": len(remote_manifest_bytes),
            "sha256": remote_manifest_file_sha,
            "completion_marker": True,
        }
    )

    return {
        "role": expected["role"],
        "release_id": manifest["release_id"],
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "manifest_file_sha256": remote_manifest_file_sha,
        "implementation_id": manifest["implementation_id"],
        "formula_registry_id": manifest["formula_registry_id"],
        "record_count": manifest["record_count"],
        "record_file_count": manifest["file_count"],
        "payload_bytes": payload_bytes,
        "remote_object_count": len(objects),
        "collision_state": collision_state,
        "remote_verified": True,
        "objects": objects,
    }


def write_packet(receipt: dict[str, Any], packet_dir: Path) -> None:
    packet_dir.mkdir(parents=True, exist_ok=True)
    (packet_dir / "C1C_G3_REMOTE_VERIFICATION_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# C1C-G3 — C1 v2 R2 publication and full remote verification",
        "",
        "**Decision:** `PASS`",
        "",
        f"- Workflow run: `{receipt['workflow_run_id']}`",
        f"- Workflow commit: `{receipt['workflow_commit']}`",
        f"- Source candidate run: `{receipt['source_candidate_workflow_run_id']}`",
        f"- Remote objects verified: `{receipt['remote_object_count']}`",
        f"- Remote bytes verified including manifests: `{receipt['remote_verified_bytes_including_manifests']}`",
        "- Publication order: payload first, manifest completion marker last",
        "- C1 selectors: unchanged pending coordinated C1C-G4/G5 transaction",
        "- C2: unchanged pending C1C-G5",
        "- Validation: `LOCKED_UNCONSUMED`",
        "",
        "## Releases",
        "",
        "| Role | Release | Manifest | Logical SHA-256 | File SHA-256 | Collision state | Objects |",
        "|---|---|---|---|---|---|---:|",
    ]
    for item in receipt["releases"]:
        lines.append(
            f"| {item['role']} | `{item['release_id']}` | `{item['manifest_id']}` | "
            f"`{item['manifest_sha256']}` | `{item['manifest_file_sha256']}` | "
            f"{item['collision_state']} | {item['remote_object_count']} |"
        )
    lines.extend(
        [
            "",
            "Rollback leaves the exact v2 releases immutable and inactive and retains the existing v1 selectors.",
            "",
            "Next: execute deterministic C2 v2 identity replay and remote verification under C1C-G5.",
            "",
        ]
    )
    (packet_dir / "C1C_G3_PUBLICATION_PACKET.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery-root", type=Path, required=True)
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--bucket", default="ovc_r2:ovc-evidence/canonical/releases")
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--approval-merge-commit", required=True)
    args = parser.parse_args()

    roots = {
        "discovery": args.discovery_root,
        "development": args.development_root,
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    local_verified: list[dict[str, Any]] = []
    local_objects: dict[str, tuple[dict[str, Any], bytes]] = {}
    for role_key, root in roots.items():
        manifest, manifest_bytes, verification = verify_local(role_key, root)
        local_verified.append(verification)
        local_objects[role_key] = (manifest, manifest_bytes)

    local_receipt = {
        "schema": "ovc-c1c-g3-local-verification/v1",
        "status": "PASS",
        "source_run_id": args.source_run_id,
        "releases": local_verified,
    }
    (args.output_root / "C1C_G3_LOCAL_VERIFICATION.json").write_text(
        json.dumps(local_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    releases: list[dict[str, Any]] = []
    for role_key, root in roots.items():
        manifest, manifest_bytes = local_objects[role_key]
        releases.append(
            publish_or_reverify(role_key, root, manifest, manifest_bytes, args.bucket)
        )

    total_objects = sum(item["remote_object_count"] for item in releases)
    total_bytes = sum(
        sum(obj["size_bytes"] for obj in item["objects"]) for item in releases
    )
    receipt = {
        "schema": "ovc-c1c-g3-remote-verification/v1",
        "gate_id": "C1C-G3",
        "decision": "PASS",
        "status": "PASS_FULL_REMOTE_BYTE_VERIFICATION",
        "workflow_run_id": int(os.environ["GITHUB_RUN_ID"]),
        "workflow_commit": os.environ["GITHUB_SHA"],
        "approval_merge_commit": args.approval_merge_commit,
        "source_candidate_workflow_run_id": args.source_run_id,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "bucket": "ovc-evidence",
        "prefix": "canonical/releases/",
        "publication_order": "PAYLOAD_FIRST_MANIFEST_LAST",
        "release_count": len(releases),
        "remote_object_count": total_objects,
        "remote_verified_bytes_including_manifests": total_bytes,
        "releases": releases,
        "c1_selector_change": "NONE_PENDING_COORDINATED_C1C_G4_G5_TRANSACTION",
        "c2_change": "NONE_PENDING_C1C_G5",
        "validation_consumption": "LOCKED_UNCONSUMED",
    }
    (args.output_root / "C1C_G3_REMOTE_VERIFICATION_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_packet(receipt, args.packet_dir)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "workflow_run_id": receipt["workflow_run_id"],
                "remote_object_count": total_objects,
                "remote_verified_bytes": total_bytes,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
