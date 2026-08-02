"""Deterministic copy-only compact evidence export bundles."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, Iterable

from .identity import IdentityError, canonical_json_bytes, canonical_sha256, normalize_relative_path, resolve_under, sha256_file


_PROFILE_SCHEMA = "ovc-compact-evidence-export-profile/v1"
_REQUEST_SCHEMA = "ovc-compact-evidence-export-request/v1"
_MANIFEST_SCHEMA = "ovc-compact-evidence-export-manifest/v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_EXPORT_ID_RE = re.compile(r"^DA-EXPORT-[A-Z0-9._-]+$")
_POSIX_PRIVATE_PATH_RE = re.compile(r"/(?:home|Users)/[^/\s]+/", re.IGNORECASE)


class EvidenceExportError(ValueError):
    """Fail-closed compact evidence export error with a stable code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ExportProfile:
    profile_id: str
    programme_id: str
    active: bool
    allowed_source_roots: tuple[str, ...]
    allowed_extensions: tuple[str, ...]
    max_file_bytes: int
    max_bundle_bytes: int
    denied_path_suffixes: tuple[str, ...]
    denied_content_tokens: tuple[str, ...]


@dataclass(frozen=True)
class ExportFile:
    path: str
    size_bytes: int
    sha256: str
    role: str


@dataclass(frozen=True)
class ExportRequest:
    export_id: str
    programme_id: str
    profile_id: str
    source_commit: str
    files: tuple[ExportFile, ...]


@dataclass(frozen=True)
class ExportPlan:
    bundle_id: str
    repository_root: Path
    external_root: Path
    destination: Path
    staging: Path
    request: ExportRequest
    profile: ExportProfile
    files: tuple[ExportFile, ...]
    manifest: dict[str, Any]


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceExportError("INVALID_JSON", str(path)) from exc
    if not isinstance(value, dict):
        raise EvidenceExportError("INVALID_JSON", "root must be an object")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], *, label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise EvidenceExportError("CLOSED_SCHEMA_MISMATCH", f"{label} keys differ: {sorted(actual ^ expected)}")


