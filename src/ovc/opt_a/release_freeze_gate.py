from __future__ import annotations

import json
import shutil
from pathlib import Path, PurePosixPath
from typing import Any

from .release_freeze import (
    GATE_ID,
    PROGRAMME_ID,
    REVIEWED_MANIFESTS,
    ROLE_RELEASES,
    ReleaseFreezeError,
    _inventory,
    _load_json,
    _safe_relative,
    canonical_json_sha256,
    sha256_file,
)

DISPOSITION = "RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS"


def _verify(workspace: Path, role: str) -> dict[str, Any]:
    manifest = _load_json(workspace / "workspace-manifest.json")
    unhashed = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if manifest.get("manifest_sha256") != canonical_json_sha256(unhashed):
        raise ReleaseFreezeError("workspace manifest self-hash mismatch")
    if manifest.get("manifest_sha256") != REVIEWED_MANIFESTS[role]:
        raise ReleaseFreezeError("workspace manifest is not the A2-G2 reviewed identity")
    if manifest.get("role") != role or manifest.get("target_release_id") != ROLE_RELEASES[role]:
        raise ReleaseFreezeError("reviewed role identity mismatch")
    if manifest.get("authority_state") != "MUTABLE_WORKSPACE":
        raise ReleaseFreezeError("workspace authority state mismatch")
    if role == "VALIDATION" and manifest.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise ReleaseFreezeError("validation workspace lock is missing")

    for record in manifest.get("observations", []):
        relative = _safe_relative(record.get("path"))
        path = workspace.joinpath(*PurePosixPath(relative).parts)
        digest, size = sha256_file(path)
        if digest != record.get("sha256") or size != record.get("size_bytes"):
            raise ReleaseFreezeError(f"observation byte identity mismatch: {relative}")

    quarantine = manifest.get("quarantine")
    if not isinstance(quarantine, list) or len(quarantine) != manifest.get("quarantined_bucket_count"):
        raise ReleaseFreezeError("quarantine cardinality mismatch")
    for record in quarantine:
        if record.get("reason") != "INCOMPLETE_OR_NONCONTIGUOUS_M1_BUCKET":
            raise ReleaseFreezeError("unreviewed quarantine reason")
        if not record.get("bucket_id"):
            raise ReleaseFreezeError("quarantine bucket identity missing")
        missing = record.get("missing_timestamps_ms")
        unexpected = record.get("unexpected_timestamps_ms")
        if not isinstance(missing, list) or not isinstance(unexpected, list):
            raise ReleaseFreezeError("quarantine timestamp evidence missing")
        if record.get("missing_timestamp_count") != len(missing):
            raise ReleaseFreezeError("missing timestamp count mismatch")
        if record.get("unexpected_timestamp_count") != len(unexpected):
            raise ReleaseFreezeError("unexpected timestamp count mismatch")
        if int(record["expected_count"]) - len(missing) + len(unexpected) != int(record["observed_count"]):
            raise ReleaseFreezeError("quarantine coverage arithmetic mismatch")
    return manifest


def _copy_observations(workspace: Path, release_root: Path, manifest: dict[str, Any]) -> None:
    for record in manifest["observations"]:
        relative = _safe_relative(record["path"])
        source = workspace.joinpath(*PurePosixPath(relative).parts)
        target = release_root / "canonical" / PurePosixPath(relative).relative_to("observations")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target, follow_symlinks=False)


