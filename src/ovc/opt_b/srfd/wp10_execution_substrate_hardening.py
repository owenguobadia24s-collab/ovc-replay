from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

from .serialization import logical_sha256
from .wp10_durable_execution import RunCapacityStore, execute_durable_resumable_units
from .wp10_execution_resilience import RunCheckpointStore, RunStartReceipt
from .wp10_v10_storage import ContentAddressedArtifactStoreV10


PROGRAMME_ID = "OVC-SRFD-BENCHMARK-v0.1"
HARDENING_PACKET_ID = "SRFDI-WP10-EXECUTION-SUBSTRATE-HARDENING-v0.1"
SYNTHETIC_REHEARSAL_UNIT_COUNT = 2020
SYNTHETIC_DOMAIN_COUNT = 36
SYNTHETIC_CONFIGS_PER_DOMAIN = 54


class ExecutionSubstrateHardeningError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _read_int_file(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw or raw == "max":
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _physical_memory_bytes() -> int | None:
    if os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
        except Exception:
            return None
        return None
    try:
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, OSError, ValueError):
        return None
    return pages * page_size if pages > 0 and page_size > 0 else None


def _process_address_space_limit_bytes() -> int | None:
    if os.name == "nt":
        return None
    try:
        import resource

        soft, _hard = resource.getrlimit(resource.RLIMIT_AS)
    except (ImportError, OSError, ValueError):
        return None
    if soft in (-1, getattr(resource, "RLIM_INFINITY", -1)):
        return None
    return int(soft) if int(soft) > 0 else None


def _cgroup_memory_limit_bytes() -> int | None:
    candidates = (
        Path("/sys/fs/cgroup/memory.max"),
        Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
    )
    values = [value for value in (_read_int_file(path) for path in candidates) if value]
    if not values:
        return None
    # Some cgroup v1 hosts expose an effectively-infinite sentinel. Ignore values
    # larger than 2**60 so the profile reflects a real enforcement ceiling.
    realistic = [value for value in values if value < 2**60]
    return min(realistic) if realistic else None


def _filesystem_type(path: Path) -> str | None:
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            root = Path(path.anchor or path.drive + "\\")
            fs_name = ctypes.create_unicode_buffer(256)
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                wintypes.LPCWSTR(str(root)),
                None,
                0,
                None,
                None,
                None,
                fs_name,
                len(fs_name),
            )
            return fs_name.value if ok else None
        except Exception:
            return None
    try:
        resolved = path.resolve()
        best_mount = ""
        best_fs = None
        for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            mount = parts[1].replace("\\040", " ")
            if str(resolved).startswith(mount.rstrip("/") + "/") or str(resolved) == mount:
                if len(mount) > len(best_mount):
                    best_mount = mount
                    best_fs = parts[2]
        return best_fs
    except OSError:
        return None


def _selected_dependency_versions() -> dict[str, str]:
    names = (
        "pytest",
        "pydantic",
        "fastapi",
        "numpy",
        "scipy",
        "pandas",
        "orjson",
    )
    result: dict[str, str] = {}
    for name in names:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = "NOT_INSTALLED"
    return result


