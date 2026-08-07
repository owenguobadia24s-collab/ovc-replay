from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
import json
import multiprocessing
import os
import platform
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Mapping

from .capacity import profile_fixture_capacity
from .serialization import logical_sha256, stable_id


ALLOWED_CHANGE_CLASSES = frozenset({
    "COMPUTE_ONLY_EQUIVALENT",
    "PHYSICAL_STORAGE_ONLY",
    "ORCHESTRATION_ONLY",
    "OBSERVABILITY_ONLY",
    "DEPENDENCY_CHANGE",
})
BLOCKING_CHANGE_CLASS = "POTENTIAL_SEMANTIC_CHANGE"
BRIDGE_DISPOSITIONS = frozenset({"PLAUSIBLE", "INDETERMINATE", "IMPLAUSIBLE"})
BRIDGE_REQUIRED_FIELDS = (
    "environment_fingerprint",
    "baseline_component_id",
    "candidate_component_id",
    "population",
    "backend",
    "before_wall_seconds",
    "after_wall_seconds",
    "before_cpu_seconds",
    "after_cpu_seconds",
    "before_peak_rss_bytes",
    "after_peak_rss_bytes",
    "before_external_bytes",
    "after_external_bytes",
    "storage_read_seconds",
    "storage_write_seconds",
    "cache_state",
    "logical_equivalence",
    "marginal_improvement_factor",
    "remaining_bottleneck",
    "bounded_forecast",
    "disposition",
)


class CapacityV2Error(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class H0IOProfile:
    payload_bytes: int
    write_seconds: float
    first_read_seconds: float
    second_read_seconds: float
    fsync_seconds: float
    rename_seconds: float
    write_mib_per_second: float
    first_read_mib_per_second: float
    second_read_mib_per_second: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "payload_bytes": self.payload_bytes,
            "write_seconds": self.write_seconds,
            "first_read_seconds": self.first_read_seconds,
            "second_read_seconds": self.second_read_seconds,
            "fsync_seconds": self.fsync_seconds,
            "rename_seconds": self.rename_seconds,
            "write_mib_per_second": self.write_mib_per_second,
            "first_read_mib_per_second": self.first_read_mib_per_second,
            "second_read_mib_per_second": self.second_read_mib_per_second,
        }


def classify_change(change_class: str) -> str:
    value = str(change_class).strip().upper()
    if value == BLOCKING_CHANGE_CLASS:
        raise CapacityV2Error("G8R_POTENTIAL_SEMANTIC_CHANGE", "semantic changes are outside G8R authority")
    if value not in ALLOWED_CHANGE_CLASSES:
        raise CapacityV2Error("G8R_UNKNOWN_CHANGE_CLASS", value)
    return value


def _read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _cpu_model() -> str:
    text = _read_text("/proc/cpuinfo")
    if text:
        for line in text.splitlines():
            if line.lower().startswith("model name") and ":" in line:
                return line.split(":", 1)[1].strip()
    return platform.processor() or platform.machine() or "UNKNOWN"


def _physical_core_count() -> int | None:
    text = _read_text("/proc/cpuinfo")
    if not text:
        return None
    physical: set[tuple[str, str]] = set()
    physical_id: str | None = None
    core_id: str | None = None
    for line in text.splitlines() + [""]:
        if not line.strip():
            if physical_id is not None and core_id is not None:
                physical.add((physical_id, core_id))
            physical_id = core_id = None
            continue
        key, _, value = line.partition(":")
        if key.strip() == "physical id":
            physical_id = value.strip()
        elif key.strip() == "core id":
            core_id = value.strip()
    return len(physical) or None


def _linux_meminfo() -> dict[str, int]:
    text = _read_text("/proc/meminfo")
    output: dict[str, int] = {}
    if text:
        for line in text.splitlines():
            key, _, raw = line.partition(":")
            parts = raw.strip().split()
            if not parts:
                continue
            try:
                value = int(parts[0])
            except ValueError:
                continue
            if len(parts) > 1 and parts[1].lower() == "kb":
                value *= 1024
            output[key] = value
    return output


