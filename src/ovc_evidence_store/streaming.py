from __future__ import annotations

import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from typing import Any, Mapping

from .content_addressed import (
    ArtifactReceipt,
    ContentAddressedArtifactStore,
    _atomic_write,
    _unit_name,
    canonical_json_bytes,
)
from .manifest import EvidenceStoreError


class StreamingContentAddressedArtifactStore(ContentAddressedArtifactStore):
    """File-backed extension of the programme-neutral artifact store.

    The wire manifest, deterministic 16 MiB chunking, gzip parameters and CAS
    identities are identical to ``commit_bytes``. Only materialisation changes:
    the raw scientific output is read one chunk at a time so a large exact JSON
    artifact never has to exist as one Python ``bytes`` object.
    """

    def commit_file(
        self,
        *,
        unit_id: str,
        raw_output_path: Path,
        logical_output_sha256: str,
        context: Mapping[str, Any],
        manifest_schema: str = "ovc-external-artifact-manifest/v1",
    ) -> ArtifactReceipt:
        unit = str(unit_id).strip()
        _unit_name(unit)
        source = Path(raw_output_path)
        if not source.is_file():
            raise EvidenceStoreError(f"ARTIFACT_SOURCE_MISSING:{unit}")

        stage_root = self.namespace_root / ".staging" / sha256(unit.encode("utf-8")).hexdigest()
        if stage_root.exists():
            shutil.rmtree(stage_root)
        stage_root.mkdir(parents=True, exist_ok=True)

        whole = sha256()
        raw_bytes = 0
        chunks: list[dict[str, Any]] = []
        pending: list[tuple[Path, Path, int]] = []
        try:
            with source.open("rb") as handle:
                index = 0
                while True:
                    raw_chunk = handle.read(self.chunk_bytes)
                    if not raw_chunk:
                        break
                    raw_bytes += len(raw_chunk)
                    whole.update(raw_chunk)
                    raw_chunk_sha = sha256(raw_chunk).hexdigest()
                    compressed = gzip.compress(raw_chunk, compresslevel=self.compression_level, mtime=0)
                    compressed_sha = sha256(compressed).hexdigest()
                    final_path = self._cas_path(raw_chunk_sha)
                    if final_path.exists():
                        existing = final_path.read_bytes()
                        if sha256(existing).hexdigest() != compressed_sha or gzip.decompress(existing) != raw_chunk:
                            raise EvidenceStoreError(f"ARTIFACT_CORRUPT CAS collision:{raw_chunk_sha}")
                    else:
                        staged = stage_root / f"{index:08d}.gz"
                        _atomic_write(staged, compressed)
                        pending.append((final_path, staged, len(compressed)))
                    chunks.append(
                        {
                            "index": index,
                            "raw_sha256": raw_chunk_sha,
                            "raw_bytes": len(raw_chunk),
                            "compressed_sha256": compressed_sha,
                            "compressed_bytes": len(compressed),
                        }
                    )
                    index += 1

            raw_sha = whole.hexdigest()
            manifest = {
                "schema": manifest_schema,
                "namespace": self.namespace,
                "unit_id": unit,
                "logical_output_sha256": str(logical_output_sha256),
                "raw_output_sha256": raw_sha,
                "raw_output_bytes": raw_bytes,
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
                self._reserve(sum(size for _, _, size in pending) + len(manifest_bytes))
                for final_path, staged, size in pending:
                    final_path.parent.mkdir(parents=True, exist_ok=True)
                    if final_path.exists():
                        staged.unlink(missing_ok=True)
                    else:
                        os.replace(staged, final_path)
                        self._record_written(size)
                _atomic_write(manifest_path, manifest_bytes)
                self._record_written(len(manifest_bytes))

            receipt = ArtifactReceipt(
                namespace=self.namespace,
                unit_id=unit,
                manifest_sha256=manifest_sha,
                logical_output_sha256=str(logical_output_sha256),
                raw_output_sha256=raw_sha,
                raw_output_bytes=raw_bytes,
            )
            self.verify_receipt_streaming(receipt, expected_context=context)
            return receipt
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root)

    def verify_receipt_streaming(
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
        if expected_context is not None and manifest.get("context") != dict(expected_context):
            raise EvidenceStoreError(f"ARTIFACT_CONTEXT_MISMATCH:{receipt.unit_id}")
        if manifest.get("logical_output_sha256") != receipt.logical_output_sha256:
            raise EvidenceStoreError(f"ARTIFACT_CORRUPT:logical:{receipt.unit_id}")

        whole = sha256()
        total = 0
        for chunk in manifest["storage"]["chunks"]:
            path = self._cas_path(str(chunk["raw_sha256"]))
            if not path.exists():
                raise EvidenceStoreError(f"ARTIFACT_MISSING:{chunk['raw_sha256']}")
            compressed = path.read_bytes()
            if sha256(compressed).hexdigest() != str(chunk["compressed_sha256"]):
                raise EvidenceStoreError(f"ARTIFACT_CORRUPT:compressed:{receipt.unit_id}")
            raw = gzip.decompress(compressed)
            if len(raw) != int(chunk["raw_bytes"]) or sha256(raw).hexdigest() != str(chunk["raw_sha256"]):
                raise EvidenceStoreError(f"ARTIFACT_CORRUPT:raw:{receipt.unit_id}")
            whole.update(raw)
            total += len(raw)
        if total != int(manifest["raw_output_bytes"]) or total != receipt.raw_output_bytes:
            raise EvidenceStoreError(f"ARTIFACT_CORRUPT:length:{receipt.unit_id}")
        if whole.hexdigest() != str(manifest["raw_output_sha256"]) or whole.hexdigest() != receipt.raw_output_sha256:
            raise EvidenceStoreError(f"ARTIFACT_CORRUPT:whole:{receipt.unit_id}")