def capture_execution_environment_profile(
    *,
    artifact_root: Path,
    temporary_root: Path | None = None,
) -> dict[str, Any]:
    """Capture the real execution-host envelope that must be bound before v1.1.

    This is execution governance only.  It does not change SRFD scientific inputs,
    methods, population, family grid, Validation state, or any market authority.
    """
    artifact_root = Path(artifact_root).resolve()
    temp_root = Path(temporary_root or tempfile.gettempdir()).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    temp_root.mkdir(parents=True, exist_ok=True)

    physical = _physical_memory_bytes()
    cgroup = _cgroup_memory_limit_bytes()
    address_space = _process_address_space_limit_bytes()
    candidates = [value for value in (physical, cgroup, address_space) if value]
    effective_memory = min(candidates) if candidates else None
    artifact_usage = shutil.disk_usage(artifact_root)
    temp_usage = shutil.disk_usage(temp_root)
    cpu_count = os.cpu_count()
    env_concurrency = {
        name: os.environ.get(name)
        for name in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        )
        if os.environ.get(name) is not None
    }
    body: dict[str, Any] = {
        "schema": "ovc-srfdi-execution-environment-profile/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": HARDENING_PACKET_ID,
        "authority_effect": "EXECUTION_GOVERNANCE_ONLY",
        "scientific_delta": "NONE",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
        },
        "memory": {
            "physical_bytes": physical,
            "cgroup_limit_bytes": cgroup,
            "process_address_space_limit_bytes": address_space,
            "effective_detected_ceiling_bytes": effective_memory,
        },
        "artifact_storage": {
            "path": str(artifact_root),
            "filesystem_type": _filesystem_type(artifact_root),
            "total_bytes": artifact_usage.total,
            "free_bytes": artifact_usage.free,
        },
        "temporary_storage": {
            "path": str(temp_root),
            "filesystem_type": _filesystem_type(temp_root),
            "total_bytes": temp_usage.total,
            "free_bytes": temp_usage.free,
        },
        "concurrency": {
            "logical_cpu_count": cpu_count,
            "environment_thread_limits": env_concurrency,
            "srfd_worker_model": "SERIAL_WORK_UNIT_COMMIT_ORDER",
        },
        "dependencies": _selected_dependency_versions(),
        "required_profile_fields_complete": all(
            value is not None
            for value in (
                effective_memory,
                artifact_usage.total,
                artifact_usage.free,
                temp_usage.total,
                temp_usage.free,
                cpu_count,
            )
        ),
    }
    return {**body, "logical_sha256": logical_sha256(body)}


def classify_work_unit_id(unit_id: str) -> str:
    unit = str(unit_id)
    if unit == "population":
        return "POPULATION"
    if unit.startswith("segmentation/") and len(unit.split("/")) == 2:
        return "SEGMENTATION"
    if unit == "packet":
        return "TERMINAL_AGGREGATION"
    parts = unit.split("/")
    if len(parts) == 3 and parts[0] == "domain" and parts[2] == "prepare":
        return "DOMAIN_PREPARATION"
    if len(parts) == 4 and parts[0] == "domain" and parts[2] == "configuration":
        return "CONFIGURATION"
    if len(parts) == 3 and parts[0] == "domain" and parts[2] == "analysis":
        return "DOMAIN_ANALYSIS"
    raise ExecutionSubstrateHardeningError("WORK_UNIT_CLASS_UNKNOWN", unit)


def validate_work_unit_output_contract(unit_id: str, output: Mapping[str, Any]) -> dict[str, Any]:
    """Fail immediately when a worker dispatches the wrong object type for a unit ID."""
    kind = classify_work_unit_id(unit_id)
    schema = str(output.get("schema", ""))
    expected_schema = {
        "POPULATION": "ovc-srfdi-wp10-v07-population-unit/v1",
        "SEGMENTATION": "ovc-srfdi-wp10-v07-segmentation-output/v1",
        "DOMAIN_PREPARATION": "ovc-srfdi-wp10-v07-domain-preparation/v1",
        "CONFIGURATION": "ovc-srfdi-wp10-v07-family-configuration/v1",
        "TERMINAL_AGGREGATION": "ovc-srfdi-wp10-v07-production-evidence-packet/v1",
    }.get(kind)
    if expected_schema is not None and schema != expected_schema:
        raise ExecutionSubstrateHardeningError(
            "WORK_UNIT_OUTPUT_SCHEMA_MISMATCH",
            f"unit={unit_id} kind={kind} expected={expected_schema} actual={schema}",
        )
    if kind == "CONFIGURATION" and not isinstance(output.get("catalog"), Mapping):
        raise ExecutionSubstrateHardeningError(
            "WORK_UNIT_OUTPUT_CONTRACT_MISMATCH", f"configuration missing catalog:{unit_id}"
        )
    if kind == "DOMAIN_PREPARATION" and not isinstance(output.get("preparation"), Mapping):
        raise ExecutionSubstrateHardeningError(
            "WORK_UNIT_OUTPUT_CONTRACT_MISMATCH", f"preparation missing preparation payload:{unit_id}"
        )
    if kind == "DOMAIN_ANALYSIS":
        if schema == "ovc-srfdi-wp10-v07-domain-preparation/v1" or "catalog" in output:
            raise ExecutionSubstrateHardeningError(
                "WORK_UNIT_OUTPUT_CONTRACT_MISMATCH", f"analysis received non-analysis payload:{unit_id}"
            )
        if str(output.get("domain_id", "")) != unit_id.split("/")[1]:
            raise ExecutionSubstrateHardeningError(
                "WORK_UNIT_OUTPUT_CONTRACT_MISMATCH", f"analysis domain mismatch:{unit_id}"
            )
    if kind in {"DOMAIN_PREPARATION", "CONFIGURATION", "DOMAIN_ANALYSIS"}:
        expected_domain = unit_id.split("/")[1]
        if str(output.get("domain_id", "")) != expected_domain:
            raise ExecutionSubstrateHardeningError(
                "WORK_UNIT_OUTPUT_CONTRACT_MISMATCH",
                f"domain mismatch unit={unit_id} output={output.get('domain_id')}",
            )
    return dict(output)


