from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Any, Callable, Iterable, Mapping

from ovc_evidence_store.content_addressed import ArtifactReceipt
from ovc_evidence_store.streaming import StreamingContentAddressedArtifactStore

from .serialization import logical_sha256
from .wp10_durable_execution import DurableExecutionError, RunCapacityStore
from .wp10_execution_resilience import RunBinding, RunCheckpointStore, RunStartReceipt, WorkUnitReceipt
from .wp10_v10_storage import ContentAddressedArtifactStoreV10
from .wp10_v11_hardening import validate_work_unit_output
from .wp10_v11_streaming_analysis import FileBackedDomainAnalysis


class ContentAddressedArtifactStoreV11(ContentAddressedArtifactStoreV10):
    MANIFEST_SCHEMA = "ovc-srfdi-wp10-v11-artifact-manifest/v1-file-backed"

    def _store(self, run_id: str) -> StreamingContentAddressedArtifactStore:
        rid=str(run_id).strip()
        if rid not in self._stores:
            self._stores[rid]=StreamingContentAddressedArtifactStore(
                self.root,
                namespace=f"srfd/wp10-v1-1/{rid}",
                max_external_bytes=self.max_external_bytes,
                chunk_bytes=16*1024*1024,
                compression_level=6,
            )
        return self._stores[rid]  # type: ignore[return-value]

    @staticmethod
    def _context(start: RunStartReceipt, binding: Any) -> dict[str,str]:
        return {
            "programme_id":"OVC-SRFD-BENCHMARK-v0.1",
            "packet_id":"SRFDI-WP10-v1.1",
            "run_id":start.run_id,
            "token_id":start.token_id,
            "run_binding_sha256":binding.logical_hash,
        }

    def commit_file_output(self,start:RunStartReceipt,binding:Any,unit_id:str,output:FileBackedDomainAnalysis)->WorkUnitReceipt:
        if start.run_binding_sha256 != binding.logical_hash:
            raise DurableExecutionError("RESUME_BINDING_MISMATCH","artifact run start and binding differ")
        expected_domain=str(unit_id).split('/')[1] if str(unit_id).startswith('domain/') else None
        if not str(unit_id).endswith('/analysis') or expected_domain != output.domain_id or output.configuration_count != 54:
            raise DurableExecutionError("WORK_UNIT_INVALID_OUTPUT",f"file-backed output binding mismatch:{unit_id}")
        try:
            receipt=self._store(start.run_id).commit_file(
                unit_id=str(unit_id),raw_output_path=output.path,logical_output_sha256=output.logical_hash,
                context=self._context(start,binding),manifest_schema=self.MANIFEST_SCHEMA,
            )
        except Exception as exc:
            from ovc_evidence_store import EvidenceStoreError
            if isinstance(exc,EvidenceStoreError):
                raise self._translate_error(exc) from exc
            raise
        if receipt.raw_output_sha256 != output.raw_sha256 or receipt.raw_output_bytes != output.raw_bytes:
            raise DurableExecutionError("ARTIFACT_CORRUPT",f"file receipt mismatch:{unit_id}")
        result=WorkUnitReceipt(unit_id=str(unit_id),output_logical_hash=output.logical_hash,artifact_sha256=receipt.manifest_sha256)
        self.verify_receipt(start,binding,result)
        return result

    def verify_receipt(self,start:RunStartReceipt,binding:Any,receipt:WorkUnitReceipt)->None:
        if receipt.artifact_sha256 is None:
            raise DurableExecutionError("CHECKPOINT_ARTIFACT_HASH_MISSING",receipt.unit_id)
        store=self._store(start.run_id)
        path=store.namespace_root/'manifests'/(sha256(receipt.unit_id.encode('utf-8')).hexdigest()+'.json')
        if not path.exists():
            raise DurableExecutionError("ARTIFACT_MISSING",receipt.unit_id)
        raw_manifest=path.read_bytes()
        if sha256(raw_manifest).hexdigest()!=receipt.artifact_sha256:
            raise DurableExecutionError("ARTIFACT_CORRUPT",f"manifest:{receipt.unit_id}")
        try:
            manifest=json.loads(raw_manifest)
            artifact=ArtifactReceipt(
                namespace=store.namespace,unit_id=receipt.unit_id,manifest_sha256=receipt.artifact_sha256,
                logical_output_sha256=receipt.output_logical_hash,raw_output_sha256=str(manifest['raw_output_sha256']),
                raw_output_bytes=int(manifest['raw_output_bytes']),
            )
            store.verify_receipt_streaming(artifact,expected_context=self._context(start,binding))
        except DurableExecutionError:
            raise
        except Exception as exc:
            raise DurableExecutionError("ARTIFACT_CORRUPT",f"{receipt.unit_id}:{exc}") from exc


def execute_durable_resumable_units_v11(
    *,start:RunStartReceipt,binding:RunBinding,checkpoint_store:RunCheckpointStore,
    artifact_store:ContentAddressedArtifactStoreV11,unit_ids:Iterable[str],
    worker:Callable[[str],Mapping[str,Any]|FileBackedDomainAnalysis],capacity_store:RunCapacityStore|None=None,
    stop_after_new_units:int|None=None,
)->dict[str,Any]:
    ordered=tuple(str(value) for value in unit_ids)
    if len(ordered)!=len(set(ordered)):
        raise DurableExecutionError("WORK_UNIT_DUPLICATE","work unit IDs must be unique")
    checkpoint=checkpoint_store.latest(start,binding,allow_missing=True)
    committed=[] if checkpoint is None else list(checkpoint.unit_receipts)
    for receipt in committed:
        artifact_store.verify_receipt(start,binding,receipt)
    completed={item.unit_id for item in committed}; new_count=0
    for unit_id in ordered:
        if unit_id in completed: continue
        started=time.perf_counter(); output=worker(unit_id); active_seconds=time.perf_counter()-started
        if isinstance(output,FileBackedDomainAnalysis):
            if not unit_id.endswith('/analysis'):
                raise DurableExecutionError("WORK_UNIT_INVALID_OUTPUT",f"file-backed output only valid for domain analysis:{unit_id}")
        elif isinstance(output,Mapping):
            validate_work_unit_output(unit_id,output)
        else:
            raise DurableExecutionError("WORK_UNIT_INVALID_OUTPUT",f"unsupported output type:{unit_id}")
        if capacity_store is not None:
            capacity_store.account_unit(start,binding,active_wall_seconds=active_seconds)
        if isinstance(output,FileBackedDomainAnalysis):
            receipt=artifact_store.commit_file_output(start,binding,unit_id,output)
            output.path.unlink(missing_ok=True)
        else:
            receipt=artifact_store.commit_output(start,binding,unit_id,output)
        committed.append(receipt); checkpoint=checkpoint_store.commit(start,binding,committed); completed.add(unit_id); new_count+=1
        if stop_after_new_units is not None and new_count>=stop_after_new_units: break
    complete=len(completed)==len(ordered)
    payload={
        "run_id":start.run_id,"run_binding_sha256":binding.logical_hash,"ordered_unit_count":len(ordered),
        "completed_unit_count":len(completed),"completed_units":[item.unit_id for item in committed],
        "unit_output_hashes":{item.unit_id:item.output_logical_hash for item in committed},
        "unit_artifact_sha256":{item.unit_id:item.artifact_sha256 for item in committed},
        "last_checkpoint_id":checkpoint.checkpoint_id if checkpoint else None,"complete":complete,
        "authority_effect":"NONE_EXECUTION_ROUTE_ONLY",
    }
    return {**payload,"result_logical_hash":logical_sha256(payload)}
