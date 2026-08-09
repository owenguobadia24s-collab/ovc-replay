from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from time import perf_counter, process_time
from typing import Any, Iterable, Mapping, Sequence

from .serialization import logical_sha256
from .telemetry import MetricValue, TelemetryReceipt, validate_metric_coverage


ALLOWED_SHAPES = frozenset({
    "APPROX_LINEAR_OBSERVED",
    "SUPER_LINEAR_OBSERVED",
    "KNOWN_QUADRATIC_WORK_COUNT",
    "FIXED_OVERHEAD_DOMINANT",
    "UNRESOLVED",
})


@dataclass(frozen=True)
class ScalingCase:
    case_id: str
    n: int
    capacity_tier: str
    scientific_pack_id: str

    def __post_init__(self) -> None:
        if self.n <= 1:
            raise ValueError("scaling N must exceed one")
        if not self.case_id or not self.scientific_pack_id:
            raise ValueError("scaling case identity required")


@dataclass(frozen=True)
class ScalingObservation:
    case_id: str
    n: int
    scientific_hash: str
    pair_count: int
    configuration_count: int
    artifact_bytes: int
    no_cache_work_units: int
    cache_work_units: int
    cache_work_units_avoided: int
    checkpoint_bytes: int
    checkpoint_overhead_seconds: float
    restart_recovery_seconds: float
    wall_seconds: float
    cpu_seconds: float
    telemetry: TelemetryReceipt

    def deterministic_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "n": self.n,
            "scientific_hash": self.scientific_hash,
            "pair_count": self.pair_count,
            "configuration_count": self.configuration_count,
            "artifact_bytes": self.artifact_bytes,
            "no_cache_work_units": self.no_cache_work_units,
            "cache_work_units": self.cache_work_units,
            "cache_work_units_avoided": self.cache_work_units_avoided,
            "checkpoint_bytes": self.checkpoint_bytes,
        }


def default_scaling_ladder() -> tuple[ScalingCase, ...]:
    return (
        ScalingCase("MICRO", 8, "MICRO", "IROF.WP10.SCIENTIFIC_PACK.v0_1"),
        ScalingCase("SMALL", 16, "SMALL", "IROF.WP10.SCIENTIFIC_PACK.v0_1"),
        ScalingCase("MEDIUM", 32, "MEDIUM", "IROF.WP10.SCIENTIFIC_PACK.v0_1"),
        ScalingCase("LARGE_FIXTURE", 64, "LARGE", "IROF.WP10.SCIENTIFIC_PACK.v0_1"),
    )


def _objects(n: int, scientific_pack_id: str) -> tuple[str, ...]:
    return tuple(
        logical_sha256({"pack": scientific_pack_id, "index": index, "value": index % 7})
        for index in range(n)
    )


def _pair_surface(objects: Sequence[str], *, cache: dict[tuple[str, str], str] | None = None) -> tuple[tuple[str, ...], int, int]:
    output: list[str] = []
    work_units = 0
    hits = 0
    for left_index in range(len(objects)):
        left = objects[left_index]
        for right_index in range(left_index + 1, len(objects)):
            right = objects[right_index]
            key = (left, right)
            if cache is not None and key in cache:
                output.append(cache[key])
                hits += 1
                continue
            value = sha256(f"{left}|{right}".encode("utf-8")).hexdigest()
            work_units += 1
            if cache is not None:
                cache[key] = value
            output.append(value)
    return tuple(output), work_units, hits