def synthetic_rehearsal_unit_ids() -> tuple[str, ...]:
    units: list[str] = [
        "population",
        "segmentation/RUN_CHANGE_SEGMENTATION",
        "segmentation/NULL_BOUNDARY_CONTROL",
    ]
    for domain_index in range(SYNTHETIC_DOMAIN_COUNT):
        domain_id = f"SYNTH-DOMAIN-{domain_index:02d}"
        units.append(f"domain/{domain_id}/prepare")
        for config_index in range(SYNTHETIC_CONFIGS_PER_DOMAIN):
            units.append(f"domain/{domain_id}/configuration/SYNTH-CONFIG-{config_index:02d}")
        units.append(f"domain/{domain_id}/analysis")
    units.append("packet")
    if len(units) != SYNTHETIC_REHEARSAL_UNIT_COUNT:
        raise ExecutionSubstrateHardeningError(
            "SYNTHETIC_REHEARSAL_PLAN_COUNT_DRIFT", str(len(units))
        )
    return tuple(units)


def synthetic_minimal_worker(unit_id: str) -> Mapping[str, Any]:
    kind = classify_work_unit_id(unit_id)
    if kind == "POPULATION":
        output: dict[str, Any] = {
            "schema": "ovc-srfdi-wp10-v07-population-unit/v1",
            "synthetic": True,
            "work_unit_count": SYNTHETIC_REHEARSAL_UNIT_COUNT,
        }
    elif kind == "SEGMENTATION":
        output = {
            "schema": "ovc-srfdi-wp10-v07-segmentation-output/v1",
            "method_id": unit_id.split("/", 1)[1],
            "counts": {"synthetic": 1},
            "result": {"synthetic": True},
        }
    elif kind == "DOMAIN_PREPARATION":
        domain_id = unit_id.split("/")[1]
        output = {
            "schema": "ovc-srfdi-wp10-v07-domain-preparation/v1",
            "domain_id": domain_id,
            "preparation": {"synthetic": True},
            "configuration_plan": [],
        }
    elif kind == "CONFIGURATION":
        parts = unit_id.split("/")
        output = {
            "schema": "ovc-srfdi-wp10-v07-family-configuration/v1",
            "domain_id": parts[1],
            "configuration": {"configuration_id": parts[3]},
            "catalog": {"synthetic": True, "configuration_id": parts[3]},
        }
    elif kind == "DOMAIN_ANALYSIS":
        output = {
            "schema": "ovc-srfdi-wp10-v07-domain-analysis/v1",
            "domain_id": unit_id.split("/")[1],
            "synthetic": True,
        }
    else:
        output = {
            "schema": "ovc-srfdi-wp10-v07-production-evidence-packet/v1",
            "synthetic": True,
            "completed_work_unit_count_before_packet": SYNTHETIC_REHEARSAL_UNIT_COUNT - 1,
        }
    output["authority_effect"] = "NONE_SYNTHETIC_EXECUTION_ASSURANCE_ONLY"
    output["logical_hash"] = logical_sha256(output)
    return validate_work_unit_output_contract(unit_id, output)


