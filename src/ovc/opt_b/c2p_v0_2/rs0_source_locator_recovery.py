from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

C2_VNEXT_AUTHORITY = "registries/opt_b/c2/vnext/C2_VNEXT_ACTIVE_RUNTIME_AUTHORITY_v0_1.json"
C2E_AUTHORITY = "registries/authority/C2E_ACTIVE_ENGINE_AUTHORITY_v0_1.json"
GRUN_SNAPSHOT = "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_GRUN_SOURCE_AUTHORITY_SNAPSHOT_v0_1.json"
C1_REMOTE_RECEIPT = "docs/releases/opt-b-c1-v2/corrective/c1c-g3/C1C_G3_REMOTE_VERIFICATION_RECEIPT.json"
LEGACY_C2_REMOTE_RECEIPT = "docs/releases/opt-b-c1-v2/corrective/c1c-g5/C1C_G5_C2_V2_REMOTE_VERIFICATION_RECEIPT.json"
C2_PACKAGE_MANIFEST = "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp11/C2AR_WP11_INTEGRATED_MANIFEST.json"

EXPECTED_C2_PACKAGE = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
EXPECTED_C2_PACKAGE_SHA256 = "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
EXPECTED_C2E_PACK = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
EXPECTED_C2E_PACK_SHA256 = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
EXPECTED_C1_RELEASE = "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2"
EXPECTED_LEGACY_C2_RELEASE = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2"


class RS0SourceRecoveryError(RuntimeError):
    pass


def _load(repo_root: Path, relative: str) -> dict[str, Any]:
    path = (repo_root / relative).resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RS0SourceRecoveryError(f"SOURCE_RECOVERY_RECORD_UNREADABLE:{relative}") from exc
    if not isinstance(value, dict):
        raise RS0SourceRecoveryError(f"SOURCE_RECOVERY_RECORD_NOT_OBJECT:{relative}")
    return value


def _release(receipt: Mapping[str, Any], release_id: str) -> dict[str, Any]:
    releases = receipt.get("releases")
    if not isinstance(releases, list):
        raise RS0SourceRecoveryError("SOURCE_RECOVERY_RELEASE_LIST_MISSING")
    for release in releases:
        if isinstance(release, Mapping) and release.get("release_id") == release_id:
            return dict(release)
    raise RS0SourceRecoveryError(f"SOURCE_RECOVERY_RELEASE_NOT_FOUND:{release_id}")