def _filesystem_type(path: Path) -> str:
    text = _read_text("/proc/mounts")
    if not text:
        return "UNKNOWN"
    resolved = str(path.resolve())
    best_mount = ""
    best_type = "UNKNOWN"
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        mount = fields[1].replace("\\040", " ")
        if resolved == mount or resolved.startswith(mount.rstrip("/") + "/"):
            if len(mount) > len(best_mount):
                best_mount = mount
                best_type = fields[2]
    return best_type


def _numpy_identity() -> dict[str, Any]:
    try:
        version = metadata.version("numpy")
    except metadata.PackageNotFoundError:
        return {"present": False, "version": None, "admission_state": "CANDIDATE_UNADMITTED"}
    return {"present": True, "version": version, "admission_state": "CANDIDATE_UNADMITTED"}


def _io_profile(root: Path, *, payload_bytes: int = 4 * 1024 * 1024) -> H0IOProfile:
    if payload_bytes < 4096:
        raise CapacityV2Error("G8R_INVALID_IO_PROFILE", "payload_bytes must be at least 4096")
    root.mkdir(parents=True, exist_ok=True)
    payload = bytes((index % 251 for index in range(64 * 1024)))
    repeats, remainder = divmod(payload_bytes, len(payload))
    mib = payload_bytes / (1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="ovc-g8r-h0-", dir=root) as tmp:
        tmp_path = Path(tmp)
        staging = tmp_path / "h0.staging"
        complete = tmp_path / "h0.complete"
        start = time.perf_counter()
        fsync_total = 0.0
        with staging.open("wb") as handle:
            for _ in range(repeats):
                handle.write(payload)
            if remainder:
                handle.write(payload[:remainder])
            handle.flush()
            fsync_start = time.perf_counter()
            os.fsync(handle.fileno())
            fsync_total = time.perf_counter() - fsync_start
        write_seconds = time.perf_counter() - start
        rename_start = time.perf_counter()
        os.replace(staging, complete)
        rename_seconds = time.perf_counter() - rename_start

        read_start = time.perf_counter()
        with complete.open("rb") as handle:
            while handle.read(1024 * 1024):
                pass
        first_read_seconds = time.perf_counter() - read_start

        read_start = time.perf_counter()
        with complete.open("rb") as handle:
            while handle.read(1024 * 1024):
                pass
        second_read_seconds = time.perf_counter() - read_start

    return H0IOProfile(
        payload_bytes=payload_bytes,
        write_seconds=write_seconds,
        first_read_seconds=first_read_seconds,
        second_read_seconds=second_read_seconds,
        fsync_seconds=fsync_total,
        rename_seconds=rename_seconds,
        write_mib_per_second=mib / write_seconds if write_seconds else float("inf"),
        first_read_mib_per_second=mib / first_read_seconds if first_read_seconds else float("inf"),
        second_read_mib_per_second=mib / second_read_seconds if second_read_seconds else float("inf"),
    )


