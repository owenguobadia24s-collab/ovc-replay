from __future__ import annotations

from dataclasses import dataclass
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .serialization import canonical_json_bytes, logical_sha256
from .wp10_execution_resilience import RunStartReceipt, WorkUnitReceipt
from .wp10_durable_execution import DurableExecutionError

CHUNK_BYTES = 16 * 1024 * 1024
COMPRESSION = "gzip"
COMPRESSION_LEVEL = 6


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _unit_name(unit_id: str) -> str:
    return sha256(str(unit_id).encode("utf-8")).hexdigest() + ".json"


def _gzip(raw: bytes) -> bytes:
    return gzip.compress(raw, compresslevel=COMPRESSION_LEVEL, mtime=0)


@dataclass(frozen=True)
class ReuseSource:
    run_id: str
    token_id: str
    run_binding_sha256: str
    checkpoint_id: str
    checkpoint_sequence: int


class ContentAddressedArtifactStoreV10:
    """Deterministic chunked/compressed external store for WP10 v1.0.

    The scientific output mapping is unchanged. Only physical materialisation changes:
    canonical output bytes are split deterministically, gzip-compressed with mtime=0,
    and stored content-addressed outside Git. A compact run/unit manifest binds the
    logical output, raw bytes and physical chunks. The checkpoint receipt hashes this
    manifest, not an uncompressed multi-hundred-MB JSON envelope.
    """

    def __init__(self, root: Path, *, max_external_bytes: int) -> None:
        self.root = Path(root)
        self.max_external_bytes = int(max_external_bytes)
        self._size_cache: dict[str, int] = {}

    def _run_root(self, run_id: str) -> Path:
        return self.root / "runs" / run_id / "artifacts_v10"

    def _manifest_path(self, run_id: str, unit_id: str) -> Path:
        return self._run_root(run_id) / "manifests" / _unit_name(unit_id)

    def _cas_path(self, run_id: str, raw_sha: str) -> Path:
        return self._run_root(run_id) / "cas" / "sha256" / raw_sha[:2] / f"{raw_sha}.gz"

    def total_bytes(self, run_id: str) -> int:
        if run_id not in self._size_cache:
            base = self._run_root(run_id)
            total = 0
            if base.exists():
                total = sum(p.stat().st_size for p in base.rglob("*") if p.is_file())
            self._size_cache[run_id] = total
        return self._size_cache[run_id]

    def _reserve(self, run_id: str, added: int) -> None:
        projected = self.total_bytes(run_id) + int(added)
        if projected > self.max_external_bytes:
            raise DurableExecutionError(
                "CAPACITY_EXTERNAL_BYTES_EXCEEDED",
                f"tier=T1_EXTERNAL_ARTIFACT projected={projected} limit={self.max_external_bytes}",
            )

    def commit_output(
        self,
        start: RunStartReceipt,
        binding: Any,
        unit_id: str,
        output: Mapping[str, Any],
    ) -> WorkUnitReceipt:
        if start.run_binding_sha256 != binding.logical_hash:
            raise DurableExecutionError("RESUME_BINDING_MISMATCH", "artifact run start and binding differ")
        unit = str(unit_id).strip()
        if not unit:
            raise DurableExecutionError("WORK_UNIT_INVALID_OUTPUT", "unit_id required")
        raw = canonical_json_bytes(output)
        output_logical_hash = logical_sha256(output)
        raw_sha = sha256(raw).hexdigest()
        chunks: list[dict[str, Any]] = []
        new_chunks: list[tuple[Path, bytes]] = []
        for index, offset in enumerate(range(0, len(raw), CHUNK_BYTES)):
            raw_chunk = raw[offset : offset + CHUNK_BYTES]
            raw_chunk_sha = sha256(raw_chunk).hexdigest()
            compressed = _gzip(raw_chunk)
            compressed_sha = sha256(compressed).hexdigest()
            path = self._cas_path(start.run_id, raw_chunk_sha)
            if path.exists():
                existing = path.read_bytes()
                if sha256(existing).hexdigest() != compressed_sha or gzip.decompress(existing) != raw_chunk:
                    raise DurableExecutionError("ARTIFACT_CORRUPT", f"CAS collision/corruption:{raw_chunk_sha}")
            else:
                new_chunks.append((path, compressed))
            chunks.append({
                "index": index,
                "raw_sha256": raw_chunk_sha,
                "raw_bytes": len(raw_chunk),
                "compressed_sha256": compressed_sha,
                "compressed_bytes": len(compressed),
            })
        manifest = {
            "schema": "ovc-srfdi-wp10-v10-artifact-manifest/v1",
            "run_id": start.run_id,
            "token_id": start.token_id,
            "run_binding_sha256": binding.logical_hash,
            "unit_id": unit,
            "output_logical_hash": output_logical_hash,
            "raw_output_sha256": raw_sha,
            "raw_output_bytes": len(raw),
            "storage": {
                "layout": "CONTENT_ADDRESSED_CHUNKED_COMPRESSED",
                "compression": COMPRESSION,
                "compression_level": COMPRESSION_LEVEL,
                "gzip_mtime": 0,
                "chunk_bytes": CHUNK_BYTES,
                "chunks": chunks,
            },
        }
        manifest_bytes = canonical_json_bytes(manifest) + b"\n"
        manifest_sha = sha256(manifest_bytes).hexdigest()
        mpath = self._manifest_path(start.run_id, unit)
        if mpath.exists():
            if mpath.read_bytes() != manifest_bytes:
                raise DurableExecutionError("ARTIFACT_HISTORY_REWRITE", unit)
        else:
            self._reserve(start.run_id, sum(len(data) for _, data in new_chunks) + len(manifest_bytes))
            for path, data in new_chunks:
                _atomic_write(path, data)
                self._size_cache[start.run_id] = self.total_bytes(start.run_id) + len(data)
            _atomic_write(mpath, manifest_bytes)
            self._size_cache[start.run_id] = self.total_bytes(start.run_id) + len(manifest_bytes)
        receipt = WorkUnitReceipt(unit_id=unit, output_logical_hash=output_logical_hash, artifact_sha256=manifest_sha)
        self.verify_receipt(start, binding, receipt)
        return receipt

    def _load_manifest(self, start: RunStartReceipt, binding: Any, unit_id: str) -> tuple[dict[str, Any], bytes]:
        path = self._manifest_path(start.run_id, unit_id)
        if not path.exists():
            raise DurableExecutionError("ARTIFACT_MISSING", unit_id)
        raw_manifest = path.read_bytes()
        try:
            manifest = json.loads(raw_manifest)
        except Exception as exc:
            raise DurableExecutionError("ARTIFACT_CORRUPT", str(exc)) from exc
        if (
            manifest.get("schema") != "ovc-srfdi-wp10-v10-artifact-manifest/v1"
            or manifest.get("run_id") != start.run_id
            or manifest.get("token_id") != start.token_id
            or manifest.get("run_binding_sha256") != binding.logical_hash
            or manifest.get("unit_id") != unit_id
        ):
            raise DurableExecutionError("ARTIFACT_BINDING_MISMATCH", unit_id)
        return manifest, raw_manifest

    def load_output(self, start: RunStartReceipt, binding: Any, unit_id: str) -> dict[str, Any]:
        manifest, _ = self._load_manifest(start, binding, unit_id)
        parts: list[bytes] = []
        for chunk in manifest["storage"]["chunks"]:
            path = self._cas_path(start.run_id, str(chunk["raw_sha256"]))
            if not path.exists():
                raise DurableExecutionError("ARTIFACT_MISSING", str(chunk["raw_sha256"]))
            compressed = path.read_bytes()
            if sha256(compressed).hexdigest() != str(chunk["compressed_sha256"]):
                raise DurableExecutionError("ARTIFACT_CORRRUPT", f"compressed:{unit_id}")
            raw = gzip.decompress(compressed)
            if len(raw) != int(chunk["raw_bytes"]) or sha256(raw).hexdigest() != str(chunk["raw_sha256"]):
                raise DurableExecutionError("ARTIFACT_CORRRUPT", f"raw:{unit_id}")
            parts.append(raw)
        raw_output = b"".join(parts)
        if len(raw_output) != int(manifest["raw_output_bytes"]) or sha256(raw_output).hexdigest() != str(manifest["raw_output_sha256"]):
            raise DurableExecutionError("ARTIFACT_CORRUPT", f"whole:{unit_id}")
        try:
            output = json.loads(raw_output)
        except Exception as exc:
            raise DurableExecutionError("ARTIFAACT_CORRUPT", str(exc)) from exc
        if not isinstance(output, Mapping) or logical_sha256(output) != str(manifest["output_logical_hash"]):
            raise DurableExecutionError("ARTIFACT_CORRUPT", f"logical:{unit_id}")
        return dict(output)

    def verify_receipt(self, start: RunStartReceipt, binding: Any, receipt: WorkUnitReceipt) -> None:
        if receipt.artifact_sha256 is None:
            raise DurableExecutionError("CHECKPOINT_ARTIFACT_HASH_MISSING", receipt.unit_id)
        manifest, raw_manifest = self._load_manifest(start, binding, receipt.unit_id)
        if sha256(raw_manifest).hexdigest() != receipt.artifact_sha256:
            raise DurableExecutionError("ARTIFACT_CORRUPT", f"manifest:{receipt.unit_id}")
        output = self.load_output(start, binding, receipt.unit_id)
        if logical_sha256(output) != receipt.output_logical_hash or manifest["output_logical_hash"] != receipt.output_logical_hash:
            raise DurableExecutionError("ARTIFACT_CORRUPT", f"receipt:{receipt.unit_id}")

    def import_v09_output(
        self,
        *,
        start: RunStartReceipt,
        binding: Any,
        v09_root: Path,
        source: ReuseSource,
        source_receipt: WorkUnitReceipt,
        expected_v09_binding_sha256: str,
    ) -> WorkUnitReceipt:
        """Verify one committed v0.9 artifact and re-materialise its unchanged output under v1.0.

        The old checkpoint is never copied or relabelled. Only an individually verified output
        is admitted as a reusable dependency/cache value in the new run.
        """
        old_name = _unit_name(source_receipt.unit_id)
        old_path = Path(v09_root) / "runs" / source.run_id / "artifacts" / old_name
        if not old_path.exists():
            raise DurableExecutionError("REUSE_SOURCE_ARTIFACT_MISSING", source_receipt.unit_id)
        old_raw = old_path.read_bytes()
        if source_receipt.artifact_sha256 is None or sha256(old_raw).hexdigest() != source_receipt.artifact_sha256:
            raise DurableExecutionError("REUSE_SOURCE_HASH_MISMATCH", source_receipt.unit_id)
        try:
            envelope = json.loads(old_raw)
        except Exception as exc:
            raise DurableExecutionError("REUSE_SOURCE_CORRUPT", str(exc)) from exc
        if (
            envelope.get("schema") != "ovc-srfd-run-work-unit-artifact/v1"
            or envelope.get("run_id") != source.run_id
            or envelope.get("token_id") != source.token_id
            or envelope.get("run_binding_sha256") != expected_v09_binding_sha256
            or envelope.get("unit_id") != source_receipt.unit_id
        ):
            raise DurableExecutionError("REUSE_SOURCE_BINDING_MISMATCH", source_receipt.unit_id)
        output = envelope.get("output")
        if not isinstance(output, Mapping):
            raise DurableExecutionError("REUSE_SOURCE_CORRUPT", source_receipt.unit_id)
        actual_logical = logical_sha256(output)
        if actual_logical != source_receipt.output_logical_hash or envelope.get("output_logical_hash") != actual_logical:
            raise DurableExecutionError("REUSE_SOURCE_LOGICAL_HASH_MISMATCH", source_receipt.unit_id)
        return self.commit_output(start, binding, source_receipt.unit_id, output)
