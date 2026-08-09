from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import Any, Callable, Iterable, Mapping, Sequence

from .serialization import canonical_json_bytes, logical_sha256, stable_id


class ExecutionResilienceError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _hex64(value: str, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise ExecutionResilienceError("RESILIENCE_BINDING_INVALID", f"{field} must be lowercase sha256")
    return text


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    data = canonical_json_bytes(value) + b"\n"
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    try:
        directory_fd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


@dataclass(frozen=True)
class RunBinding:
    programme_id: str
    packet_id: str
    population_id: str
    eligible_ids_sha256: str
    scientific_manifest_sha256: str
    preregistration_sha256: str
    representation_pack_sha256: str
    segmentation_pack_sha256: str
    stability_pack_sha256: str
    source_binding_sha256: str
    capacity_grid_sha256: str
    implementation_commit: str

    def to_dict(self) -> dict[str, str]:
        payload = {
            "programme_id": self.programme_id,
            "packet_id": self.packet_id,
            "population_id": self.population_id,
            "eligible_ids_sha256": _hex64(self.eligible_ids_sha256, "eligible_ids_sha256"),
            "scientific_manifest_sha256": _hex64(self.scientific_manifest_sha256, "scientific_manifest_sha256"),
            "preregistration_sha256": _hex64(self.preregistration_sha256, "preregistration_sha256"),
            "representation_pack_sha256": _hex64(self.representation_pack_sha256, "representation_pack_sha256"),
            "segmentation_pack_sha256": _hex64(self.segmentation_pack_sha256, "segmentation_pack_sha256"),
            "stability_pack_sha256": _hex64(self.stability_pack_sha256, "stability_pack_sha256"),
            "source_binding_sha256": _hex64(self.source_binding_sha256, "source_binding_sha256"),
            "capacity_grid_sha256": _hex64(self.capacity_grid_sha256, "capacity_grid_sha256"),
            "implementation_commit": _hex64(self.implementation_commit, "implementation_commit"),
        }
        if not all(str(payload[key]).strip() for key in ("programme_id", "packet_id", "population_id")):
            raise ExecutionResilienceError("RESILIENCE_BINDING_INVALID", "programme, packet and population IDs are required")
        return payload

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.to_dict())


@dataclass(frozen=True)
class RunStartReceipt:
    run_id: str
    token_id: str
    run_binding_sha256: str
    consumption_id: str
    state: str = "CONSUMED_FOR_RUN"

    def to_dict(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "token_id": self.token_id,
            "run_binding_sha256": self.run_binding_sha256,
            "consumption_id": self.consumption_id,
            "state": self.state,
        }


