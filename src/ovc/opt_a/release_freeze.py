from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

PROGRAMME_ID = "OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2"
GATE_ID = "A2-G3"
SCHEMA = "ovc-opt-a-role-release-descriptor/v1"
FREEZE_RECEIPT_SCHEMA = "ovc-opt-a-role-release-freeze-receipt/v1"
ROLE_RELEASES = {
    "DISCOVERY": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
    "DEVELOPMENT": "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
    "VALIDATION": "OPT-A.GBPUSD.VALIDATION.2025.v2",
}
REVIEWED_MANIFESTS = {
    "DISCOVERY": "f1ef621bce4a098a80d2cb309ae6f9cba2fcd177e71ce1ac98614f826e0f9a71",
    "DEVELOPMENT": "fa527f01fc0db621cbcddf2fe4bbe8f697e54c9af238e56e85f2a4da0140b1c2",
    "VALIDATION": "9e92e479b7d39e6669681659d0acf98b1d686d0dc66bfe2e8558d742aaa13514",
}


class ReleaseFreezeError(ValueError):
    """Raised when a reviewed mutable workspace cannot be frozen lawfully."""


def canonical_json_bytes(document: object) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def canonical_json_sha256(document: object) -> str:
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseFreezeError(f"invalid JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise ReleaseFreezeError(f"JSON evidence must be an object: {path}")
    return value


def _safe_relative(path: object) -> str:
    if not isinstance(path, str) or not path:
        raise ReleaseFreezeError("manifest path must be a non-empty string")
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise ReleaseFreezeError(f"unsafe manifest path: {path!r}")
    return pure.as_posix()


def verify_reviewed_workspace(workspace: Path, role: str) -> dict[str, Any]:
    role = role.upper()
    if role not in ROLE_RELEASES:
        raise ReleaseFreezeError(f"unknown role: {role}")
    manifest_path = workspace / "workspace-manifest.json"
    manifest = _load_json(manifest_path)
    recorded_hash = manifest.get("manifest_sha256")
    unhashed = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    calculated_hash = canonical_json_sha256(unhashed)
    if recorded_hash != calculated_hash:
        raise ReleaseFreezeError("workspace manifest self-hash mismatch")
    if recorded_hash != REVIEWED_MANIFESTS[role]:
        raise ReleaseFreezeError("workspace manifest is not the A2-G2 reviewed identity")
    if manifest.get("role") != role:
        raise ReleaseFreezeError("workspace role mismatch")
    if manifest.get("target_release_id") != ROLE_RELEASES[role]:
        raise ReleaseFreezeError("target release identity mismatch")
    if manifest.get("authority_state") != "MUTABLE_WORKSPACE":
        raise ReleaseFreezeError("workspace is not mutable review evidence")
    if manifest.get("qa_state") not in {"PASS", "WARN"}:
        raise ReleaseFreezeError("workspace QA state is not freeze-eligible")
    if role == "VALIDATION" and manifest.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise ReleaseFreezeError("validation workspace lock is missing")

    observations = manifest.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ReleaseFreezeError("workspace observations are missing")
    for record in observations:
        if not isinstance(record, dict):
            raise ReleaseFreezeError("invalid observation record")
        relative = _safe_relative(record.get("path"))
        candidate = workspace.joinpath(*PurePosixPath(relative).parts)
        if not candidate.is_file() or candidate.is_symlink():
            raise ReleaseFreezeError(f"observation is missing or unsafe: {relative}")
        digest, size = sha256_file(candidate)
        if digest != record.get("sha256") or size != record.get("size_bytes"):
            raise ReleaseFreezeError(f"observation byte identity mismatch: {relative}")

    quarantine = manifest.get("quarantine")
    if not isinstance(quarantine, list):
        raise ReleaseFreezeError("workspace quarantine must be an array")
    if len(quarantine) != manifest.get("quarantined_bucket_count"):
        raise ReleaseFreezeError("workspace quarantine cardinality mismatch")
    for record in quarantine:
        if not isinstance(record, dict):
            raise ReleaseFreezeError("invalid quarantine record")
        if record.get("reason") != "INCOMPLETE_OR_NONCONTIGUOUS_M1_BUCKET":
            raise ReleaseFreezeError("unreviewed quarantine reason")
        if record.get("disposition") != "RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS":
            raise ReleaseFreezeError("quarantine disposition mismatch")
        if not isinstance(record.get("bucket_id"), str) or not record["bucket_id"]:
            raise ReleaseFreezeError("quarantine bucket identity missing")
        missing = record.get("missing_timestamps")
        unexpected = record.get("unexpected_timestamps")
        if not isinstance(missing, list) or not isinstance(unexpected, list):
            raise ReleaseFreezeError("quarantine timestamp evidence missing")
        expected = int(record.get("expected_count", -1))
        observed = int(record.get("observed_count", -1))
        if expected - len(missing) + len(unexpected) != observed:
            raise ReleaseFreezeError("quarantine coverage arithmetic mismatch")
    return manifest


def _inventory(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    aliases: set[str] = set()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().encode("utf-8")):
        if path.is_symlink():
            raise ReleaseFreezeError(f"symbolic link prohibited: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        alias = relative.casefold()
        if alias in aliases:
            raise ReleaseFreezeError(f"case-folding path collision: {relative}")
        aliases.add(alias)
        digest, size = sha256_file(path)
        records.append({"path": relative, "sha256": digest, "size_bytes": size})
    return records


def _copy_observations(workspace: Path, release_root: Path, records: Iterable[dict[str, Any]]) -> None:
    for record in records:
        relative = _safe_relative(record["path"])
        source = workspace.joinpath(*PurePosixPath(relative).parts)
        target = release_root / "canonical" / PurePosixPath(relative).relative_to("observations")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target, follow_symlinks=False)


def freeze_role_release(*, workspace: Path, output_root: Path, role: str, source_commit: str) -> dict[str, Any]:
    role = role.upper()
    manifest = verify_reviewed_workspace(workspace, role)
    release_id = ROLE_RELEASES[role]
    release_root = output_root / release_id
    if release_root.exists() or release_root.is_symlink():
        raise ReleaseFreezeError(f"release root already exists: {release_root}")
    release_root.mkdir(parents=True)

    try:
        _copy_observations(workspace, release_root, manifest["observations"])
        qa_root = release_root / "QA"
        qa_root.mkdir(parents=True)
        quarantine_path = qa_root / "quarantine-ledger.jsonl"
        with quarantine_path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in sorted(manifest["quarantine"], key=lambda item: item["bucket_id"]):
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

        source_manifest = release_root / "lineage" / "reviewed-workspace-manifest.json"
        source_manifest.parent.mkdir(parents=True)
        source_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        descriptor = {
            "schema": SCHEMA,
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
            "quarantine_disposition": "RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS",
            "authority": {
                "r2_publication": "DENIED_PENDING_SEPARATE_GATE",
                "selector_activation": "DENIED",
                "opt_b_handoff": "DENIED",
                "market": "NONE",
            },
        }
        descriptor["descriptor_sha256"] = canonical_json_sha256(descriptor)
        descriptor_path = release_root / "release-descriptor.json"
        descriptor_path.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        inventory = _inventory(release_root)
        inventory_document = {
            "schema": "ovc-opt-a-role-release-inventory/v1",
            "release_id": release_id,
            "files": inventory,
            "file_count": len(inventory),
            "total_size_bytes": sum(int(item["size_bytes"]) for item in inventory),
        }
        inventory_document["inventory_sha256"] = canonical_json_sha256(inventory_document)
        inventory_path = release_root / "release-inventory.json"
        inventory_path.write_text(json.dumps(inventory_document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        final_inventory = _inventory(release_root)
        receipt = {
            "schema": FREEZE_RECEIPT_SCHEMA,
            "programme_id": PROGRAMME_ID,
            "gate_id": GATE_ID,
            "release_id": release_id,
            "role": role,
            "result": "PASS",
            "source_commit": source_commit,
            "source_workspace_manifest_sha256": manifest["manifest_sha256"],
            "release_inventory_sha256": inventory_document["inventory_sha256"],
            "release_file_count": len(final_inventory),
            "release_total_size_bytes": sum(int(item["size_bytes"]) for item in final_inventory),
            "release_root": release_root.as_posix(),
            "overwrite_policy": "DENIED",
            "quarantine_disposition": "RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS",
            "authority": descriptor["authority"],
        }
        receipt["receipt_sha256"] = canonical_json_sha256(receipt)
        (release_root / "freeze-receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return receipt
    except Exception:
        shutil.rmtree(release_root, ignore_errors=True)
        raise


def freeze_all_roles(*, workspaces_root: Path, output_root: Path, source_commit: str) -> dict[str, Any]:
    receipts = {
        role: freeze_role_release(
            workspace=workspaces_root / role.lower(),
            output_root=output_root,
            role=role,
            source_commit=source_commit,
        )
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
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "A2_G3_FREEZE_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