@dataclass(frozen=True)
class _SyntheticBinding:
    logical_hash: str


def run_full_2020_unit_rehearsal(root: Path) -> dict[str, Any]:
    """Exercise the exact durable scheduler/checkpoint/CAS route across all 2,020 units.

    Intentional stops occur at unit-class boundaries.  The last resume executes only the
    terminal packet so restart behavior is tested on both sides of every unit class.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    binding_hash = sha256(b"OVC-SRFD-SYNTHETIC-2020-UNIT-REHEARSAL-v1").hexdigest()
    binding = _SyntheticBinding(binding_hash)
    start = RunStartReceipt(
        run_id="SRFD.SYNTHETIC.REHEARSAL.2020.v1",
        token_id="SRFD.SYNTHETIC.AUTH.NOT_REAL.v1",
        run_binding_sha256=binding_hash,
        consumption_id="SRFD.SYNTHETIC.CONSUMPTION.NOT_REAL.v1",
    )
    checkpoints = RunCheckpointStore(root)
    artifacts = ContentAddressedArtifactStoreV10(root, max_external_bytes=8 * 1024**3)
    capacity = RunCapacityStore(
        root,
        max_committed_active_wall_seconds=24 * 60 * 60,
        max_peak_rss_bytes=1024**4,
    )
    units = synthetic_rehearsal_unit_ids()
    # Cumulative boundary totals: population=1, segmentations=3, first prepare=4,
    # first domain configurations=58, first analysis=59, before final packet=2019.
    targets: Sequence[int] = (1, 3, 4, 58, 59, 2019, 2020)
    completed = 0
    passes: list[dict[str, Any]] = []
    started = time.perf_counter()
    for target in targets:
        result = execute_durable_resumable_units(
            start=start,
            binding=binding,
            checkpoint_store=checkpoints,
            artifact_store=artifacts,
            capacity_store=capacity,
            unit_ids=units,
            worker=synthetic_minimal_worker,
            stop_after_new_units=target - completed,
        )
        completed = int(result["completed_unit_count"])
        if completed != target:
            raise ExecutionSubstrateHardeningError(
                "SYNTHETIC_RESTART_TARGET_MISMATCH", f"target={target} completed={completed}"
            )
        passes.append(
            {
                "target_completed": target,
                "last_checkpoint_id": result["last_checkpoint_id"],
                "complete": bool(result["complete"]),
                "result_logical_hash": result["result_logical_hash"],
            }
        )
    final = checkpoints.latest(start, binding)
    if final is None or final.sequence != SYNTHETIC_REHEARSAL_UNIT_COUNT:
        raise ExecutionSubstrateHardeningError(
            "SYNTHETIC_CHECKPOINT_COUNT_MISMATCH",
            f"sequence={None if final is None else final.sequence}",
        )
    if tuple(final.completed_units) != units:
        raise ExecutionSubstrateHardeningError(
            "SYNTHETIC_CHECKPOINT_ORDER_MISMATCH", "final unit order differs"
        )
    elapsed = time.perf_counter() - started
    body = {
        "schema": "ovc-srfdi-2020-unit-synthetic-rehearsal-receipt/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": HARDENING_PACKET_ID,
        "status": "PASS",
        "authority_effect": "NONE_SYNTHETIC_EXECUTION_ASSURANCE_ONLY",
        "scientific_delta": "NONE",
        "real_june_payload_used": False,
        "scheduler": "execute_durable_resumable_units",
        "checkpoint_store": "RunCheckpointStore",
        "artifact_store": "ContentAddressedArtifactStoreV10",
        "capacity_store": "RunCapacityStore",
        "ordered_unit_count": len(units),
        "completed_unit_count": len(final.completed_units),
        "checkpoint_sequence": final.sequence,
        "restart_targets": list(targets),
        "restart_passes": passes,
        "elapsed_seconds": elapsed,
        "external_artifact_bytes": artifacts.total_bytes(start.run_id),
        "final_checkpoint_id": final.checkpoint_id,
    }
    return {**body, "logical_sha256": logical_sha256(body)}