class RunAuthorityStore:
    """Append-once token consumption ledger.

    A token starts one run exactly once. Resume never consumes the token again; it uses
    the immutable RunStartReceipt plus a verified checkpoint from that same run.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, token_id: str) -> Path:
        safe = token_id.replace("/", "_")
        return self.root / "consumption" / f"{safe}.json"

    def consume(self, token: Mapping[str, Any], binding: RunBinding) -> RunStartReceipt:
        token_id = str(token.get("token_id", "")).strip()
        if not token_id:
            raise ExecutionResilienceError("TOKEN_INVALID", "token_id required")
        if token.get("state") != "AUTHORIZED_UNCONSUMED":
            raise ExecutionResilienceError("TOKEN_NOT_STARTABLE", "token must be AUTHORIZED_UNCONSUMED")
        if str(token.get("run_binding_sha256", "")) != binding.logical_hash:
            raise ExecutionResilienceError("TOKEN_BINDING_MISMATCH", "token does not bind exact run inputs")
        path = self._path(token_id)
        if path.exists():
            raise ExecutionResilienceError("TOKEN_ALREADY_CONSUMED", "token already has a start receipt")
        core = {"token_id": token_id, "run_binding_sha256": binding.logical_hash}
        run_id = stable_id("SRFD.RUN.", core)
        consumption_id = stable_id("SRFD.TOKEN.CONSUMPTION.", {**core, "run_id": run_id})
        receipt = RunStartReceipt(run_id, token_id, binding.logical_hash, consumption_id)
        payload = {**receipt.to_dict(), "schema": "ovc-srfd-run-start-receipt/v1"}
        _atomic_write_json(path, payload)
        loaded = self.load(token_id)
        if loaded != receipt:
            raise ExecutionResilienceError("TOKEN_CONSUMPTION_COMMIT_FAILURE", "start receipt did not round-trip")
        return receipt

    def load(self, token_id: str) -> RunStartReceipt:
        path = self._path(token_id)
        if not path.exists():
            raise ExecutionResilienceError("TOKEN_NOT_CONSUMED", "no start receipt exists")
        try:
            data = json.loads(path.read_text())
        except Exception as exc:  # pragma: no cover - exact exception is platform dependent
            raise ExecutionResilienceError("TOKEN_CONSUMPTION_CORRUPT", str(exc)) from exc
        receipt = RunStartReceipt(
            run_id=str(data.get("run_id", "")),
            token_id=str(data.get("token_id", "")),
            run_binding_sha256=str(data.get("run_binding_sha256", "")),
            consumption_id=str(data.get("consumption_id", "")),
            state=str(data.get("state", "")),
        )
        expected_run = stable_id("SRFD.RUN.", {"token_id": receipt.token_id, "run_binding_sha256": receipt.run_binding_sha256})
        expected_consumption = stable_id("SRFD.TOKEN.CONSUMPTION.", {"token_id": receipt.token_id, "run_binding_sha256": receipt.run_binding_sha256, "run_id": expected_run})
        if receipt.state != "CONSUMED_FOR_RUN" or receipt.run_id != expected_run or receipt.consumption_id != expected_consumption:
            raise ExecutionResilienceError("TOKEN_CONSUMPTION_CORRUPT", "start receipt identity mismatch")
        return receipt


@dataclass(frozen=True)
class WorkUnitReceipt:
    unit_id: str
    output_logical_hash: str
    artifact_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "output_logical_hash": _hex64(self.output_logical_hash, "output_logical_hash"),
            "artifact_sha256": _hex64(self.artifact_sha256, "artifact_sha256") if self.artifact_sha256 else None,
        }


@dataclass(frozen=True)
class RunCheckpointReceipt:
    checkpoint_id: str
    run_id: str
    token_id: str
    run_binding_sha256: str
    sequence: int
    completed_units: tuple[str, ...]
    unit_receipts: tuple[WorkUnitReceipt, ...]
    state_logical_hash: str
    state: str = "COMMITTED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "token_id": self.token_id,
            "run_binding_sha256": self.run_binding_sha256,
            "sequence": self.sequence,
            "completed_units": list(self.completed_units),
            "unit_receipts": [item.to_dict() for item in self.unit_receipts],
            "state_logical_hash": self.state_logical_hash,
            "state": self.state,
        }


class RunCheckpointStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _run_dir(self, run_id: str) -> Path:
        return self.root / "runs" / run_id / "checkpoints"

    def _path(self, run_id: str, sequence: int) -> Path:
        return self._run_dir(run_id) / f"{sequence:08d}.json"

    def commit(
        self,
        start: RunStartReceipt,
        binding: RunBinding,
        receipts: Sequence[WorkUnitReceipt],
    ) -> RunCheckpointReceipt:
        if start.run_binding_sha256 != binding.logical_hash:
            raise ExecutionResilienceError("RESUME_BINDING_MISMATCH", "run start and binding differ")
        unit_ids = [item.unit_id for item in receipts]
        if len(unit_ids) != len(set(unit_ids)):
            raise ExecutionResilienceError("CHECKPOINT_DUPLICATE_UNIT", "completed unit IDs must be unique")
        prior = self.latest(start, binding, allow_missing=True)
        sequence = 1 if prior is None else prior.sequence + 1
        if prior is not None:
            prior_ids = list(prior.completed_units)
            if unit_ids[: len(prior_ids)] != prior_ids:
                raise ExecutionResilienceError("CHECKPOINT_HISTORY_REWRITE", "checkpoint cannot rewrite or reorder completed units")
        state_payload = {
            "run_id": start.run_id,
            "run_binding_sha256": binding.logical_hash,
            "completed_units": unit_ids,
            "unit_receipts": [item.to_dict() for item in receipts],
        }
        state_hash = logical_sha256(state_payload)
        identity_payload = {**state_payload, "sequence": sequence, "state_logical_hash": state_hash}
        checkpoint_id = stable_id("SRFD.RUN.CHECKPOINT.", identity_payload)
        receipt = RunCheckpointReceipt(
            checkpoint_id=checkpoint_id,
            run_id=start.run_id,
            token_id=start.token_id,
            run_binding_sha256=binding.logical_hash,
            sequence=sequence,
            completed_units=tuple(unit_ids),
            unit_receipts=tuple(receipts),
            state_logical_hash=state_hash,
        )
        payload = {**receipt.to_dict(), "schema": "ovc-srfd-run-checkpoint-receipt/v1"}
        path = self._path(start.run_id, sequence)
        if path.exists():
            raise ExecutionResilienceError("CHECKPOINT_IDENTITY_REUSE", "checkpoint sequence already exists")
        _atomic_write_json(path, payload)
        loaded = self._load_path(path)
        if loaded != receipt:
            raise ExecutionResilienceError("CHECKPOINT_COMMIT_FAILURE", "checkpoint did not round-trip")
        return receipt

    def _load_path(self, path: Path) -> RunCheckpointReceipt:
        try:
            data = json.loads(path.read_text())
        except Exception as exc:  # pragma: no cover
            raise ExecutionResilienceError("CHECKPOINT_CORRUPT", str(exc)) from exc
        units = tuple(str(v) for v in data.get("completed_units", []))
        receipts = tuple(
            WorkUnitReceipt(
                unit_id=str(item.get("unit_id", "")),
                output_logical_hash=str(item.get("output_logical_hash", "")),
                artifact_sha256=item.get("artifact_sha256"),
            )
            for item in data.get("unit_receipts", [])
        )
        receipt = RunCheckpointReceipt(
            checkpoint_id=str(data.get("checkpoint_id", "")),
            run_id=str(data.get("run_id", "")),
            token_id=str(data.get("token_id", "")),
            run_binding_sha256=str(data.get("run_binding_sha256", "")),
            sequence=int(data.get("sequence", 0)),
            completed_units=units,
            unit_receipts=receipts,
            state_logical_hash=str(data.get("state_logical_hash", "")),
            state=str(data.get("state", "")),
        )
        state_payload = {
            "run_id": receipt.run_id,
            "run_binding_sha256": receipt.run_binding_sha256,
            "completed_units": list(receipt.completed_units),
            "unit_receipts": [item.to_dict() for item in receipt.unit_receipts],
        }
        expected_hash = logical_sha256(state_payload)
        expected_id = stable_id("SRFD.RUN.CHECKPOINT.", {**state_payload, "sequence": receipt.sequence, "state_logical_hash": expected_hash})
        if receipt.state != "COMMITTED" or receipt.state_logical_hash != expected_hash or receipt.checkpoint_id != expected_id:
            raise ExecutionResilienceError("CHECKPOINT_CORRUPT", "checkpoint hash or identity mismatch")
        if len(receipt.completed_units) != len(receipt.unit_receipts):
            raise ExecutionResilienceError("CHECKPOINT_CORRUPT", "unit receipt cardinality mismatch")
        if [item.unit_id for item in receipt.unit_receipts] != list(receipt.completed_units):
            raise ExecutionResilienceError("CHECKPOINT_CORRUPT", "unit receipt order mismatch")
        return receipt

    def latest(self, start: RunStartReceipt, binding: RunBinding, *, allow_missing: bool = False) -> RunCheckpointReceipt | None:
        if start.run_binding_sha256 != binding.logical_hash:
            raise ExecutionResilienceError("RESUME_BINDING_MISMATCH", "run start and binding differ")
        directory = self._run_dir(start.run_id)
        if not directory.exists():
            if allow_missing:
                return None
            raise ExecutionResilienceError("CHECKPOINT_MISSING", "no committed checkpoint exists")
        paths = sorted(p for p in directory.glob("*.json") if p.name[:-5].isdigit())
        if not paths:
            if allow_missing:
                return None
            raise ExecutionResilienceError("CHECKPOINT_MISSING", "no committed checkpoint exists")
        receipts = [self._load_path(path) for path in paths]
        for expected_sequence, receipt in enumerate(receipts, start=1):
            if receipt.sequence != expected_sequence:
                raise ExecutionResilienceError("CHECKPOINT_SEQUENCE_GAP", "checkpoint sequence must be contiguous")
            if receipt.run_id != start.run_id or receipt.token_id != start.token_id or receipt.run_binding_sha256 != binding.logical_hash:
                raise ExecutionResilienceError("RESUME_BINDING_MISMATCH", "checkpoint belongs to another run or authority")
            if expected_sequence > 1:
                previous = receipts[expected_sequence - 2]
                if list(receipt.completed_units)[: len(previous.completed_units)] != list(previous.completed_units):
                    raise ExecutionResilienceError("CHECKPOINT_HISTORY_REWRITE", "later checkpoint rewrites prior committed units")
        return receipts[-1]


def execute_resumable_units(
    *,
    start: RunStartReceipt,
    binding: RunBinding,
    checkpoint_store: RunCheckpointStore,
    unit_ids: Iterable[str],
    worker: Callable[[str], Mapping[str, Any]],
    stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    ordered = tuple(str(v) for v in unit_ids)
    if len(ordered) != len(set(ordered)):
        raise ExecutionResilienceError("WORK_UNIT_DUPLICATE", "work unit IDs must be unique")
    checkpoint = checkpoint_store.latest(start, binding, allow_missing=True)
    committed = [] if checkpoint is None else list(checkpoint.unit_receipts)
    completed = {item.unit_id for item in committed}
    new_count = 0
    for unit_id in ordered:
        if unit_id in completed:
            continue
        output = worker(unit_id)
        if not isinstance(output, Mapping):
            raise ExecutionResilienceError("WORK_UNIT_INVALID_OUTPUT", f"{unit_id} did not return a mapping")
        committed.append(WorkUnitReceipt(unit_id=unit_id, output_logical_hash=logical_sha256(output)))
        checkpoint = checkpoint_store.commit(start, binding, committed)
        completed.add(unit_id)
        new_count += 1
        if stop_after_new_units is not None and new_count >= stop_after_new_units:
            break
    complete = len(completed) == len(ordered)
    payload = {
        "run_id": start.run_id,
        "run_binding_sha256": binding.logical_hash,
        "ordered_unit_count": len(ordered),
        "completed_unit_count": len(completed),
        "completed_units": [item.unit_id for item in committed],
        "unit_output_hashes": {item.unit_id: item.output_logical_hash for item in committed},
        "last_checkpoint_id": checkpoint.checkpoint_id if checkpoint else None,
        "complete": complete,
        "authority_effect": "NONE",
    }
    return {**payload, "result_logical_hash": logical_sha256(payload)}