def inspect_repository_source_chain(repo_root: Path) -> dict[str, Any]:
    """Resolve what can be recovered without inventing or substituting source evidence.

    This function deliberately stops at the current C2-vNext/C2E materialisation boundary.
    A historical C2-v2 release may prove lineage/reproducibility, but current authority
    explicitly forbids using it as a new-evidence parent.
    """
    repo_root = repo_root.resolve()
    grun = _load(repo_root, GRUN_SNAPSHOT)
    c2_auth = _load(repo_root, C2_VNEXT_AUTHORITY)
    c2e_auth = _load(repo_root, C2E_AUTHORITY)
    c1_receipt = _load(repo_root, C1_REMOTE_RECEIPT)
    legacy_c2_receipt = _load(repo_root, LEGACY_C2_REMOTE_RECEIPT)
    c2_package = _load(repo_root, C2_PACKAGE_MANIFEST)

    grun_c2 = grun.get("upstream_bindings", {}).get("c2", {})
    grun_c2e = grun.get("upstream_bindings", {}).get("c2e", {})
    if c2_auth.get("package_id") != EXPECTED_C2_PACKAGE or c2_auth.get("package_sha256") != EXPECTED_C2_PACKAGE_SHA256:
        raise RS0SourceRecoveryError("CURRENT_C2_VNEXT_AUTHORITY_DRIFT")
    if grun_c2.get("package_id") != EXPECTED_C2_PACKAGE or grun_c2.get("package_sha256") != EXPECTED_C2_PACKAGE_SHA256:
        raise RS0SourceRecoveryError("GRUN_C2_BINDING_DRIFT")
    if c2e_auth.get("active_boundary_pack_id") != EXPECTED_C2E_PACK or c2e_auth.get("active_boundary_pack_logical_sha256") != EXPECTED_C2E_PACK_SHA256:
        raise RS0SourceRecoveryError("CURRENT_C2E_AUTHORITY_DRIFT")
    if grun_c2e.get("boundary_pack_id") != EXPECTED_C2E_PACK or grun_c2e.get("boundary_pack_sha256") != EXPECTED_C2E_PACK_SHA256:
        raise RS0SourceRecoveryError("GRUN_C2E_BINDING_DRIFT")
    if c2_package.get("package_id") != EXPECTED_C2_PACKAGE or c2_package.get("package_sha256") != EXPECTED_C2_PACKAGE_SHA256:
        raise RS0SourceRecoveryError("C2_PACKAGE_MANIFEST_DRIFT")

    c1 = _release(c1_receipt, EXPECTED_C1_RELEASE)
    legacy_c2 = _release(legacy_c2_receipt, EXPECTED_LEGACY_C2_RELEASE)
    legacy_policy = str(c2_auth.get("historical_replay_policy", ""))
    if "NOT_AS_NEW_EVIDENCE_PARENT" not in legacy_policy:
        raise RS0SourceRecoveryError("LEGACY_C2_NEW_EVIDENCE_FIREWALL_MISSING")

    c1_objects = c1.get("objects", [])
    if not isinstance(c1_objects, list) or not c1_objects:
        raise RS0SourceRecoveryError("C1_DISCOVERY_REMOTE_OBJECT_LOCATOR_EMPTY")
    if any(not isinstance(row, Mapping) or not row.get("key") or not row.get("sha256") for row in c1_objects):
        raise RS0SourceRecoveryError("C1_DISCOVERY_REMOTE_OBJECT_LOCATOR_INVALID")

    c2_external = c2_package.get("external_replay", {})
    if not isinstance(c2_external, Mapping):
        raise RS0SourceRecoveryError("C2_PACKAGE_EXTERNAL_REPLAY_INVALID")

    return {
        "schema": "ovc-c2p2-rs0-source-recovery-inspection/v1",
        "programme_id": "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1",
        "population": {
            "instrument": "GBPUSD",
            "sides": ["BID", "ASK"],
            "clocks": ["15M", "2H_A_L"],
            "interval": "[2021-01-01T00:00:00Z,2024-01-01T00:00:00Z)",
        },
        "current_c2": {
            "package_id": EXPECTED_C2_PACKAGE,
            "package_sha256": EXPECTED_C2_PACKAGE_SHA256,
            "authority_state": c2_auth.get("state"),
            "materialised_2021_2023_locator": "NOT_PRESENT_IN_REPOSITORY_RECORDS",
        },
        "current_c2e": {
            "boundary_pack_id": EXPECTED_C2E_PACK,
            "boundary_pack_sha256": EXPECTED_C2E_PACK_SHA256,
            "authority_state": c2e_auth.get("state"),
            "materialised_2021_2023_locator": "NOT_PRESENT_IN_REPOSITORY_RECORDS",
        },
        "upstream_c1": {
            "release_id": EXPECTED_C1_RELEASE,
            "manifest_id": c1.get("manifest_id"),
            "manifest_sha256": c1.get("manifest_sha256"),
            "remote_object_count": len(c1_objects),
            "remote_object_locator_status": "RECOVERED_FROM_IMMUTABLE_REMOTE_VERIFICATION_RECEIPT",
            "direct_rs0_source_role": "FORBIDDEN_NOT_C2_VNEXT_OR_C2E",
        },
        "legacy_c2": {
            "release_id": EXPECTED_LEGACY_C2_RELEASE,
            "manifest_id": legacy_c2.get("manifest_id"),
            "manifest_sha256": legacy_c2.get("manifest_sha256"),
            "remote_prefix": legacy_c2.get("remote_prefix"),
            "remote_verified": legacy_c2.get("remote_verified"),
            "disposition": "REJECT_AS_NEW_EVIDENCE_PARENT_LEGACY_READ_ONLY_ONLY",
        },
        "historical_c2_vnext_replay": {
            "google_drive_replay_folder_id": c2_external.get("google_drive_replay_folder_id"),
            "logical_population_sha256": c2_external.get("logical_population_sha256"),
            "scope": "HISTORICAL_JUNE_REPLAY_ONLY_NOT_2021_2023_SOURCE",
        },
        "recovery_status": "BLOCKED_CURRENT_C2_VNEXT_C2E_2021_2023_MATERIALISATION_ABSENT",
        "run_authority_consumed": False,
        "fallback_forbidden": True,
    }
