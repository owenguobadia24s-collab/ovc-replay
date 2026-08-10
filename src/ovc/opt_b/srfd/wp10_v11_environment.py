from __future__ import annotations

from hashlib import sha256
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
try:
    import resource
except ImportError:  # Windows: profile capture is Linux-runner specific, import remains safe.
    resource = None  # type: ignore[assignment]
import sys
import tempfile
from typing import Any, Mapping

from .serialization import canonical_json_bytes, logical_sha256


PROFILE_SCHEMA = "ovc-srfdi-execution-environment-profile/v1"
RELEVANT_DEPENDENCIES = (
    "pytest", "numpy", "scipy", "pandas", "pydantic", "fastapi", "setuptools", "pip"
)


class ExecutionEnvironmentError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _read_text(path: str | Path) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _cgroup_int(path: str | Path) -> int | None:
    value = _read_text(path)
    if value in (None, "", "max"):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _meminfo() -> dict[str, int]:
    path = Path("/proc/meminfo")
    if not path.exists():
        return {}
    result: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, raw = line.split(":", 1)
        parts = raw.strip().split()
        if not parts:
            continue
        value = int(parts[0])
        if len(parts) > 1 and parts[1] == "kB":
            value *= 1024
        result[key] = value
    return result


def _filesystem_identity(path: str | Path) -> dict[str, Any]:
    resolved = os.path.realpath(path)
    mount_point = None
    filesystem_type = None
    source = None
    mountinfo = Path("/proc/self/mountinfo")
    if mountinfo.exists():
        best_len = -1
        for line in mountinfo.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            try:
                sep = parts.index("-")
            except ValueError:
                continue
            mount = parts[4]
            if resolved == mount or resolved.startswith(mount.rstrip("/") + "/"):
                if len(mount) > best_len:
                    best_len = len(mount)
                    mount_point = mount
                    filesystem_type = parts[sep + 1]
                    source = parts[sep + 2]
    stat = os.statvfs(path)
    return {
        "path": str(path),
        "mount_point": mount_point,
        "filesystem_type": filesystem_type,
        "source": source,
        "block_size": int(stat.f_frsize),
        "total_bytes": int(stat.f_frsize * stat.f_blocks),
        "available_bytes": int(stat.f_frsize * stat.f_bavail),
        "free_bytes": int(stat.f_frsize * stat.f_bfree),
    }


def _process_limits() -> dict[str, dict[str, int | None]]:
    result: dict[str, dict[str, int | None]] = {}
    if resource is None:
        return result
    for name in ("RLIMIT_AS", "RLIMIT_DATA", "RLIMIT_RSS", "RLIMIT_NOFILE", "RLIMIT_NPROC", "RLIMIT_STACK"):
        if not hasattr(resource, name):
            continue
        soft, hard = resource.getrlimit(getattr(resource, name))
        result[name] = {
            "soft": None if soft == resource.RLIM_INFINITY else int(soft),
            "hard": None if hard == resource.RLIM_INFINITY else int(hard),
        }
    return result


