"""Compact artifact references and exact byte verification."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .identity import canonical_sha256, normalize_relative_path, resolve_under, sha256_file


@dataclass(frozen=True)
class ArtifactRef:
    logical_name: str
    relative_path: str
    size_bytes: int
    sha256: str
    schema_id: str | None = None
    media_type: str = "application/octet-stream"
    identity_policy: str = "EXACT_FILE"

    def __post_init__(self) -> None:
        normalize_relative_path(self.relative_path)
        if not self.logical_name:
            raise ValueError("logical_name is required")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")
        if len(self.sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.sha256):
            raise ValueError("sha256 must be lowercase hexadecimal")

    @property
    def logical_hash(self) -> str:
        return canonical_sha256(asdict(self), role="ARTIFACT_REF")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_artifact(root: Path, ref: ArtifactRef) -> dict[str, Any]:
    path = resolve_under(root, ref.relative_path)
    if not path.is_file():
        return {"status": "BLOCK", "reason": "MISSING_FILE", "path": ref.relative_path}
    if path.is_symlink():
        return {"status": "BLOCK", "reason": "SYMLINK_PROHIBITED", "path": ref.relative_path}
    size = path.stat().st_size
    if size != ref.size_bytes:
        return {
            "status": "BLOCK",
            "reason": "SIZE_MISMATCH",
            "expected": ref.size_bytes,
            "actual": size,
            "path": ref.relative_path,
        }
    digest = sha256_file(path)
    if digest != ref.sha256:
        return {
            "status": "BLOCK",
            "reason": "SHA256_MISMATCH",
            "expected": ref.sha256,
            "actual": digest,
            "path": ref.relative_path,
        }
    return {
        "status": "PASS",
        "reason": "EXACT_BYTES_VERIFIED",
        "path": ref.relative_path,
        "size_bytes": size,
        "sha256": digest,
        "artifact_ref_hash": ref.logical_hash,
    }
