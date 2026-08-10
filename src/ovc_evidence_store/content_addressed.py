from __future__ import annotations

from dataclasses import dataclass
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .manifest import EvidenceStoreError

DEFAULT_CHUNK_BYTES = 16 * 1024 * 1024
DEFAULT_COMPRESSION_LEVEL = 6


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _safe_namespace(value: str) -> str:
    namespace = str(value).strip().strip("/")
    if not namespace or namespace.startswith(".") or ".." in Path(namespace).parts:
        raise EvidenceStoreError("content-addressed namespace must be a non-empty relative path")
    return namespace


def _unit_name(unit_id: str) -> str:
    unit = str(unit_id).strip()
    if not unit:
        raise EvidenceStoreError("unit_id is required")
    return sha256(unit.encode("utf-8")).hexdigest() + ".json"


@dataclass(frozen=True)
class ArtifactReceipt:
    namespace: str
    unit_id: str
    manifest_sha256: str
    logical_output_sha256: str
    raw_output_sha256: str
    raw_output_bytes: int


class ContentAddressedArtifactStore:
    """Programme-neutral deterministic external artifact store.

    This component owns only physical evidence materialisation: deterministic
    chunking, deterministic gzip compression, content addressing, capacity
    enforcement, manifests and read-back verification.  It does not know or
    grant scientific, selector, release, Validation, probability, risk,
    exposure or execution authority.
    """

    def __init__(
        self,
        root: Path,
        *,
        namespace: str,
        max_external_bytes: int,
        chunk_bytes: int = DEFAULT_CHUNK_BYTES,
        compression_level: int = DEFAULT_COMPRESSION_LEVEL,
    ) -> None:
        self.root = Path(root)
        self.namespace = _safe_namespace(namespace)
        self.max_external_bytes = int(max_external_bytes)
        self.chunk_bytes = int(chunk_bytes)
        self.compression_level = int(compression_level)
        if self.max_external_bytes <= 0 or self.chunk_bytes <= 0:
            raise EvidenceStoreError("capacity and chunk_bytes must be positive")
        if not 0 <= self.compression_level <= 9:
            raise EvidenceStoreError("compression_level must be between 0 and 9")
        self._size_cache: int | None = None

    @property
    def namespace_root(self) -> Path:
        return self.root / "artifact_store" / self.namespace

    def _manifest_path(self, unit_id: str) -> Path:
        return self.namespace_root / "manifests" / _unit_name(unit_id)

    def _cas_path(self, raw_chunk_sha256: str) -> Path:
        digest = str(raw_chunk_sha256)
        return self.namespace_root / "cas" / "sha256" / digest[:2] / f"{digest}.gz"

    def total_bytes(self) -> int:
        if self._size_cache is None:
            base = self.namespace_root
            self._size_cache = (
                sum(path.stat().st_size for path in base.rglob("*") if path.is_file())
                if base.exists()
                else 0
            )
        return self._size_cache

    def _reserve(self, added_bytes: int) -> None:
        projected = self.total_bytes() + int(added_bytes)
        if projected > self.max_external_bytes:
            raise EvidenceStoreError(
                "CAPACITY_EXTERNAL_BYTES_EXCEEDED "
                f"namespace={self.namespace} projected={projected} limit={self.max_external_bytes}"
            )

    def _record_written(self, byte_count: int) -> None:
        current = self.total_bytes()
        self._size_cache = current + int(byte_count)

    def commit_bytes(
        self,
        *,
        unit_id: str,
        raw_output: bytes,
        logical_output_sha256: str,
        context: Mapping[str, Any],
        manifest_schema: str = "ovc-external-artifact-manifest/v1",
    ) -> ArtifactReceipt:
        unit = str(unit_id).strip()
        _unit_name(unit)
        raw = bytes(raw_output)
        raw_sha = sha256(raw).hexdigest()
        chunks: list[dict[str, Any]] = []
        pending: list[tuple[Path, bytes]] = []
        for index, offset in enumerate(range(0, len(raw), self.chunk_bytes)):
            raw_chunk = raw[offset : offset + self.chunk_bytes]
            raw_chunk_sha = sha256(raw_chunk).hexdigest()
            compressed = gzip.compress(raw_chunk, compresslevel=self.compression_level, mtime=0)
            compressed_sha = sha256(compressed).hexdigest()
            path = self._cas_path(raw_chunk_sha)
            if path.exists():
                existing = path.read_bytes()
                if sha256(existing).hexdigest() != compressed_sha or gzip.decompress(existing) != raw_chunk:
                    raise EvidenceStoreError(f"ARTIFACT_CORRUPT CAS collision:{raw_chunk_sha}")
            else:
                pending.append((path, compressed))
            chunks.append(
                {
                    "index": index,
                    "raw_sha256": raw_chunk_sha,
                    "raw_bytes": len(raw_chunk),
                    "compressed_sha256": compressed_sha,
                    "compressed_bytes": len(compressed),
                }
            )
        manifest = {
            "schema": manifest_schema,
            "namespace": self.namespace,
            "unit_id": unit,
            "logical_output_sha256": str(logical_output_sha256),
            "raw_output_sha256": raw_sha,
            "raw_output_bytes": len(raw),
            "context": dict(context),
            "storage": {
                "layout": "CONTENT_ADDRESSED_CHUNKED_COMPRESSED",
                "compression": "gzip",
                "compression_level": self.compression_level,
                "gzip_mtime": 0,
                "chunk_bytes": self.chunk_bytes,
                "chunks": chunks,
            },
        }
        manifest_bytes = canonical_json_bytes(manifest) + b"\n"
        manifest_sha = sha256(manifest_bytes).hexdigest()
        manifest_path = self._manifest_path(unit)
        if manifest_path.exists():
            if manifest_path.read_bytes() != manifest_bytes:
                raise EvidenceStoreError(f"ARTIFACT_HISTORY_REWRITE:{unit}")
        else:
            self._reserve(sum(len(data) for _, data in pending) + len(manifest_bytes))
            for path, data in pending:
                _atomic_write(path, data)
                self._record_written(len(data))
            _atomic_write(manifest_path, manifest_bytes)
            self._record_written(len(manifest_bytes))
        receipt = ArtifactReceipt(
            namespace=self.namespace,
            unit_id=unit,
            manifest_sha256=manifest_sha,
            logical_output_sha256=str(logical_output_sha256),
            raw_output_sha256=raw_sha,
            raw_output_bytes=len(raw),
        )
        self.verify_receipt(receipt, expected_context=context)
        return receipt

    def _load_manifest(self, unit_id: str) -> tuple[dict[str, Any], bytes]:
        path = self._manifest_path(unit_id)
        if not path.exists():
            raise EvidenceStoreError(f"ARTIFACT_MISSING:{unit_id}")
        raw_manifest = path.read_bytes()
        try:
            manifest = json.loads(raw_manifest)
        except Exception as exc:
            raise EvidenceStoreError(f"ARTIFACT_CORRUPT:{unit_id}:{exc}") from exc
        if manifest.get("namespace") != self.namespace or manifest.get("unit_id") != unit_id:
            raise EvidenceStoreError(f"ARTIFACT_BINDING_MISMATCH:{unit_id}")
        return manifest, raw_manifest

    def load_bytes(
        self,
        unit_id: str,
        *,
        expected_context: Mapping[str, Any] | None = None,
    ) -> bytes:
        manifest, _ = self._load_manifest(unit_id)
        if expected_context is not None and manifest.get("context") != dict(expected_context):
            raise EvidenceStoreError(f"ARTIFACT_CONTEXT_MISMATCH:{unit_id}")
        parts: list[bytes] = []
        for chunk in manifest["storage"]["chunks"]:
            path = self._cas_path(str(chunk["raw_sha256"]))
            if not path.exists():
                raise EvidenceStoreError(f"ARTIFACT_MISSING:{chunk['raw_sha256']}")
            compressed = path.read_bytes()
            if sha256(compressed).hexdigest() != str(chunk["compressed_sha256"]):
                raise EvidenceStoreError(f"ARTIFACT_CORRUPT:compressed:{unit_id}")
            raw = gzip.decompress(compressed)
            if len(raw) != int(chunk["raw_bytes"]) or sha256(raw).hexdigest() != str(chunk["raw_sha256"]):
                raise EvidenceStoreError(f"ARTIFACT_CORRUPT:raw:{unit_id}")
            parts.append(raw)
        output = b"".join(parts)
        if len(output) != int(manifest["raw_output_bytes"]):
            raise EvidenceStoreError(f"ARTIFACT_CORRUPT:length:{unit_id}")
        if sha256(output).hexdigest() != str(manifest["raw_output_sha256"]):
            raise EvidenceStoreError(f"ARTIFACT_CORRUPT:whole:{unit_id}")
        return output

    def verify_receipt(
        self,
        receipt: ArtifactReceipt,
        *,
        expected_context: Mapping[str, Any] | None = None,
    ) -> None:
        if receipt.namespace != self.namespace:
            raise EvidenceStoreError(f"ARTIFACT_BINDING_MISMATCH:{receipt.unit_id}")
        manifest, raw_manifest = self._load_manifest(receipt.unit_id)
        if sha256(raw_manifest).hexdigest() != receipt.manifest_sha256:
            raise EvidenceStoreError(f"ARTIFACT_CORRUPT:manifest:{receipt.unit_id}")
        output = self.load_bytes(receipt.unit_id, expected_context=expected_context)
        if sha256(output).hexdigest() != receipt.raw_output_sha256:
            raise EvidenceStoreError(f"ARTIFACT_CORRUPT:receipt:{receipt.unit_id}")
        if manifest.get("logical_output_sha256") != receipt.logical_output_sha256:
            raise EvidenceStoreError(f"ARTIFACT_CORRUPT:logical:{receipt.unit_id}")