def run_scaling_case(case: ScalingCase) -> ScalingObservation:
    start_wall = perf_counter()
    start_cpu = process_time()
    objects = _objects(case.n, case.scientific_pack_id)

    no_cache_pairs, no_cache_work, _ = _pair_surface(objects)
    cache: dict[tuple[str, str], str] = {}
    warm_pairs, warm_work, _ = _pair_surface(objects, cache=cache)
    cached_pairs, cached_work, cache_hits = _pair_surface(objects, cache=cache)
    if no_cache_pairs != warm_pairs or no_cache_pairs != cached_pairs:
        raise RuntimeError("IROF_WP10_CACHE_CHANGED_SCIENTIFIC_OUTPUT")

    checkpoint_start = perf_counter()
    checkpoint_payload = json.dumps(
        {"case_id": case.case_id, "completed_pairs": len(no_cache_pairs), "scientific_pack_id": case.scientific_pack_id},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    checkpoint_overhead = perf_counter() - checkpoint_start

    restart_start = perf_counter()
    checkpoint_loaded = json.loads(checkpoint_payload.decode("utf-8"))
    if checkpoint_loaded["completed_pairs"] != len(no_cache_pairs):
        raise RuntimeError("IROF_WP10_CHECKPOINT_RESTART_MISMATCH")
    restart_recovery = perf_counter() - restart_start

    scientific_payload = {
        "scientific_pack_id": case.scientific_pack_id,
        "n": case.n,
        "object_hashes": objects,
        "pair_hashes": no_cache_pairs,
    }
    scientific_hash = logical_sha256(scientific_payload)
    artifact_bytes = len(json.dumps(scientific_payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    wall_seconds = perf_counter() - start_wall
    cpu_seconds = process_time() - start_cpu
    pair_count = case.n * (case.n - 1) // 2

    metrics = (
        MetricValue("wall_seconds", wall_seconds, "seconds"),
        MetricValue("cpu_seconds", cpu_seconds, "seconds"),
        MetricValue("core_seconds", cpu_seconds, "core_seconds"),
        MetricValue("peak_rss_bytes", None, "bytes", availability="UNAVAILABLE", reason_code="PORTABLE_RSS_NOT_MEASURED"),
        MetricValue("worker_count", 1, "workers"),
        MetricValue("bytes_read", 0, "bytes"),
        MetricValue("bytes_written", artifact_bytes, "bytes"),
        MetricValue("persistent_bytes", artifact_bytes, "bytes"),
        MetricValue("temporary_bytes", len(checkpoint_payload), "bytes"),
        MetricValue("object_count", case.n, "objects"),
        MetricValue("pair_count", pair_count, "pairs"),
        MetricValue("tile_count", 1, "tiles"),
        MetricValue("configuration_count", 1, "configurations"),
        MetricValue("throughput_per_second", pair_count / wall_seconds if wall_seconds > 0 else 0.0, "pairs_per_second"),
        MetricValue("cache_hit_count", cache_hits, "hits"),
        MetricValue("cache_miss_count", warm_work, "misses"),
        MetricValue("restart_count", 1, "restarts"),
    )
    telemetry = TelemetryReceipt(
        run_id=f"IROF.WP10.{case.case_id}",
        stage_id="PAIRWISE_SYNTHETIC_CHARACTERIZATION",
        metrics=metrics,
        warnings=("PEAK_RSS_UNAVAILABLE_PORTABLY", "PARALLELISM_EFFICIENCY_NOT_MEASURED_SINGLE_WORKER"),
        capacity_status="COMPLETE",
        scientific_effect="NONE",
    )
    validate_metric_coverage(telemetry)
    return ScalingObservation(
        case_id=case.case_id,
        n=case.n,
        scientific_hash=scientific_hash,
        pair_count=pair_count,
        configuration_count=1,
        artifact_bytes=artifact_bytes,
        no_cache_work_units=no_cache_work,
        cache_work_units=cached_work,
        cache_work_units_avoided=no_cache_work - cached_work,
        checkpoint_bytes=len(checkpoint_payload),
        checkpoint_overhead_seconds=checkpoint_overhead,
        restart_recovery_seconds=restart_recovery,
        wall_seconds=wall_seconds,
        cpu_seconds=cpu_seconds,
        telemetry=telemetry,
    )


def run_scaling_ladder(cases: Iterable[ScalingCase] | None = None) -> tuple[ScalingObservation, ...]:
    selected = tuple(cases or default_scaling_ladder())
    if len(selected) < 4:
        raise ValueError("WP10 requires MICRO plus at least three increasing N values")
    ns = tuple(item.n for item in selected)
    if tuple(sorted(ns)) != ns or len(set(ns)) != len(ns):
        raise ValueError("scaling N values must be strictly increasing")
    packs = {item.scientific_pack_id for item in selected}
    if len(packs) != 1:
        raise ValueError("scientific pack must remain identical across scaling ladder")
    return tuple(run_scaling_case(item) for item in selected)


def classify_shape(observations: Sequence[ScalingObservation], *, metric: str) -> str:
    if not observations:
        return "UNRESOLVED"
    if metric == "pair_count":
        expected = [item.n * (item.n - 1) // 2 for item in observations]
        if [item.pair_count for item in observations] == expected:
            return "KNOWN_QUADRATIC_WORK_COUNT"
        return "UNRESOLVED"
    values = [float(getattr(item, metric)) for item in observations]
    if len(values) < 3 or any(value <= 0 for value in values):
        return "UNRESOLVED"
    ns = [item.n for item in observations]
    normalized = [value / n for value, n in zip(values, ns)]
    spread = max(normalized) / min(normalized)
    if spread <= 1.5:
        return "APPROX_LINEAR_OBSERVED"
    if values[-1] / values[0] < 1.5 and ns[-1] / ns[0] >= 4:
        return "FIXED_OVERHEAD_DOMINANT"
    if values[-1] / values[0] > ns[-1] / ns[0] * 1.5:
        return "SUPER_LINEAR_OBSERVED"
    return "UNRESOLVED"


def characterize_ladder(observations: Sequence[ScalingObservation]) -> dict[str, Any]:
    deterministic_rows = [item.deterministic_dict() for item in observations]
    return {
        "schema": "ovc-irof-wp10-characterization/v0.1",
        "case_ids": [item.case_id for item in observations],
        "n_values": [item.n for item in observations],
        "scientific_pack_ids": ["IROF.WP10.SCIENTIFIC_PACK.v0_1"],
        "deterministic_rows": deterministic_rows,
        "shape": {
            "pair_count": classify_shape(observations, metric="pair_count"),
            "wall_seconds": classify_shape(observations, metric="wall_seconds"),
            "cpu_seconds": classify_shape(observations, metric="cpu_seconds"),
        },
        "measurement_availability": {
            "wall_seconds": "AVAILABLE_RUNTIME_MEASURED",
            "cpu_seconds": "AVAILABLE_RUNTIME_MEASURED",
            "peak_rss_bytes": "UNAVAILABLE_PORTABLY",
            "parallelism_efficiency": "NOT_APPLICABLE_SINGLE_WORKER_CHARACTERIZATION",
        },
        "scientific_effect": "NONE",
    }