def _string_tuple(value: Any, *, field: str, nonempty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or (nonempty and not value) or any(not isinstance(item, str) or not item for item in value):
        raise EvidenceExportError("INVALID_PROFILE", field)
    return tuple(value)


def load_profile(path: Path) -> ExportProfile:
    value = _load_json_object(path)
    expected = {
        "schema", "profile_id", "programme_id", "status", "active",
        "allowed_source_roots", "allowed_extensions", "max_file_bytes",
        "max_bundle_bytes", "denied_path_suffixes", "denied_content_tokens",
        "network_access", "repository_write", "remote_write", "accepted_bundle_deletion",
    }
    _exact_keys(value, expected, label="profile")
    if value["schema"] != _PROFILE_SCHEMA or value["status"] != "ACTIVE" or value["active"] is not True:
        raise EvidenceExportError("PROFILE_INACTIVE", "exact active profile is required")
    if not isinstance(value["profile_id"], str) or not isinstance(value["programme_id"], str):
        raise EvidenceExportError("INVALID_PROFILE", "profile identity")
    for field in ("network_access", "repository_write", "remote_write", "accepted_bundle_deletion"):
        if value[field] != "PROHIBITED":
            raise EvidenceExportError("AUTHORITY_EXCEEDED", f"{field} must be PROHIBITED")
    if type(value["max_file_bytes"]) is not int or value["max_file_bytes"] < 1:
        raise EvidenceExportError("INVALID_PROFILE", "max_file_bytes")
    if type(value["max_bundle_bytes"]) is not int or value["max_bundle_bytes"] < value["max_file_bytes"]:
        raise EvidenceExportError("INVALID_PROFILE", "max_bundle_bytes")
    roots = tuple(normalize_relative_path(item) for item in _string_tuple(value["allowed_source_roots"], field="allowed_source_roots"))
    extensions = _string_tuple(value["allowed_extensions"], field="allowed_extensions")
    denied_suffixes = tuple(item.lower() for item in _string_tuple(value["denied_path_suffixes"], field="denied_path_suffixes"))
    denied_tokens = _string_tuple(value["denied_content_tokens"], field="denied_content_tokens")
    if any(not item.startswith(".") or item != item.lower() for item in extensions):
        raise EvidenceExportError("INVALID_PROFILE", "allowed_extensions")
    if len(set(roots)) != len(roots) or len(set(extensions)) != len(extensions):
        raise EvidenceExportError("INVALID_PROFILE", "duplicate roots or extensions")
    return ExportProfile(
        profile_id=value["profile_id"],
        programme_id=value["programme_id"],
        active=True,
        allowed_source_roots=roots,
        allowed_extensions=extensions,
        max_file_bytes=value["max_file_bytes"],
        max_bundle_bytes=value["max_bundle_bytes"],
        denied_path_suffixes=denied_suffixes,
        denied_content_tokens=denied_tokens,
    )


def load_request(path: Path) -> ExportRequest:
    value = _load_json_object(path)
    _exact_keys(value, {"schema", "export_id", "programme_id", "profile_id", "source_commit", "files"}, label="request")
    if value["schema"] != _REQUEST_SCHEMA:
        raise EvidenceExportError("REQUEST_SCHEMA_MISMATCH", str(value["schema"]))
    if any(not isinstance(value[field], str) for field in ("export_id", "programme_id", "profile_id", "source_commit")):
        raise EvidenceExportError("INVALID_REQUEST", "identity fields must be strings")
    export_id = value["export_id"]
    source_commit = value["source_commit"]
    if not _EXPORT_ID_RE.fullmatch(export_id):
        raise EvidenceExportError("INVALID_EXPORT_ID", export_id)
    if not _COMMIT_RE.fullmatch(source_commit):
        raise EvidenceExportError("INVALID_SOURCE_COMMIT", source_commit)
    rows = value["files"]
    if not isinstance(rows, list) or not rows:
        raise EvidenceExportError("EMPTY_EXPORT", "at least one file is required")
    files: list[ExportFile] = []
    seen: set[str] = set()
    allowed_roles = {"CONTRACT", "SCHEMA", "REGISTRY", "PACKET", "QA", "DECISION", "RECEIPT", "DOCUMENTATION"}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise EvidenceExportError("INVALID_FILE_ROW", str(index))
        _exact_keys(row, {"path", "size_bytes", "sha256", "role"}, label=f"file[{index}]")
        if not isinstance(row["path"], str) or not isinstance(row["sha256"], str) or not isinstance(row["role"], str):
            raise EvidenceExportError("INVALID_FILE_ROW", str(index))
        try:
            logical_path = normalize_relative_path(row["path"])
        except IdentityError as exc:
            raise EvidenceExportError("UNSAFE_PATH", row["path"]) from exc
        if logical_path in seen:
            raise EvidenceExportError("DUPLICATE_PATH", logical_path)
        seen.add(logical_path)
        size = row["size_bytes"]
        digest = row["sha256"]
        role = row["role"]
        if type(size) is not int or size < 0:
            raise EvidenceExportError("INVALID_SIZE", logical_path)
        if not _SHA256_RE.fullmatch(digest):
            raise EvidenceExportError("INVALID_SHA256", logical_path)
        if role not in allowed_roles:
            raise EvidenceExportError("INVALID_ROLE", role)
        files.append(ExportFile(logical_path, size, digest, role))
    return ExportRequest(
        export_id=export_id,
        programme_id=value["programme_id"],
        profile_id=value["profile_id"],
        source_commit=source_commit,
        files=tuple(files),
    )


def _is_under_allowed_root(path: str, roots: Iterable[str]) -> bool:
    return any(path.startswith(root.rstrip("/") + "/") for root in roots)


def _assert_no_symlink(root: Path, logical_path: str) -> None:
    cursor = root.resolve()
    for part in logical_path.split("/"):
        cursor = cursor / part
        if cursor.is_symlink():
            raise EvidenceExportError("SYMLINK_PROHIBITED", logical_path)


def _assert_destination(repository_root: Path, external_root: Path) -> tuple[Path, Path]:
    if not external_root.is_absolute():
        raise EvidenceExportError("EXTERNAL_ROOT_NOT_ABSOLUTE", str(external_root))
    repo = repository_root.resolve()
    external = external_root.resolve(strict=False)
    try:
        external.relative_to(repo)
    except ValueError:
        pass
    else:
        raise EvidenceExportError("EXTERNAL_ROOT_INSIDE_REPOSITORY", str(external))
    if external == repo:
        raise EvidenceExportError("EXTERNAL_ROOT_INSIDE_REPOSITORY", str(external))
    return repo, external


def _scan_content(path: Path, profile: ExportProfile, logical_path: str) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise EvidenceExportError("NON_UTF8_COMPACT_EVIDENCE", logical_path) from exc
    for token in profile.denied_content_tokens:
        if token in text:
            raise EvidenceExportError("DENIED_CONTENT", f"{logical_path}:{token}")
    if _POSIX_PRIVATE_PATH_RE.search(text):
        raise EvidenceExportError("PRIVATE_ABSOLUTE_PATH", logical_path)


def build_plan(repository_root: Path, external_root: Path, request: ExportRequest, profile: ExportProfile) -> ExportPlan:
    repo, external = _assert_destination(repository_root, external_root)
    if not profile.active:
        raise EvidenceExportError("PROFILE_INACTIVE", profile.profile_id)
    if request.profile_id != profile.profile_id or request.programme_id != profile.programme_id:
        raise EvidenceExportError("PROFILE_IDENTITY_MISMATCH", request.export_id)

    normalized: list[ExportFile] = []
    total = 0
    for item in request.files:
        logical_path = normalize_relative_path(item.path)
        suffix = Path(logical_path).suffix.lower()
        if not _is_under_allowed_root(logical_path, profile.allowed_source_roots):
            raise EvidenceExportError("SOURCE_ROOT_NOT_ALLOWED", logical_path)
        if suffix in profile.denied_path_suffixes or suffix not in profile.allowed_extensions:
            raise EvidenceExportError("FILE_TYPE_NOT_ALLOWED", logical_path)
        _assert_no_symlink(repo, logical_path)
        source = resolve_under(repo, logical_path)
        if not source.is_file():
            raise EvidenceExportError("SOURCE_NOT_REGULAR_FILE", logical_path)
        actual_size = source.stat().st_size
        if actual_size != item.size_bytes:
            raise EvidenceExportError("SIZE_MISMATCH", logical_path)
        if actual_size > profile.max_file_bytes:
            raise EvidenceExportError("CAPACITY_EXCEEDED", logical_path)
        actual_hash = sha256_file(source)
        if actual_hash != item.sha256:
            raise EvidenceExportError("SHA256_MISMATCH", logical_path)
        _scan_content(source, profile, logical_path)
        total += actual_size
        if total > profile.max_bundle_bytes:
            raise EvidenceExportError("CAPACITY_EXCEEDED", request.export_id)
        normalized.append(ExportFile(logical_path, actual_size, actual_hash, item.role))

    normalized.sort(key=lambda row: row.path)
    identity_content = {
        "profile_id": profile.profile_id,
        "programme_id": profile.programme_id,
        "source_commit": request.source_commit,
        "files": [
            {"path": row.path, "size_bytes": row.size_bytes, "sha256": row.sha256, "role": row.role}
            for row in normalized
        ],
    }
    bundle_id = canonical_sha256(identity_content, role="OVC_COMPACT_EVIDENCE_EXPORT_BUNDLE")
    manifest = {
        "schema": _MANIFEST_SCHEMA,
        "programme_id": request.programme_id,
        "profile_id": request.profile_id,
        "source_commit": request.source_commit,
        "bundle_id": bundle_id,
        "file_count": len(normalized),
        "total_bytes": total,
        "files": [
            {"path": row.path, "size_bytes": row.size_bytes, "sha256": row.sha256, "role": row.role}
            for row in normalized
        ],
        "authority": {
            "mode": "LOCAL_COPY_ONLY",
            "network_access": "PROHIBITED",
            "repository_write": "PROHIBITED",
            "remote_write": "PROHIBITED",
            "accepted_bundle_deletion": "PROHIBITED",
        },
    }
    base = external / "development-acceleration" / "compact-evidence"
    return ExportPlan(
        bundle_id=bundle_id,
        repository_root=repo,
        external_root=external,
        destination=base / bundle_id,
        staging=base / f".{bundle_id}.staging",
        request=request,
        profile=profile,
        files=tuple(normalized),
        manifest=manifest,
    )


def _manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return canonical_json_bytes(manifest) + b"\n"


def verify_bundle(plan: ExportPlan) -> None:
    manifest_path = plan.destination / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise EvidenceExportError("DESTINATION_COLLISION", "manifest missing or unsafe")
    if manifest_path.read_bytes() != _manifest_bytes(plan.manifest):
        raise EvidenceExportError("DESTINATION_COLLISION", "manifest differs")
    for item in plan.files:
        exported = resolve_under(plan.destination / "files", item.path)
        if not exported.is_file() or exported.is_symlink():
            raise EvidenceExportError("DESTINATION_COLLISION", item.path)
        if exported.stat().st_size != item.size_bytes or sha256_file(exported) != item.sha256:
            raise EvidenceExportError("DESTINATION_COLLISION", item.path)


def _quarantine_staging(plan: ExportPlan) -> Path:
    quarantine_root = plan.staging.parent / "quarantine"
    quarantine_root.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        candidate = quarantine_root / f"{plan.bundle_id}.{index:04d}"
        if not candidate.exists():
            os.replace(plan.staging, candidate)
            return candidate
        index += 1


def execute_export(plan: ExportPlan) -> dict[str, Any]:
    plan.destination.parent.mkdir(parents=True, exist_ok=True)
    if plan.destination.exists():
        verify_bundle(plan)
        return {
            "status": "IDEMPOTENT_REUSE",
            "export_id": plan.request.export_id,
            "bundle_id": plan.bundle_id,
            "bundle_directory": str(plan.destination),
            "manifest_sha256": canonical_sha256(plan.manifest, role="OVC_COMPACT_EVIDENCE_EXPORT_MANIFEST"),
        }
    if plan.staging.exists():
        _quarantine_staging(plan)
    plan.staging.mkdir(parents=True, exist_ok=False)
    try:
        files_root = plan.staging / "files"
        for item in plan.files:
            source = resolve_under(plan.repository_root, item.path)
            target = resolve_under(files_root, item.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if target.stat().st_size != item.size_bytes or sha256_file(target) != item.sha256:
                raise EvidenceExportError("COPY_VERIFICATION_FAILED", item.path)
        (plan.staging / "manifest.json").write_bytes(_manifest_bytes(plan.manifest))
        os.replace(plan.staging, plan.destination)
        verify_bundle(plan)
    except Exception:
        if plan.staging.exists():
            _quarantine_staging(plan)
        raise
    return {
        "status": "PASS",
        "export_id": plan.request.export_id,
        "bundle_id": plan.bundle_id,
        "bundle_directory": str(plan.destination),
        "manifest_sha256": canonical_sha256(plan.manifest, role="OVC_COMPACT_EVIDENCE_EXPORT_MANIFEST"),
    }
