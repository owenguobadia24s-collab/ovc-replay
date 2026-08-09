from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Iterable, Mapping

from .serialization import canonical_json_bytes, logical_sha256
from .wp10_execution_resilience import (
    ExecutionResilienceError,
    RunBinding,
    RunCheckpointStore,
    RunStartReceipt,
    WorkUnitReceipt,
)


class DurableExecutionError(ExecutionResilienceError):
    pass


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    try:
        directory_fd = os.open(str(path.parent), os.O_RDONLY)
    except (AttributeError, OSError):
        return
    try:
        os.fsync(directory_fd)
    except OSError:
        pass
    finally:
        os.close(directory_fd)


def _artifact_name(unit_id: str) -> str:
    return sha256(unit_id.encode("utf-8")).hexdigest() + ".json"


def peak_rss_bytes() -> int:
    """Return process peak resident memory using only the Python standard library."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        process = ctypes.windll.kernel32.GetCurrentProcess()
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            process, ctypes.byref(counters), ctypes.sizeof(counters)
        )
        if not ok:
            raise DurableExecutionError(
                "CAPACITY_TELEMETRY_UNAVAILABLE", "GetProcessMemoryInfo failed"
            )
        return int(counters.PeakWorkingSetSize)

    try:
        import resource
    except ImportError as exc:  # pragma: no cover - unusual non-Windows platform
        raise DurableExecutionError(
            "CAPACITY_TELEMETRY_UNAVAILABLE", "resource module unavailable"
        ) from exc
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


class RunArtifactStore:
    """Durable, content-bound external artifact store for one resumable run.

    Scientific outputs are written before checkpoint commitment. If a process dies after
    the artifact write but before checkpoint commit, recomputation must reproduce the
    identical bytes; otherwise the run fails closed instead of silently rewriting history.
    """

    def __init__(self, root: Path, *, max_external_bytes: int | None = None) -> None:
        self.root = Path(root)
        self.max_external_bytes = max_external_bytes
        self._size_cache: dict[str, int] = {}

    def _run_dir(self, run_id: str) -> Path:
        return self.root / "runs" / run_id / "artifacts"

    def _path(self, run_id: str, unit_id: str) -> Path:
        return self._run_dir(run_id) / _artifact_name(unit_id)

    def total_bytes(self, run_id: str) -> int:
        if run_id not in self._size_cache:
            directory = self._run_dir(run_id)
            total = 0
            if directory.exists():
                total = sum(
                    path.stat().st_size
                    for path in directory.glob("*.json")
                    if path.is_file()
                )
            self._size_cache[run_id] = total
        return self._size_cache[run_id]

    def commit_output(
        self,
        start: RunStartReceipt,
        binding: RunBinding,
        unit_id: str,
        output: Mapping[str, Any],
    ) -> WorkUnitReceipt:
        if start.run_binding_sha256 != binding.logical_hash:
            raise DurableExecutionError(
                "RESUME_BINDING_MISMATCH", "artifact run start and binding differ"
            )
        unit = str(unit_id).strip()
        if not unit:
            raise DurableExecutionError("WORK_UNIT_INVALID_OUTPUT", "unit_id required")
        logical_hash = logical_sha256(output)
        envelope = {
            "schema": "ovc-srfd-run-work-unit-artifact/v1",
            "run_id": start.run_id,
            "token_id": start.token_id,
            "run_binding_sha256": binding.logical_hash,
            "unit_id": unit,
            "output_logical_hash": logical_hash,
            "output": dict(output),
        }
        data = canonical_json_bytes(envelope) + b"\n"
        artifact_sha = sha256(data).hexdigest()
        path = self._path(start.run_id, unit)
        if path.exists():
            existing = path.read_bytes()
            if existing != data:
                raise DurableExecutionError(
                    "ARTIFACT_HISTORY_REWRITE",
                    f"existing artifact differs for committed unit candidate:{unit}",
                )
        else:
            projected = self.total_bytes(start.run_id) + len(data)
            if self.max_external_bytes is not None and projected > self.max_external_bytes:
                raise DurableExecutionError(
                    "CAPACITY_EXTERNAL_BYTES_EXCEEDED",
                    f"projected={projected} limit={self.max_external_bytes}",
                )
            _atomic_write_bytes(path, data)
            self._size_cache[start.run_id] = projected
        receipt = WorkUnitReceipt(
            unit_id=unit,
            output_logical_hash=logical_hash,
            artifact_sha256=artifact_sha,
        )
        self.verify_receipt(start, binding, receipt)
        return receipt

    def load_output(
        self,
        start: RunStartReceipt,
        binding: RunBinding,
        unit_id: str,
    ) -> dict[str, Any]:
        if start.run_binding_sha256 != binding.logical_hash:
            raise DurableExecutionError(
                "RESUME_BINDING_MISMATCH", "artifact run start and binding differ"
            )
        path = self._path(start.run_id, unit_id)
        if not path.exists():
            raise DurableExecutionError(
                "ARTIFACT_MISSING", f"no durable artifact for unit:{unit_id}"
            )
        raw = path.read_bytes()
        try:
            envelope = json.loads(raw)
        except Exception as exc:
            raise DurableExecutionError("ARTIFACT_CORRUPT", str(exc)) from exc
        expected_sha = sha256(raw).hexdigest()
        if (
            envelope.get("schema") != "ovc-srfd-run-work-unit-artifact/v1"
            or envelope.get("run_id") != start.run_id
            or envelope.get("token_id") != start.token_id
            or envelope.get("run_binding_sha256") != binding.logical_hash
            or envelope.get("unit_id") != unit_id
        ):
            raise DurableExecutionError(
                "ARTIFACT_BINDING_MISMATCH", f"artifact envelope mismatch:{unit_id}"
            )
        output = envelope.get("output")
        if not isinstance(output, Mapping):
            raise DurableExecutionError(
                "ARTIFACT_CORRUPT", f"artifact output is not a mapping:{unit_id}"
            )
        logical_hash = logical_sha256(output)
        if envelope.get("output_logical_hash") != logical_hash:
            raise DurableExecutionError(
                "ARTIFACT_CORRUPT", f"artifact logical hash mismatch:{unit_id}"
            )
        envelope["_verified_artifact_sha256"] = expected_sha
        return dict(output)

    def verify_receipt(
        self,
        start: RunStartReceipt,
        binding: RunBinding,
        receipt: WorkUnitReceipt,
    ) -> None:
        if receipt.artifact_sha256 is None:
            raise DurableExecutionError(
                "CHECKPOINT_ARTIFACT_HASH_MISSING", receipt.unit_id
            )
        path = self._path(start.run_id, receipt.unit_id)
        if not path.exists():
            raise DurableExecutionError("ARTIFACT_MISSING", receipt.unit_id)
        raw = path.read_bytes()
        actual_sha = sha256(raw).hexdigest()
        if actual_sha != receipt.artifact_sha256:
            raise DurableExecutionError(
                "ARTIFACT_CORRUPT", f"file sha mismatch:{receipt.unit_id}"
            )
        output = self.load_output(start, binding, receipt.unit_id)
        if logical_sha256(output) != receipt.output_logical_hash:
            raise DurableExecutionError(
                "ARTIFACT_CORRUPT", f"receipt logical hash mismatch:{receipt.unit_id}"
            )


class RunCapacityStore:
    """Non-scientific execution telemetry persisted independently of output identity."""

    def __init__(
        self,
        root: Path,
        *,
        max_committed_active_wall_seconds: float,
        max_peak_rss_bytes: int,
    ) -> None:
        self.root = Path(root)
        self.max_wall = float(max_committed_active_wall_seconds)
        self.max_rss = int(max_peak_rss_bytes)

    def _path(self, run_id: str) -> Path:
        return self.root / "runs" / run_id / "capacity_telemetry.json"

    def load(self, start: RunStartReceipt, binding: RunBinding) -> dict[str, Any]:
        if start.run_binding_sha256 != binding.logical_hash:
            raise DurableExecutionError(
                "RESUME_BINDING_MISMATCH", "capacity run start and binding differ"
            )
        path = self._path(start.run_id)
        if not path.exists():
            return {
                "schema": "ovc-srfd-run-capacity-telemetry/v1",
                "run_id": start.run_id,
                "run_binding_sha256": binding.logical_hash,
                "committed_active_wall_seconds": 0.0,
                "peak_rss_bytes": 0,
                "accounted_unit_count": 0,
                "capacity_status": "WITHIN_T0",
            }
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DurableExecutionError("CAPACITY_TELEMETRY_CORRUPT", str(exc)) from exc
        if (
            payload.get("schema") != "ovc-srfd-run-capacity-telemetry/v1"
            or payload.get("run_id") != start.run_id
            or payload.get("run_binding_sha256") != binding.logical_hash
        ):
            raise DurableExecutionError(
                "CAPACITY_TELEMETRY_CORRUPT", "capacity identity mismatch"
            )
        return payload

    def account_unit(
        self,
        start: RunStartReceipt,
        binding: RunBinding,
        *,
        active_wall_seconds: float,
    ) -> dict[str, Any]:
        if active_wall_seconds < 0:
            raise DurableExecutionError(
                "CAPACITY_TELEMETRY_CORRUPT", "negative active wall"
            )
        prior = self.load(start, binding)
        wall = float(prior["committed_active_wall_seconds"]) + float(active_wall_seconds)
        rss = max(int(prior["peak_rss_bytes"]), peak_rss_bytes())
        status = "WITHIN_T0" if wall <= self.max_wall and rss <= self.max_rss else "CAPACITY_EXCEEDED"
        payload = {
            "schema": "ovc-srfd-run-capacity-telemetry/v1",
            "run_id": start.run_id,
            "run_binding_sha256": binding.logical_hash,
            "committed_active_wall_seconds": wall,
            "peak_rss_bytes": rss,
            "accounted_unit_count": int(prior["accounted_unit_count"]) + 1,
            "capacity_status": status,
            "t0": {
                "max_committed_active_wall_seconds": self.max_wall,
                "max_peak_rss_bytes": self.max_rss,
            },
        }
        _atomic_write_bytes(self._path(start.run_id), canonical_json_bytes(payload) + b"\n")
        if status != "WITHIN_T0":
            raise DurableExecutionError(
                "CAPACITY_EXCEEDED", f"wall={wall} rss={rss}"
            )
        return payload


def execute_durable_resumable_units(
    *,
    start: RunStartReceipt,
    binding: RunBinding,
    checkpoint_store: RunCheckpointStore,
    artifact_store: RunArtifactStore,
    unit_ids: Iterable[str],
    worker: Callable[[str], Mapping[str, Any]],
    capacity_store: RunCapacityStore | None = None,
    stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    ordered = tuple(str(value) for value in unit_ids)
    if len(ordered) != len(set(ordered)):
        raise DurableExecutionError("WORK_UNIT_DUPLICATE", "work unit IDs must be unique")
    checkpoint = checkpoint_store.latest(start, binding, allow_missing=True)
    committed = [] if checkpoint is None else list(checkpoint.unit_receipts)
    for receipt in committed:
        artifact_store.verify_receipt(start, binding, receipt)
    completed = {item.unit_id for item in committed}
    new_count = 0
    for unit_id in ordered:
        if unit_id in completed:
            continue
        started = time.perf_counter()
        output = worker(unit_id)
        if not isinstance(output, Mapping):
            raise DurableExecutionError(
                "WORK_UNIT_INVALID_OUTPUT", f"{unit_id} did not return a mapping"
            )
        active_seconds = time.perf_counter() - started
        if capacity_store is not None:
            capacity_store.account_unit(
                start, binding, active_wall_seconds=active_seconds
            )
        receipt = artifact_store.commit_output(start, binding, unit_id, output)
        committed.append(receipt)
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
        "unit_output_hashes": {
            item.unit_id: item.output_logical_hash for item in committed
        },
        "unit_artifact_sha256": {
            item.unit_id: item.artifact_sha256 for item in committed
        },
        "last_checkpoint_id": checkpoint.checkpoint_id if checkpoint else None,
        "complete": complete,
        "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
    }
    return {**payload, "result_logical_hash": logical_sha256(payload)}
