"""Canonical serialization, identity roles and safe logical paths."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath
from typing import Any


class IdentityError(ValueError):
    """Raised when content cannot receive a lawful deterministic identity."""


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise IdentityError("non-finite floating point values are prohibited")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise IdentityError("canonical object keys must be strings")
            _reject_non_finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_non_finite(item)


def canonical_json_bytes(value: Any) -> bytes:
    """Return UTF-8 canonical JSON bytes with no machine-specific fields added."""
    _reject_non_finite(value)
    text = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return text.encode("utf-8")


def canonical_sha256(value: Any, *, role: str | None = None) -> str:
    """Hash canonical logical content, optionally binding an explicit identity role."""
    payload: Any = value if role is None else {"identity_role": role, "logical_content": value}
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_relative_path(raw: str) -> str:
    """Normalize a repository-relative logical path and reject traversal/absolute paths."""
    if not raw or "\x00" in raw:
        raise IdentityError("path is empty or contains NUL")
    candidate = raw.replace("\\", "/")
    if candidate.startswith("/") or ":" in candidate.split("/", 1)[0]:
        raise IdentityError("absolute or drive-qualified paths are prohibited")
    path = PurePosixPath(candidate)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise IdentityError("path traversal or ambiguous segments are prohibited")
    normalized = path.as_posix()
    if normalized.startswith(".git/") or normalized == ".git":
        raise IdentityError("Git internals are prohibited")
    return normalized


def resolve_under(root: Path, relative_path: str) -> Path:
    """Resolve a normalized logical path beneath root without following escape paths."""
    normalized = normalize_relative_path(relative_path)
    root_resolved = root.resolve()
    candidate = (root_resolved / normalized).resolve(strict=False)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise IdentityError("resolved path escapes logical root") from exc
    return candidate
