from __future__ import annotations

import hashlib
import io
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, BinaryIO, Callable

from .manifest import (
    EvidenceStoreError,
    remote_keys,
    validate_manifest,
    verify_local,
)


Runner = Callable[..., subprocess.CompletedProcess[bytes]]
PopenFactory = Callable[..., subprocess.Popen[bytes]]
_REMOTE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_RCLONE_READ_FLAGS = ["--s3-no-check-bucket"]
_RCLONE_WRITE_FLAGS = ["--immutable", "--s3-no-check-bucket"]
_BUFFER_SIZE = 1024 * 1024


def _remote_target(remote: str, key: str) -> str:
    if not isinstance(remote, str) or not _REMOTE_RE.fullmatch(remote):
        raise EvidenceStoreError(
            "remote must be an rclone remote name using only ASCII letters, "
            "digits, '.', '_' or '-', without ':'"
        )
    return f"{remote}:{key}"


def _run(
    arguments: list[str],
    runner: Runner,
    *,
    logical_path: str,
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = runner(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except OSError as exc:
        raise EvidenceStoreError(
            f"cannot execute rclone for {logical_path!r}: {exc}"
        ) from exc
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise EvidenceStoreError(
            f"rclone failed for {logical_path!r} with exit code "
            f"{result.returncode}: {stderr or '(no error text)'}"
        )
    return result


def _stream_hash(stream: BinaryIO) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(_BUFFER_SIZE):
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def _cat_bytes_for_test(
    arguments: list[str], runner: Runner, *, logical_path: str
) -> tuple[str, int, bytes]:
    result = _run(arguments, runner, logical_path=logical_path)
    digest, size = _stream_hash(io.BytesIO(result.stdout))
    return digest, size, result.stdout


def _cat_streaming(
    arguments: list[str],
    *,
    logical_path: str,
    popen_factory: PopenFactory,
    capture_bytes: bool,
) -> tuple[str, int, bytes | None]:
    try:
        process = popen_factory(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise EvidenceStoreError(
            f"cannot execute rclone for {logical_path!r}: {exc}"
        ) from exc
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise EvidenceStoreError(f"rclone pipes unavailable for {logical_path!r}")
    digest = hashlib.sha256()
    size = 0
    captured = bytearray() if capture_bytes else None
    while chunk := process.stdout.read(_BUFFER_SIZE):
        digest.update(chunk)
        size += len(chunk)
        if captured is not None:
            captured.extend(chunk)
    stderr = process.stderr.read()
    return_code = process.wait()
    if return_code != 0:
        error_text = stderr.decode("utf-8", errors="replace").strip()
        raise EvidenceStoreError(
            f"rclone failed for {logical_path!r} with exit code "
            f"{return_code}: {error_text or '(no error text)'}"
        )
    return digest.hexdigest(), size, bytes(captured) if captured is not None else None


def upload(
    document: dict[str, Any],
    manifest_path: Path,
    root: Path,
    remote: str,
    *,
    runner: Runner = subprocess.run,
) -> None:
    validate_manifest(document)
    verify_local(document, root)
    manifest_key, file_keys = remote_keys(document)
    for record in document["files"]:
        local = root.joinpath(*PurePosixPath(record["path"]).parts)
        logical_path = file_keys[record["path"]]
        _run(
            [
                "rclone",
                "copyto",
                *_RCLONE_WRITE_FLAGS,
                str(local),
                _remote_target(remote, logical_path),
            ],
            runner,
            logical_path=logical_path,
        )
    _run(
        [
            "rclone",
            "copyto",
            *_RCLONE_WRITE_FLAGS,
            str(manifest_path),
            _remote_target(remote, manifest_key),
        ],
        runner,
        logical_path=manifest_key,
    )


def verify_remote(
    document: dict[str, Any],
    manifest_path: Path,
    remote: str,
    *,
    runner: Runner | None = None,
    popen_factory: PopenFactory = subprocess.Popen,
) -> None:
    validate_manifest(document)
    manifest_key, file_keys = remote_keys(document)
    expected_manifest = manifest_path.read_bytes()
    manifest_arguments = [
        "rclone",
        "cat",
        *_RCLONE_READ_FLAGS,
        _remote_target(remote, manifest_key),
    ]
    if runner is None:
        _, _, streamed_manifest = _cat_streaming(
            manifest_arguments,
            logical_path=manifest_key,
            popen_factory=popen_factory,
            capture_bytes=True,
        )
        assert streamed_manifest is not None
        remote_manifest = streamed_manifest
    else:
        _, _, remote_manifest = _cat_bytes_for_test(
            manifest_arguments, runner, logical_path=manifest_key
        )
    if remote_manifest != expected_manifest:
        raise EvidenceStoreError("remote manifest byte content does not match the local manifest")
    for record in document["files"]:
        logical_path = file_keys[record["path"]]
        arguments = [
            "rclone",
            "cat",
            *_RCLONE_READ_FLAGS,
            _remote_target(remote, logical_path),
        ]
        if runner is None:
            digest, size, _ = _cat_streaming(
                arguments,
                logical_path=logical_path,
                popen_factory=popen_factory,
                capture_bytes=False,
            )
        else:
            digest, size, _ = _cat_bytes_for_test(
                arguments, runner, logical_path=logical_path
            )
        if size != record["size"]:
            raise EvidenceStoreError(
                f"remote byte-size mismatch for {record['path']!r}: "
                f"expected {record['size']}, got {size}"
            )
        if digest != record["sha256"]:
            raise EvidenceStoreError(
                f"remote SHA-256 mismatch for {record['path']!r}: "
                f"expected {record['sha256']}, got {digest}"
            )