def capture_execution_environment(
    *,
    profile_id: str,
    working_root: str | Path,
    captured_at: str,
    pip_freeze_bytes: bytes | None = None,
    required_min_free_bytes_before_run: int = 30 * 1024**3,
    t1_external_artifact_limit_bytes: int = 24 * 1024**3,
    minimum_temp_reserve_bytes: int = 4 * 1024**3,
) -> dict[str, Any]:
    mem = _meminfo()
    cpu_max = _read_text("/sys/fs/cgroup/cpu.max")
    quota_cores = None
    if cpu_max:
        parts = cpu_max.split()
        if len(parts) == 2 and parts[0] != "max":
            quota_cores = int(parts[0]) / int(parts[1])
    dependencies: dict[str, str | None] = {}
    for name in RELEVANT_DEPENDENCIES:
        try:
            dependencies[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            dependencies[name] = None
    dependency_inventory = None
    if pip_freeze_bytes is not None:
        dependency_inventory = {
            "pip_freeze_line_count": len(pip_freeze_bytes.splitlines()),
            "pip_freeze_sha256": sha256(pip_freeze_bytes).hexdigest(),
        }
    temp_root = tempfile.gettempdir()
    payload: dict[str, Any] = {
        "schema": PROFILE_SCHEMA,
        "profile_id": str(profile_id),
        "captured_at": str(captured_at),
        "purpose": "Freeze actual host/process/storage limits before SRFDI-WP10-v1.1 scientific retry.",
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "kernel": _read_text("/proc/version"),
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
            "compiler": platform.python_compiler(),
        },
        "dependencies": dependencies,
        "dependency_inventory": dependency_inventory,
        "concurrency": {
            "os_cpu_count": os.cpu_count(),
            "cgroup_cpu_max": cpu_max,
            "effective_cpu_quota_cores": quota_cores,
            "pids_max": _read_text("/sys/fs/cgroup/pids.max"),
        },
        "memory": {
            "host_mem_total_bytes": mem.get("MemTotal"),
            "host_mem_available_bytes_at_capture": mem.get("MemAvailable"),
            "swap_total_bytes": mem.get("SwapTotal"),
            "swap_free_bytes_at_capture": mem.get("SwapFree"),
            "cgroup_memory_max_bytes": _cgroup_int("/sys/fs/cgroup/memory.max"),
            "cgroup_memory_high_bytes": _cgroup_int("/sys/fs/cgroup/memory.high"),
            "cgroup_memory_current_bytes_at_capture": _cgroup_int("/sys/fs/cgroup/memory.current"),
            "cgroup_memory_swap_max_bytes": _cgroup_int("/sys/fs/cgroup/memory.swap.max"),
        },
        "process_limits": _process_limits(),
        "storage": {
            "working_root": _filesystem_identity(working_root),
            "temp_root": _filesystem_identity(temp_root),
            "root": _filesystem_identity("/"),
        },
        "temp_policy": {
            "tempdir": temp_root,
            "same_filesystem_as_working_root": os.stat(working_root).st_dev == os.stat(temp_root).st_dev,
        },
        "execution_constraints": {
            "max_worker_concurrency": 1,
            "scientific_run_parallelism": "SINGLE_PROCESS_SINGLE_WORKER",
            "required_min_free_bytes_before_run": int(required_min_free_bytes_before_run),
            "t1_external_artifact_limit_bytes": int(t1_external_artifact_limit_bytes),
            "minimum_temp_reserve_bytes": int(minimum_temp_reserve_bytes),
            "hard_memory_ceiling_source": "cgroup_v2_memory.max",
            "hard_memory_ceiling_bytes": _cgroup_int("/sys/fs/cgroup/memory.max"),
        },
        "authority_effect": "EXECUTION_GOVERNANCE_ONLY_SCIENTIFIC_DELTA_NONE",
    }
    payload["logical_sha256"] = logical_sha256(payload)
    return payload


