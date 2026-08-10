from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from ovc_evidence_store import ContentAddressedArtifactStore, EvidenceStoreError

from .serialization import canonical_json_bytes, logical_sha256
from .wp10_execution_resilience import RunStartReceipt, WorkUnitReceipt
from .wp10_durable_execution import DurableExecutionError


@dataclass(frozen=True)
class ReuseSource:
    run_id: str
    token_id: str
    run_binding_sha256: str
    checkpoint_id: str
    checkpoint_sequence: int


class ContentAddressedArtifactStoreV10:
    """SRFD execution adapter over shared OVC artifact infrastructure.

    SRFD owns run identity, logical-output verification, v0.9 reuse eligibility,
    the T1 numeric envelope and run authority.  The shared evidence store owns
    only deterministic physical materialisation, content addressing,
    compression, capacity enforcement and read-back verification.
    """

    MANIFEST_SCHEMA = "ovc-srfdi-wp10-v10-artifact-manifest/v2-shared-infrastructure"

    def __init__(self, root: Path, *, max_external_bytes: int) -> None:
        self.root = Path(root)
        self.max_external_bytes = int(max_external_bytes)
        self._stores: dict[str, ContentAddressedArtifactStore] = {}

    def _store(self, run_id: str) -> ContentAddressedArtifactStore:
        rid = str(run_id).strip()
        if rid not in self._stores:
            self._stores[rid] = ContentAddressedArtifactStore(
                self.root,
                namespace=f"srfd/wp10-v1/{rid}",
                max_external_bytes=self.max_external_bytes,
                chunk_bytes=16 * 1024 * 1024,
                compression_level=6,
            )
        return self._stores[rid]

    @staticmethod
    def _context(start: RunStartReceipt, binding: Any) -> dict[str, str]:
        return {
            "programme_id": "OVC-SRFD-BENCHMARK-v0.1",
            "packet_id": "SRFDI-WP10-v1.0",
            "run_id": start.run_id,
            "token_id": start.token_id,
            "run_binding_sha256": binding.logical_hash,
        }

    @staticmethod
    def _translate_error(exc: EvidenceStoreError) -> DurableExecutionError:
        text = str(exc)
        reason = text.split(" ", 1)[0].split(":", 1)[0]
        return DurableExecutionError(reason, text)

    def total_bytes(self, run_id: str) -> int:
        return self._store(run_id).total_bytes()

    def commit_output(
        self,
        start: RunStartReceipt,
        binding: Any,
        unit_id: str,
        output: Mapping[str, Any],
    ) -> WorkUnitReceipt:
        if start.run_binding_sha256 != binding.logical_hash:
            raise DurableExecutionError("RESUME_BINDING_MISMATCH", "artifact run start and binding differ")
        logical = logical_sha256(output)
        raw = canonical_json_bytes(output)
        try:
            receipt = self._store(start.run_id).commit_bytes(
                unit_id=str(unit_id),
                raw_output=raw,
                logical_output_sha256=logical,
                context=self._context(start, binding),
                manifest_schema=self.MANIFEST_SCHEMA,
            )
        except EvidenceStoreError as exc:
            raise self._translate_error(exc) from exc
        result = WorkUnitReceipt(
            unit_id=str(unit_id),
            output_logical_hash=logical,
            artifact_sha256=receipt.manifest_sha256,
        )
        self.verify_receipt(start, binding, result)
        return result

    def load_output(self, start: RunStartReceipt, binding: Any, unit_id: str) -> dict[str, Any]:
        try:
            raw = self._store(start.run_id).load_bytes(
                str(unit_id), expected_context=self._context(start, binding)
            )
        except EvidenceStoreError as exc:
            raise self._translate_error(exc) from exc
        try:
            value = json.loads(raw)
        except Exception as exc:
            raise DurableExecutionError("ARTIFACT_CORRUPT", str(exc)) from exc
        if not isinstance(value, Mapping):
            raise DurableExecutionError("ARTIFACT_CORRUPT", f"mapping required:{unit_id}")
        return dict(value)

    def verify_receipt(self, start: RunStartReceipt, binding: Any, receipt: WorkUnitReceipt) -> None:
        if receipt.artifact_sha256 is None:
            raise DurableExecutionError("CHECKPOINT_ARTIFACT_HASH_MISSING", receipt.unit_id)
        store = self._store(start.run_id)
        path = store.namespace_root / "manifests" / (sha256(receipt.unit_id.encode("utf-8")).hexdigest() + ".json")
        if not path.exists() or sha256(path.read_bytes()).hexdigest() != receipt.artifact_sha256:
            raise DurableExecutionError("ARTIFACT_CORRUPT", f"manifest:{receipt.unit_id}")
        output = self.load_output(start, binding, receipt.unit_id)
        if logical_sha256(output) != receipt.output_logical_hash:
            raise DurableExecutionError("ARTIFACT_CORRUPT", f"logical:{receipt.unit_id}")

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
        """Admit one historical v0.9 output only after SRFD-specific exact verification.

        The historical checkpoint is never copied or relabelled.  Only the
        individually verified scientific output is rematerialised under the new
        shared physical store and becomes a dependency of a new v1.0 checkpoint.
        """
        old_name = sha256(str(source_receipt.unit_id).encode("utf-8")).hexdigest() + ".json"
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
