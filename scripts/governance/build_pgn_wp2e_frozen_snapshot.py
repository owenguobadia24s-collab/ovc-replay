#!/usr/bin/env python3
"""Validate and expose the immutable PGN-WP2E census snapshot.

The historical repository-genesis census is a sealed evidence bundle. Later
operator-admitted programmes are recorded in a separate additive ledger and do
not cause this snapshot to be rescanned or rewritten.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    ROOT
    / "registries/governance/programme_genesis/pgn_census/"
    "PGN_REPOSITORY_GENESIS_CENSUS_v0_2.json"
)
ADMISSION_LEDGER_PATH = (
    ROOT
    / "registries/governance/programme_genesis/post_snapshot/"
    "PGN_POST_SNAPSHOT_PROGRAMME_ADMISSION_LEDGER_v0_1.json"
)


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path.relative_to(ROOT)}")
    return value


def validate_ref(root: Path, ref: dict[str, Any]) -> dict[str, Any]:
    path = root / ref["path"]
    if not path.is_file():
        raise AssertionError(f"missing snapshot child: {ref['path']}")
    data = path.read_bytes()
    if len(data) != ref["bytes"]:
        raise AssertionError(f"byte count drift: {ref['path']}")
    if sha256_bytes(data) != ref["sha256"]:
        raise AssertionError(f"sha256 drift: {ref['path']}")
    return read_json(path)


def build_snapshot(root: Path = ROOT) -> dict[str, Any]:
    if root != ROOT:
        raise AssertionError(
            "alternate roots are not supported because snapshot identities "
            "are repository-relative"
        )

    manifest_bytes = MANIFEST_PATH.read_bytes()
    manifest = read_json(MANIFEST_PATH)

    expected_bundle_hash = manifest["bundle_manifest_sha256"]
    unsigned_manifest = dict(manifest)
    unsigned_manifest.pop("bundle_manifest_sha256")
    if sha256_bytes(canonical(unsigned_manifest)) != expected_bundle_hash:
        raise AssertionError("snapshot bundle manifest digest drift")

    objects: list[dict[str, Any]] = []
    child_identity: list[dict[str, Any]] = []
    expected_start = 0
    for ref in manifest["object_ledgers"]:
        ledger = validate_ref(root, ref)
        if ledger["start_index"] != expected_start:
            raise AssertionError("snapshot object-ledger ordering drift")
        if ledger["object_count"] != ref["object_count"]:
            raise AssertionError("snapshot object-ledger count drift")
        objects.extend(ledger["objects"])
        expected_start += ledger["object_count"]
        child_identity.append(
            {key: ref[key] for key in ("path", "sha256", "bytes")}
        )

    exclusion = validate_ref(root, manifest["exclusion_ledger"])
    lineage = validate_ref(root, manifest["lineage_consolidation_ledger"])
    coverage = validate_ref(root, manifest["coverage_and_unresolved_ledger"])
    for ref in (
        manifest["exclusion_ledger"],
        manifest["lineage_consolidation_ledger"],
        manifest["coverage_and_unresolved_ledger"],
    ):
        child_identity.append(
            {key: ref[key] for key in ("path", "sha256", "bytes")}
        )

    if sha256_bytes(canonical(child_identity)) != manifest["child_file_identity_sha256"]:
        raise AssertionError("snapshot child identity drift")
    if len(objects) != manifest["object_count"]:
        raise AssertionError("snapshot object count drift")
    if exclusion["entry_count"] != manifest["exclusion_ledger"]["entry_count"]:
        raise AssertionError("snapshot exclusion count drift")
    if lineage["entry_count"] != manifest["lineage_consolidation_ledger"]["entry_count"]:
        raise AssertionError("snapshot lineage count drift")
    if coverage["unresolved_count"] != manifest["coverage_and_unresolved_ledger"]["unresolved_count"]:
        raise AssertionError("snapshot unresolved count drift")

    return {
        "manifest": manifest,
        "manifest_git_blob_sha1": git_blob_sha1(manifest_bytes),
        "objects": objects,
        "exclusion_ledger": exclusion["entries"],
        "lineage_consolidation_ledger": lineage["entries"],
        "coverage_and_unresolved_ledger": coverage,
    }


def load_post_snapshot_admissions(root: Path = ROOT) -> dict[str, Any]:
    if root != ROOT:
        raise AssertionError(
            "alternate roots are not supported because admission identities "
            "are repository-relative"
        )
    return read_json(ADMISSION_LEDGER_PATH)


def main() -> int:
    snapshot = build_snapshot()
    admissions = load_post_snapshot_admissions()
    summary = {
        "snapshot_object_count": snapshot["manifest"]["object_count"],
        "snapshot_exclusion_count": snapshot["manifest"]["exclusion_ledger"]["entry_count"],
        "snapshot_bundle_manifest_sha256": snapshot["manifest"]["bundle_manifest_sha256"],
        "snapshot_manifest_git_blob_sha1": snapshot["manifest_git_blob_sha1"],
        "post_snapshot_admission_count": admissions["admission_count"],
    }
    print(
        "PGN_WP2E_FROZEN_SNAPSHOT="
        + json.dumps(summary, sort_keys=True, separators=(",", ":"))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