def verify_frozen_execution_environment(
    observed: Mapping[str, Any],
    frozen: Mapping[str, Any],
) -> dict[str, Any]:
    if frozen.get("schema") != PROFILE_SCHEMA or observed.get("schema") != PROFILE_SCHEMA:
        raise ExecutionEnvironmentError("EXECUTION_ENV_PROFILE_SCHEMA_MISMATCH", "v1 profile required")
    checks: list[tuple[str, Any, Any]] = [
        ("os.system", observed["os"]["system"], frozen["os"]["system"]),
        ("os.machine", observed["os"]["machine"], frozen["os"]["machine"]),
        ("os.release", observed["os"]["release"], frozen["os"]["release"]),
        ("python.version", observed["python"]["version"], frozen["python"]["version"]),
        ("memory.cgroup_memory_max_bytes", observed["memory"]["cgroup_memory_max_bytes"], frozen["memory"]["cgroup_memory_max_bytes"]),
        ("memory.cgroup_memory_swap_max_bytes", observed["memory"]["cgroup_memory_swap_max_bytes"], frozen["memory"]["cgroup_memory_swap_max_bytes"]),
        ("memory.swap_total_bytes", observed["memory"]["swap_total_bytes"], frozen["memory"]["swap_total_bytes"]),
        ("concurrency.effective_cpu_quota_cores", observed["concurrency"]["effective_cpu_quota_cores"], frozen["concurrency"]["effective_cpu_quota_cores"]),
        ("concurrency.pids_max", observed["concurrency"]["pids_max"], frozen["concurrency"]["pids_max"]),
        ("storage.working_root.filesystem_type", observed["storage"]["working_root"]["filesystem_type"], frozen["storage"]["working_root"]["filesystem_type"]),
        ("storage.working_root.total_bytes", observed["storage"]["working_root"]["total_bytes"], frozen["storage"]["working_root"]["total_bytes"]),
        ("storage.temp_root.filesystem_type", observed["storage"]["temp_root"]["filesystem_type"], frozen["storage"]["temp_root"]["filesystem_type"]),
        ("storage.temp_root.total_bytes", observed["storage"]["temp_root"]["total_bytes"], frozen["storage"]["temp_root"]["total_bytes"]),
        ("temp_policy.same_filesystem_as_working_root", observed["temp_policy"]["same_filesystem_as_working_root"], frozen["temp_policy"]["same_filesystem_as_working_root"]),
        ("execution_constraints.hard_memory_ceiling_bytes", observed["execution_constraints"]["hard_memory_ceiling_bytes"], frozen["execution_constraints"]["hard_memory_ceiling_bytes"]),
        ("dependency_inventory.pip_freeze_line_count", observed["dependency_inventory"]["pip_freeze_line_count"], frozen["dependency_inventory"]["pip_freeze_line_count"]),
        ("dependency_inventory.pip_freeze_sha256", observed["dependency_inventory"]["pip_freeze_sha256"], frozen["dependency_inventory"]["pip_freeze_sha256"]),
    ]
    for name in RELEVANT_DEPENDENCIES:
        checks.append((f"dependencies.{name}", observed["dependencies"].get(name), frozen["dependencies"].get(name)))
    for limit_name, expected_limit in frozen.get("process_limits", {}).items():
        observed_limit = observed.get("process_limits", {}).get(limit_name)
        checks.append((f"process_limits.{limit_name}", observed_limit, expected_limit))
    failures = [name for name, actual, expected in checks if actual != expected]
    required_free = int(frozen["execution_constraints"]["required_min_free_bytes_before_run"])
    available = int(observed["storage"]["working_root"]["available_bytes"])
    if available < required_free:
        failures.append("storage.working_root.available_bytes")
    required_temp = int(frozen["execution_constraints"]["minimum_temp_reserve_bytes"])
    if int(observed["storage"]["temp_root"]["available_bytes"]) < required_temp:
        failures.append("storage.temp_root.available_bytes")
    if int(frozen["execution_constraints"]["max_worker_concurrency"]) != 1:
        failures.append("execution_constraints.max_worker_concurrency")
    if failures:
        raise ExecutionEnvironmentError(
            "EXECUTION_ENVIRONMENT_MISMATCH",
            ",".join(sorted(set(failures))),
        )
    result = {
        "schema": "ovc-srfdi-execution-environment-verification/v1",
        "status": "PASS",
        "profile_id": frozen["profile_id"],
        "profile_logical_sha256": frozen["logical_sha256"],
        "available_working_bytes": available,
        "available_temp_bytes": int(observed["storage"]["temp_root"]["available_bytes"]),
        "scientific_delta": "NONE",
        "authority_effect": "EXECUTION_GOVERNANCE_ONLY",
    }
    return {**result, "logical_sha256": logical_sha256(result)}


def load_frozen_profile(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    copy = dict(value)
    expected = copy.pop("logical_sha256", None)
    actual = logical_sha256(copy)
    if expected != actual:
        raise ExecutionEnvironmentError("EXECUTION_ENV_PROFILE_HASH_MISMATCH", actual)
    return value
