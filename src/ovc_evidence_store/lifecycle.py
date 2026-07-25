from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Any, Iterable

from .manifest import (
    EvidenceStoreError,
    atomic_write_json,
    canonical_json_bytes,
    hash_file,
    validate_manifest,
    validate_relative_path,
)


WORKSPACE_INVENTORY_SCHEMA = "ovc-evidence-workspace-inventory/v1"
FREEZE_RECEIPT_SCHEMA = "ovc-evidence-freeze-receipt/v1"
PUBLICATION_APPROVAL_SCHEMA = "ovc-opt-a-publication-approval/v0.2"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def validate_identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise EvidenceStoreError(
            f"{field} must be 1-128 ASCII letters, digits, '.', '_' or '-', "
            "starting with a letter or digit"
        )
    if value in {".", ".."}:
        raise EvidenceStoreError(f"{field} may not be '.' or '..'")
    return value


def _safe_child(root: Path, identifier: str, field: str) -> Path:
    value = validate_identifier(identifier, field)
    candidate = root / value
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise EvidenceStoreError(f"unsafe {field}: {identifier!r}") from exc
    return candidate


def _ensure_plain_directory(path: Path, *, create: bool = False) -> Path:
    if create:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise EvidenceStoreError(f"cannot create directory {path}: {exc}") from exc
    if path.is_symlink() or not path.is_dir():
        raise EvidenceStoreError(f"required directory is missing or unsafe: {path}")
    return path


def init_workspace(external_root: Path, workspace_id: str) -> Path:
    """Create a new mutable workspace without creating a release root."""

    external_root = _ensure_plain_directory(external_root)
    intake_root = external_root / "intake"
    workspace_root = external_root / "workspace"
    _ensure_plain_directory(intake_root, create=True)
    _ensure_plain_directory(workspace_root, create=True)

    target = _safe_child(workspace_root, workspace_id, "workspace-id")
    if target.exists() or target.is_symlink():
        raise EvidenceStoreError(f"workspace already exists: {target}")
    try:
        target.mkdir()
    except OSError as exc:
        raise EvidenceStoreError(f"cannot create workspace {target}: {exc}") from exc
    return target


def _inventory_records(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    aliases: dict[str, str] = {}
    try:
        candidates = list(root.rglob("*"))
    except OSError as exc:
        raise EvidenceStoreError(f"cannot enumerate workspace {root}: {exc}") from exc
    for candidate in candidates:
        if candidate.is_symlink():
            raise EvidenceStoreError(f"symbolic links are not permitted: {candidate}")
        if not candidate.is_file():
            continue
        relative = validate_relative_path(candidate.relative_to(root).as_posix())
        alias = relative.casefold()
        if alias in aliases:
            raise EvidenceStoreError(
                f"duplicate/colliding workspace paths: {aliases[alias]!r} and {relative!r}"
            )
        aliases[alias] = relative
        sha256, size = hash_file(candidate)
        records.append({"path": relative, "sha256": sha256, "size": size})
    records.sort(key=lambda item: str(item["path"]).encode("utf-8"))
    return records


def build_workspace_inventory(workspace: Path, workspace_id: str) -> dict[str, Any]:
    workspace = _ensure_plain_directory(workspace)
    return {
        "schema": WORKSPACE_INVENTORY_SCHEMA,
        "workspace_id": validate_identifier(workspace_id, "workspace-id"),
        "files": _inventory_records(workspace),
        "unresolved": [],
    }


def validate_workspace_inventory(document: object) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise EvidenceStoreError("workspace inventory must be a JSON object")
    required = {"schema", "workspace_id", "files", "unresolved"}
    if set(document) != required:
        raise EvidenceStoreError("workspace inventory fields are invalid")
    if document["schema"] != WORKSPACE_INVENTORY_SCHEMA:
        raise EvidenceStoreError("unsupported workspace inventory schema")
    validate_identifier(document["workspace_id"], "workspace_id")
    if not isinstance(document["files"], list):
        raise EvidenceStoreError("workspace inventory files must be an array")
    if not isinstance(document["unresolved"], list):
        raise EvidenceStoreError("workspace inventory unresolved must be an array")
    if document["unresolved"]:
        raise EvidenceStoreError("workspace inventory contains unresolved items")

    previous: bytes | None = None
    aliases: set[str] = set()
    for index, record in enumerate(document["files"]):
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "size"}:
            raise EvidenceStoreError(f"invalid workspace file record at index {index}")
        path = validate_relative_path(record["path"])
        alias = path.casefold()
        if alias in aliases:
            raise EvidenceStoreError(f"duplicate/colliding workspace path: {path!r}")
        aliases.add(alias)
        order = path.encode("utf-8")
        if previous is not None and order <= previous:
            raise EvidenceStoreError("workspace file records are not in canonical order")
        previous = order
        if not isinstance(record["sha256"], str) or not _SHA256_RE.fullmatch(record["sha256"]):
            raise EvidenceStoreError(f"invalid workspace SHA-256 for {path!r}")
        if (
            not isinstance(record["size"], int)
            or isinstance(record["size"], bool)
            or record["size"] < 0
        ):
            raise EvidenceStoreError(f"invalid workspace byte size for {path!r}")
    return document