def freeze_role(*, workspace: Path, output_root: Path, role: str, source_commit: str) -> dict[str, Any]:
    role = role.upper()
    manifest = _verify(workspace, role)
    release_id = ROLE_RELEASES[role]
    root = output_root / release_id
    if root.exists() or root.is_symlink():
        raise ReleaseFreezeError(f"release root already exists: {root}")
    root.mkdir(parents=True)
    try:
        _copy_observations(workspace, root, manifest)
        qa = root / "QA"
        qa.mkdir()
        with (qa / "quarantine-ledger.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for item in sorted(manifest["quarantine"], key=lambda value: value["bucket_id"]):
                handle.write(json.dumps({**item, "disposition": DISPOSITION}, sort_keys=True, separators=(",", ":")) + "\n")
        lineage = root / "lineage"
        lineage.mkdir()
        (lineage / "reviewed-workspace-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        descriptor = {
            "schema": "ovc-opt-a-role-release-descriptor/v1",
            "programme_id": PROGRAMME_ID,
            "gate_id": GATE_ID,
            "release_id": release_id,
            "role": role,
            "instrument_id": "GBPUSD",
            "source_commit": source_commit,
            "source_workspace_manifest_sha256": manifest["manifest_sha256"],
            "lifecycle_state": "RELEASE_FROZEN",
            "authority_state": "CANDIDATE",
            "qa_state": "PASS_WITH_RETAINED_QUARANTINE",
            "availability_state": "LOCAL_ARTIFACT_ONLY",
            "publication_status": "NOT_ATTEMPTED",
            "selector_state": "NONE",
            "validation_consumption": "LOCKED_UNCONSUMED" if role == "VALIDATION" else "NOT_APPLICABLE",
            "clocks": ["M1", "15M", "H1_M1_DERIVED", "2H_A_L"],
            "price_sides": ["BID", "ASK"],
            "observation_object_count": len(manifest["observations"]),
            "quarantined_bucket_count": len(manifest["quarantine"]),
            "quarantine_disposition": DISPOSITION,
            "authority": {"r2_publication": "DENIED", "selector_activation": "DENIED", "opt_b_handoff": "DENIED", "market": "NONE"},
        }
        descriptor["descriptor_sha256"] = canonical_json_sha256(descriptor)
        (root / "release-descriptor.json").write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        files = _inventory(root)
        inventory = {
            "schema": "ovc-opt-a-role-release-inventory/v1",
            "release_id": release_id,
            "files": files,
            "file_count": len(files),
            "total_size_bytes": sum(int(item["size_bytes"]) for item in files),
        }
        inventory["inventory_sha256"] = canonical_json_sha256(inventory)
        (root / "release-inventory.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt = {
            "schema": "ovc-opt-a-role-release-freeze-receipt/v1",
            "programme_id": PROGRAMME_ID,
            "gate_id": GATE_ID,
            "release_id": release_id,
            "role": role,
            "result": "PASS",
            "source_commit": source_commit,
            "source_workspace_manifest_sha256": manifest["manifest_sha256"],
            "release_inventory_sha256": inventory["inventory_sha256"],
            "release_file_count": len(_inventory(root)),
            "release_total_size_bytes": sum(int(item["size_bytes"]) for item in _inventory(root)),
            "release_root": root.as_posix(),
            "overwrite_policy": "DENIED",
            "quarantine_disposition": DISPOSITION,
            "authority": descriptor["authority"],
        }
        receipt["receipt_sha256"] = canonical_json_sha256(receipt)
        (root / "freeze-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return receipt
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def freeze_all_roles(*, workspaces_root: Path, output_root: Path, source_commit: str) -> dict[str, Any]:
    receipts = {
        role: freeze_role(workspace=workspaces_root / role.lower(), output_root=output_root, role=role, source_commit=source_commit)
        for role in ("DISCOVERY", "DEVELOPMENT", "VALIDATION")
    }
    report = {
        "schema": "ovc-opt-a-a2-g3-freeze-report/v1",
        "programme_id": PROGRAMME_ID,
        "gate_id": GATE_ID,
        "result": "PASS",
        "source_commit": source_commit,
        "roles": receipts,
        "authority": {
            "role_release_freeze": "COMPLETE_LOCAL_ARTIFACT_ONLY",
            "r2_publication": "DENIED",
            "selector_activation": "DENIED",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "opt_b_handoff": "DENIED",
            "market": "NONE",
        },
    }
    report["report_sha256"] = canonical_json_sha256(report)
    (output_root / "A2_G3_FREEZE_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
