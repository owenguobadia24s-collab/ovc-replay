"""Inactive deterministic execution/replay reference kernel for SHSI-WP3."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Mapping, Sequence


class SharedExecutionError(ValueError):
    """Fail-closed execution-envelope error."""


def _hash(value: Any) -> str:
    try:
        raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    except (TypeError,ValueError) as exc: raise SharedExecutionError("NON_CANONICAL_EXECUTION_VALUE") from exc
    return hashlib.sha256(raw).hexdigest()


def _exact(value: str, field: str) -> str:
    if not isinstance(value,str) or not value or "latest" in value.lower(): raise SharedExecutionError(f"{field.upper()}_EXACT_REF_REQUIRED")
    return value


@dataclass(frozen=True)
class SemanticGenerationRef:
    owner_namespace: str; generation_id: str; contract_refs: tuple[str,...]
    def __post_init__(self):
        _exact(self.owner_namespace,"owner_namespace"); _exact(self.generation_id,"generation_id")
        if not self.contract_refs: raise SharedExecutionError("SEMANTIC_CONTRACT_REFS_REQUIRED")
        for ref in self.contract_refs: _exact(ref,"contract_ref")
    @property
    def logical_id(self)->str: return _hash({"owner":self.owner_namespace,"generation":self.generation_id,"contracts":self.contract_refs})


@dataclass(frozen=True)
class RunSpecification:
    semantic_generation_ref: str; population_ids: tuple[str,...]; scope_ref: str
    evaluation_cutoff: str; parameters: Mapping[str,Any]; output_contract_ref: str
    logical_barriers: tuple[str,...]
    def __post_init__(self):
        for v,n in ((self.semantic_generation_ref,"semantic_generation_ref"),(self.scope_ref,"scope_ref"),(self.output_contract_ref,"output_contract_ref")): _exact(v,n)
        if not self.population_ids or len(set(self.population_ids))!=len(self.population_ids): raise SharedExecutionError("POPULATION_INVALID")
        if tuple(sorted(self.population_ids))!=self.population_ids: raise SharedExecutionError("POPULATION_CANONICAL_ORDER_REQUIRED")
        if any(not b.startswith("SOURCE:") for b in self.logical_barriers): raise SharedExecutionError("WALL_CLOCK_BARRIER_FORBIDDEN")
    @property
    def logical_id(self)->str:
        return _hash({"semantic":self.semantic_generation_ref,"population":self.population_ids,"scope":self.scope_ref,"cutoff":self.evaluation_cutoff,"parameters":self.parameters,"output":self.output_contract_ref,"barriers":self.logical_barriers})


@dataclass(frozen=True)
class ExecutionEnvironmentManifest:
    environment_id: str; os: str; architecture: str; runtime: str; toolchain_lock_ref: str; reproducibility_class: str
    def __post_init__(self):
        for value,name in ((self.environment_id,"environment_id"),(self.os,"os"),(self.architecture,"architecture"),(self.runtime,"runtime"),(self.toolchain_lock_ref,"toolchain_lock_ref"),(self.reproducibility_class,"reproducibility_class")): _exact(value,name)


@dataclass(frozen=True)
class RunExecutionManifest:
    run_specification_id: str; environment_id: str; attempt_id: str
    worker_count: int; chunk_size: int; backend: str; host_path: str
    def __post_init__(self):
        for value,name in ((self.run_specification_id,"run_specification_id"),(self.environment_id,"environment_id"),(self.attempt_id,"attempt_id"),(self.backend,"backend")): _exact(value,name)
        if self.worker_count<1 or self.chunk_size<1: raise SharedExecutionError("PHYSICAL_PARTITION_INVALID")


@dataclass(frozen=True)
class LogicalResultIdentity:
    run_specification_id: str; ordered_result_hashes: tuple[str,...]
    @property
    def logical_id(self)->str: return _hash({"run_specification_id":self.run_specification_id,"ordered_result_hashes":self.ordered_result_hashes})


@dataclass(frozen=True)
class CheckpointReceipt:
    run_specification_id: str; next_index: int; committed_results: tuple[tuple[str,Any],...]; prefix_hash: str
    def validate(self)->None:
        if self.next_index!=len(self.committed_results): raise SharedExecutionError("CHECKPOINT_INDEX_MISMATCH")
        if _hash(self.committed_results)!=self.prefix_hash: raise SharedExecutionError("CHECKPOINT_HASH_MISMATCH")


@dataclass(frozen=True)
class CapacityReceipt:
    run_specification_id: str; status: str; required_units: int; available_units: int
    population_preserved: bool=True; precision_preserved: bool=True; sampling_applied: bool=False
    def __post_init__(self):
        expected="READY" if self.required_units<=self.available_units else "CAPACITY_EXCEEDED"
        if self.status!=expected or not self.population_preserved or not self.precision_preserved or self.sampling_applied: raise SharedExecutionError("CAPACITY_SEMANTIC_DEGRADATION_FORBIDDEN")


@dataclass(frozen=True)
class ReplayResultManifest:
    run_specification_id: str; logical_result_identity: str|None; status: str
    ordered_results: tuple[tuple[str,Any],...]; checkpoint: CheckpointReceipt|None; capacity_receipt: CapacityReceipt
    authority_effect: str="NONE"


def deterministic_partitions(spec: RunSpecification, chunk_size: int) -> tuple[tuple[str, ...], ...]:
    if chunk_size < 1:
        raise SharedExecutionError("PHYSICAL_PARTITION_INVALID")
    return tuple(tuple(spec.population_ids[i:i + chunk_size]) for i in range(0, len(spec.population_ids), chunk_size))


def run_reference(spec:RunSpecification, manifest:RunExecutionManifest, records:Mapping[str,Any], transform:Callable[[Any],Any], *, checkpoint:CheckpointReceipt|None=None, available_units:int|None=None, stop_before:int|None=None, stop_after:int|None=None, physical_order:Sequence[str]|None=None)->ReplayResultManifest:
    if manifest.run_specification_id!=spec.logical_id: raise SharedExecutionError("RUN_SPECIFICATION_MISMATCH")
    if set(records)!=set(spec.population_ids): raise SharedExecutionError("SEMANTIC_POPULATION_MISMATCH")
    capacity=CapacityReceipt(spec.logical_id,"READY" if available_units is None or len(records)<=available_units else "CAPACITY_EXCEEDED",len(records),len(records) if available_units is None else available_units)
    if capacity.status=="CAPACITY_EXCEEDED": return ReplayResultManifest(spec.logical_id,None,"CAPACITY_EXCEEDED",(),None,capacity)
    committed:list[tuple[str,Any]]=[]
    if checkpoint:
        checkpoint.validate()
        if checkpoint.run_specification_id!=spec.logical_id: raise SharedExecutionError("CHECKPOINT_SPEC_MISMATCH")
        committed=list(checkpoint.committed_results)
    start=len(committed)
    order=tuple(physical_order or spec.population_ids[start:])
    if set(order)!=set(spec.population_ids[start:]) or len(order)!=len(spec.population_ids[start:]): raise SharedExecutionError("PHYSICAL_ORDER_POPULATION_MISMATCH")
    computed={record_id:transform(records[record_id]) for record_id in order}
    for index,record_id in enumerate(spec.population_ids[start:],start=start):
        if stop_before is not None and index==stop_before:
            cp=CheckpointReceipt(spec.logical_id,len(committed),tuple(committed),_hash(tuple(committed)))
            return ReplayResultManifest(spec.logical_id,None,"CHECKPOINTED_BEFORE_COMMIT",tuple(committed),cp,capacity)
        committed.append((record_id,computed[record_id]))
        if stop_after is not None and index==stop_after:
            cp=CheckpointReceipt(spec.logical_id,len(committed),tuple(committed),_hash(tuple(committed)))
            return ReplayResultManifest(spec.logical_id,None,"CHECKPOINTED_AFTER_COMMIT",tuple(committed),cp,capacity)
    hashes=tuple(_hash({"record_id":rid,"result":value}) for rid,value in committed)
    identity=LogicalResultIdentity(spec.logical_id,hashes)
    return ReplayResultManifest(spec.logical_id,identity.logical_id,"COMPLETE",tuple(committed),None,capacity)


def reconcile_exact(*manifests:ReplayResultManifest)->str:
    if not manifests or any(m.status!="COMPLETE" for m in manifests): raise SharedExecutionError("LOGICAL_RESULT_RECONCILIATION_FAILED")
    ids={m.logical_result_identity for m in manifests}
    if len(ids)!=1: raise SharedExecutionError("LOGICAL_RESULT_RECONCILIATION_FAILED")
    return next(iter(ids))