def load_workspace_inventory(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_bytes())
    except OSError as exc:
        raise EvidenceStoreError(f"cannot read workspace inventory {path}: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceStoreError(f"workspace inventory is not valid UTF-8 JSON: {exc}") from exc
    return validate_workspace_inventory(document)


def write_workspace_inventory(path: Path, document: dict[str, Any]) -> None:
    validate_workspace_inventory(document)
    atomic_write_json(path, document)


def _verify_inventory(root: Path, document: dict[str, Any]) -> None:
    validate_workspace_inventory(document)
    actual = _inventory_records(root)
    if actual != document["files"]:
        raise EvidenceStoreError("workspace bytes do not match the approved inventory")


def _copy_inventory(source: Path, target: Path, records: Iterable[dict[str, object]]) -> None:
    for record in records:
        relative = str(record["path"])
        source_file = source.joinpath(*PurePosixPath(relative).parts)
        target_file = target.joinpath(*PurePosixPath(relative).parts)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(source_file, target_file, follow_symlinks=False)
        except OSError as exc:
            raise EvidenceStoreError(f"cannot freeze release file {relative!r}: {exc}") from exc


def freeze_release(
    *,
    external_root: Path,
    workspace_id: str,
    release_id: str,
    qa_state: str,
    inventory: dict[str, Any],
) -> tuple[Path, Path, dict[str, Any]]:
    """Copy an approved workspace into a new immutable-identity release root."""

    if qa_state != "PASS":
        raise EvidenceStoreError("freeze-release requires qa-state PASS")
    external_root = _ensure_plain_directory(external_root)
    workspace_root = _ensure_plain_directory(external_root / "workspace")
    workspace = _safe_child(workspace_root, workspace_id, "workspace-id")
    _ensure_plain_directory(workspace)

    inventory = validate_workspace_inventory(inventory)
    if inventory["workspace_id"] != workspace_id:
        raise EvidenceStoreError("inventory workspace_id does not match requested workspace")
    _verify_inventory(workspace, inventory)

    releases_root = external_root / "releases"
    receipts_root = external_root / "receipts" / "freeze"
    _ensure_plain_directory(releases_root, create=True)
    _ensure_plain_directory(receipts_root, create=True)
    release = _safe_child(releases_root, release_id, "release-id")
    receipt_path = _safe_child(receipts_root, f"{release_id}.json", "freeze-receipt")
    if release.exists() or release.is_symlink():
        raise EvidenceStoreError(f"release already exists: {release}")
    if receipt_path.exists() or receipt_path.is_symlink():
        raise EvidenceStoreError(f"freeze receipt already exists: {receipt_path}")

    temporary = Path(tempfile.mkdtemp(prefix=f".{release_id}.freeze-", dir=releases_root))
    try:
        _copy_inventory(workspace, temporary, inventory["files"])
        _verify_inventory(temporary, inventory)
        try:
            os.replace(temporary, release)
        except OSError as exc:
            raise EvidenceStoreError(f"cannot atomically freeze release {release}: {exc}") from exc

        receipt = {
            "schema": FREEZE_RECEIPT_SCHEMA,
            "release_id": validate_identifier(release_id, "release-id"),
            "workspace_id": workspace_id,
            "qa_state": "PASS",
            "inventory_sha256": hashlib.sha256(canonical_json_bytes(inventory)).hexdigest(),
            "file_count": len(inventory["files"]),
            "total_size_bytes": sum(int(record["size"]) for record in inventory["files"]),
            "release_root": f"releases/{release_id}",
            "overwrite_policy": "DENIED",
        }
        atomic_write_json(receipt_path, receipt)
        return release, receipt_path, receipt
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        if release.exists() and not receipt_path.exists():
            shutil.rmtree(release, ignore_errors=True)
        raise


def validate_supersession(
    *,
    new_release_id: str,
    predecessor_release_id: str,
    existing_release_ids: Iterable[str],
    predecessor_disposition: str,
) -> None:
    new_id = validate_identifier(new_release_id, "new-release-id")
    predecessor_id = validate_identifier(predecessor_release_id, "predecessor-release-id")
    existing = set(existing_release_ids)
    if new_id == predecessor_id:
        raise EvidenceStoreError("new release ID may not reuse the predecessor identity")
    if new_id in existing:
        raise EvidenceStoreError(f"new release ID is already registered: {new_id}")
    if predecessor_id not in existing:
        raise EvidenceStoreError(f"predecessor release is not registered: {predecessor_id}")
    if predecessor_disposition not in {"SUPERSEDED_UNPUBLISHED", "SUPERSEDED", "HISTORICAL"}:
        raise EvidenceStoreError("predecessor disposition does not permit supersession")


def manifest_sha256(manifest_path: Path) -> str:
    try:
        return hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise EvidenceStoreError(f"cannot read manifest for approval binding: {exc}") from exc


def validate_publication_approval(
    document: object,
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    validate_manifest(manifest)
    if not isinstance(document, dict):
        raise EvidenceStoreError("publication approval must be a JSON object")
    required = {
        "schema",
        "approval_id",
        "decision",
        "release_id",
        "manifest_id",
        "manifest_sha256",
        "source_commit",
        "operator",
        "decision_recorded_at",
        "rollback_note",
    }
    if set(document) != required:
        raise EvidenceStoreError("publication approval fields are invalid")
    if document["schema"] != PUBLICATION_APPROVAL_SCHEMA:
        raise EvidenceStoreError("unsupported publication approval schema")
    validate_identifier(document["approval_id"], "approval-id")
    if document["decision"] != "APPROVE":
        raise EvidenceStoreError("publication approval decision is not APPROVE")
    if document["release_id"] != manifest["release_id"]:
        raise EvidenceStoreError("publication approval release_id mismatch")
    if document["manifest_id"] != manifest["manifest_id"]:
        raise EvidenceStoreError("publication approval manifest_id mismatch")
    if document["manifest_sha256"] != manifest_sha256(manifest_path):
        raise EvidenceStoreError("publication approval manifest SHA-256 mismatch")
    if document["source_commit"] != manifest["repository_commit"]:
        raise EvidenceStoreError("publication approval source_commit mismatch")
    for field in ("operator", "decision_recorded_at", "rollback_note"):
        value = document[field]
        if not isinstance(value, str) or not value.strip():
            raise EvidenceStoreError(f"publication approval {field} is required")
    return document


def load_publication_approval(
    path: Path,
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    try:
        document = json.loads(path.read_bytes())
    except OSError as exc:
        raise EvidenceStoreError(f"cannot read publication approval {path}: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceStoreError(f"publication approval is not valid UTF-8 JSON: {exc}") from exc
    return validate_publication_approval(document, manifest=manifest, manifest_path=manifest_path)