def capture_h0_environment(*, artifact_root: str | os.PathLike[str] | None = None, io_payload_bytes: int = 4 * 1024 * 1024) -> dict[str, Any]:
    root = Path(artifact_root) if artifact_root is not None else Path(tempfile.gettempdir())
    usage = shutil.disk_usage(root)
    mem = _linux_meminfo()
    os_identity = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }
    runtime = {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "process_start_method": multiprocessing.get_start_method(allow_none=True) or "DEFAULT",
    }
    cpu = {
        "model": _cpu_model(),
        "physical_cores": _physical_core_count(),
        "logical_threads": os.cpu_count(),
    }
    memory = {
        "installed_bytes": mem.get("MemTotal"),
        "available_bytes_at_capture": mem.get("MemAvailable"),
    }
    storage = {
        "filesystem_type": _filesystem_type(root),
        "total_bytes": usage.total,
        "free_bytes_at_capture": usage.free,
        "io": _io_profile(root, payload_bytes=io_payload_bytes).to_dict(),
    }
    backend = {"numpy": _numpy_identity()}
    identity_payload = {
        "os": os_identity,
        "runtime": runtime,
        "cpu": cpu,
        "memory_installed_bytes": memory["installed_bytes"],
        "storage_filesystem_type": storage["filesystem_type"],
        "storage_total_bytes": storage["total_bytes"],
        "candidate_backend": backend,
    }
    payload = {
        "schema": "ovc-srfdi-g8r-h0-environment/v1",
        "authority_state": "FIXTURE_LOCAL_CAPACITY_REMEDIATION_ONLY",
        "measurement_class": "MEASURED",
        "environment_fingerprint": stable_id("SRFD.H0.", identity_payload),
        "os": os_identity,
        "runtime": runtime,
        "cpu": cpu,
        "memory": memory,
        "storage": storage,
        "candidate_backend": backend,
        "hostname_in_identity": False,
        "local_path_in_identity": False,
        "june_market_records_read": False,
        "validation_consumed": False,
    }
    payload["logical_hash"] = logical_sha256(payload)
    return payload


def reference_component_profile() -> dict[str, Any]:
    receipt = profile_fixture_capacity(
        representation_population_count=64,
        pairwise_population_count=48,
        family_population_count=24,
        dimensions=5,
        reference_population_count=None,
    )
    return {
        "schema": "ovc-srfdi-g8r-reference-component-profile/v1",
        "reference_oracle": "CURRENT_JSON_REFERENCE",
        "measurement_class": "MEASURED",
        "receipt": receipt,
        "june_market_records_read": False,
        "validation_consumed": False,
        "logical_hash": logical_sha256(receipt),
    }


def feasibility_bridge_schema() -> dict[str, Any]:
    payload = {
        "schema": "ovc-srfdi-g8r-feasibility-bridge-schema/v1",
        "required_fields": list(BRIDGE_REQUIRED_FIELDS),
        "allowed_dispositions": sorted(BRIDGE_DISPOSITIONS),
        "no_multiplicative_speedup_claim": True,
        "mandatory_before_packet": "SRFDI-G8R-WP3",
        "operator_gate": "SRFDI-G8R-G2F",
    }
    return {**payload, "schema_id": stable_id("SRFD.G8R.BRIDGE.SCHEMA.", payload)}


def validate_feasibility_bridge_receipt(receipt: Mapping[str, Any]) -> None:
    missing = [field for field in BRIDGE_REQUIRED_FIELDS if field not in receipt]
    if missing:
        raise CapacityV2Error("G8R_BRIDGE_SCHEMA_FAILURE", ",".join(missing))
    if receipt["disposition"] not in BRIDGE_DISPOSITIONS:
        raise CapacityV2Error("G8R_BRIDGE_SCHEMA_FAILURE", "invalid disposition")
    if receipt["logical_equivalence"] is not True:
        raise CapacityV2Error("G8R_BRIDGE_EQUIVALENCE_FAILURE", "bridge candidate is not logically equivalent")
    before = float(receipt["before_wall_seconds"])
    after = float(receipt["after_wall_seconds"])
    if before <= 0 or after <= 0:
        raise CapacityV2Error("G8R_BRIDGE_SCHEMA_FAILURE", "wall times must be positive")
    measured_factor = before / after
    declared_factor = float(receipt["marginal_improvement_factor"])
    if abs(measured_factor - declared_factor) > max(1e-9, abs(measured_factor) * 1e-9):
        raise CapacityV2Error("G8R_BRIDGE_FACTOR_MISMATCH", "improvement factor must be measured before/after")


def render_h0_line(receipt: Mapping[str, Any]) -> str:
    return "SRFDI_G8R_H0=" + json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)


def render_reference_profile_line(receipt: Mapping[str, Any]) -> str:
    return "SRFDI_G8R_REFERENCE_PROFILE=" + json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)
