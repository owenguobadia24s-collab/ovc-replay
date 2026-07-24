from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import unicodedata
from typing import Any, BinaryIO


MANIFEST_SCHEMA = "ovc-evidence-release-manifest/v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_BUFFER_SIZE = 1024 * 1024


class EvidenceStoreError(Exception):
    """An expected evidence-store validation or I/O failure."""


def _validated_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise EvidenceStoreError(
            f"{field} must be 1-128 ASCII letters, digits, '.', '_' or '-', "
            "starting with a letter or digit"
        )
    if value in {".", ".."}:
        raise EvidenceStoreError(f"{field} may not be '.' or '..'")
    return value


def validate_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise EvidenceStoreError("release path must be a non-empty string")
    if "\\" in value or any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise EvidenceStoreError(
            f"release path must use '/' and contain no control characters: {value!r}"
        )
    if unicodedata.normalize("NFC", value) != value:
        raise EvidenceStoreError(f"release path must be Unicode NFC: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith("/") or path.as_posix() != value:
        raise EvidenceStoreError(f"release path is not canonical relative POSIX form: {value!r}")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise EvidenceStoreError(f"release path contains an unsafe component: {value!r}")
    if ":" in value.split("/")[0]:
        raise EvidenceStoreError(f"release path may not contain a drive prefix: {value!r}")
    return value


def _hash_stream(stream: BinaryIO) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(_BUFFER_SIZE):
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def hash_file(path: Path) -> tuple[str, int]:
    try:
        with path.open("rb") as stream:
            return _hash_stream(stream)
    except OSError as exc:
        raise EvidenceStoreError(f"cannot read release file {path}: {exc}") from exc


def canonical_json_bytes(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical_json_bytes(document))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise EvidenceStoreError(f"cannot atomically write manifest {path}: {exc}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _root_file(root: Path, relative: str) -> Path:
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    current = root
    for component in PurePosixPath(relative).parts:
        current = current / component
        if current.is_symlink():
            raise EvidenceStoreError(f"symbolic links are not permitted: {relative!r}")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise EvidenceStoreError(f"missing or inaccessible release file {relative!r}: {exc}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise EvidenceStoreError(f"release path escapes root: {relative!r}") from exc
    if not resolved.is_file():
        raise EvidenceStoreError(f"release path is not a regular file: {relative!r}")
    return resolved


def _file_records(root: Path, excluded: Path | None) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    aliases: dict[str, str] = {}
    try:
        candidates = list(root.rglob("*"))
    except OSError as exc:
        raise EvidenceStoreError(f"cannot enumerate release root {root}: {exc}") from exc
    for candidate in candidates:
        if candidate.is_symlink():
            raise EvidenceStoreError(f"symbolic links are not permitted: {candidate}")
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if excluded is not None and resolved == excluded:
            continue
        relative = validate_relative_path(candidate.relative_to(root).as_posix())
        alias = unicodedata.normalize("NFC", relative).casefold()
        if alias in aliases:
            raise EvidenceStoreError(
                f"duplicate/colliding release paths: {aliases[alias]!r} and {relative!r}"
            )
        aliases[alias] = relative
        sha256, size = hash_file(resolved)
        records.append({"path": relative, "sha256": sha256, "size": size})
    records.sort(key=lambda item: str(item["path"]).encode("utf-8"))
    return records


def build_manifest(
    *,
    root: Path,
    output: Path,
    release_id: str,
    manifest_id: str,
    bucket: str,
    prefix: str,
    authority_state: str,
    repository_commit: str,
    source_ref: str,
) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise EvidenceStoreError(f"release root is not a directory: {root}")
    output_resolved = output.resolve()
    prefix_value = validate_prefix(prefix)
    fields = {
        "release_id": _validated_id(release_id, "release-id"),
        "manifest_id": _validated_id(manifest_id, "manifest-id"),
        "bucket": _validated_id(bucket, "bucket"),
        "authority_state": _required_text(authority_state, "authority-state"),
        "repository_commit": _required_text(repository_commit, "repository-commit"),
        "source_ref": _required_text(source_ref, "source-ref"),
    }
    document: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        **fields,
        "prefix": prefix_value,
        "files": _file_records(root, output_resolved),
    }
    atomic_write_json(output, document)
    return document


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or any(ord(char) < 32 for char in value):
        raise EvidenceStoreError(f"{field} must be a non-empty string without control characters")
    return value


def validate_prefix(value: object) -> str:
    if not isinstance(value, str):
        raise EvidenceStoreError("prefix must be a string")
    if value == "":
        return ""
    canonical = value.strip("/")
    if canonical != value:
        raise EvidenceStoreError("prefix must not start or end with '/'")
    validate_relative_path(canonical)
    return canonical


def validate_manifest(document: object) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise EvidenceStoreError("manifest must be a JSON object")
    required = {
        "schema", "release_id", "manifest_id", "bucket", "prefix",
        "authority_state", "repository_commit", "source_ref", "files",
    }
    if set(document) != required:
        missing = sorted(required - set(document))
        extra = sorted(set(document) - required)
        raise EvidenceStoreError(f"manifest fields invalid; missing={missing}, extra={extra}")
    if document["schema"] != MANIFEST_SCHEMA:
        raise EvidenceStoreError(f"unsupported manifest schema: {document['schema']!r}")
    _validated_id(document["release_id"], "release_id")
    _validated_id(document["manifest_id"], "manifest_id")
    _validated_id(document["bucket"], "bucket")
    validate_prefix(document["prefix"])
    for field in ("authority_state", "repository_commit", "source_ref"):
        _required_text(document[field], field)
    files = document["files"]
    if not isinstance(files, list):
        raise EvidenceStoreError("manifest files must be an array")
    aliases: dict[str, str] = {}
    previous: bytes | None = None
    for index, record in enumerate(files):
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "size"}:
            raise EvidenceStoreError(f"invalid file record at index {index}")
        path = validate_relative_path(record["path"])
        alias = unicodedata.normalize("NFC", path).casefold()
        if alias in aliases:
            raise EvidenceStoreError(
                f"duplicate/colliding manifest paths: {aliases[alias]!r} and {path!r}"
            )
        aliases[alias] = path
        order_key = path.encode("utf-8")
        if previous is not None and order_key <= previous:
            raise EvidenceStoreError("manifest file records are not in canonical UTF-8 order")
        previous = order_key
        if not isinstance(record["sha256"], str) or not _SHA256_RE.fullmatch(record["sha256"]):
            raise EvidenceStoreError(f"invalid SHA-256 for {path!r}")
        if not isinstance(record["size"], int) or isinstance(record["size"], bool) or record["size"] < 0:
            raise EvidenceStoreError(f"invalid byte size for {path!r}")
    return document


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise EvidenceStoreError(f"cannot read manifest {path}: {exc}") from exc
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceStoreError(f"manifest is not valid UTF-8 JSON: {exc}") from exc
    return validate_manifest(document)


def verify_local(document: dict[str, Any], root: Path) -> None:
    validate_manifest(document)
    root = root.resolve()
    if not root.is_dir():
        raise EvidenceStoreError(f"release root is not a directory: {root}")
    for record in document["files"]:
        path = _root_file(root, record["path"])
        sha256, size = hash_file(path)
        if size != record["size"]:
            raise EvidenceStoreError(
                f"byte-size mismatch for {record['path']!r}: expected {record['size']}, got {size}"
            )
        if sha256 != record["sha256"]:
            raise EvidenceStoreError(
                f"SHA-256 mismatch for {record['path']!r}: expected "
                f"{record['sha256']}, got {sha256}"
            )


def remote_keys(document: dict[str, Any]) -> tuple[str, dict[str, str]]:
    validate_manifest(document)
    base_parts = [
        part for part in (
            document["prefix"],
            "releases",
            document["release_id"],
            document["manifest_id"],
        ) if part
    ]
    base = "/".join(base_parts)
    manifest_key = f"{base}/manifest.json"
    file_keys = {
        record["path"]: f"{base}/files/{record['path']}" for record in document["files"]
    }
    return manifest_key, file_keys
