from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Callable

from .manifest import (
    EvidenceStoreError,
    remote_keys,
    validate_manifest,
    verify_local,
)


Runner = Callable[..., subprocess.CompletedProcess[bytes]]


def _remote_target(remote: str, key: str) -> str:
    if not remote or any(char in remote for char in "\r\n"):
        raise EvidenceStoreError("remote must be a non-empty rclone remote without newlines")
    if remote.endswith(":"):
        return f"{remote}{key}"
    return f"{remote}:{key}"


def _run(arguments: list[str], runner: Runner) -> subprocess.CompletedProcess[bytes]:
    try:
        result = runner(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except OSError as exc:
        raise EvidenceStoreError(f"cannot execute rclone: {exc}") from exc
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise EvidenceStoreError(
            f"rclone failed with exit code {result.returncode}: {stderr or '(no error text)'}"
        )
    return result


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
        _run(
            ["rclone", "copyto", "--immutable", str(local), _remote_target(remote, file_keys[record["path"]])],
            runner,
        )
    _run(
        ["rclone", "copyto", "--immutable", str(manifest_path), _remote_target(remote, manifest_key)],
        runner,
    )


def verify_remote(
    document: dict[str, Any],
    manifest_path: Path,
    remote: str,
    *,
    runner: Runner = subprocess.run,
) -> None:
    validate_manifest(document)
    manifest_key, file_keys = remote_keys(document)
    expected_manifest = manifest_path.read_bytes()
    remote_manifest = _run(
        ["rclone", "cat", _remote_target(remote, manifest_key)], runner
    ).stdout
    if remote_manifest != expected_manifest:
        raise EvidenceStoreError("remote manifest byte content does not match the local manifest")
    for record in document["files"]:
        content = _run(
            ["rclone", "cat", _remote_target(remote, file_keys[record["path"]])], runner
        ).stdout
        size = len(content)
        digest = hashlib.sha256(content).hexdigest()
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
