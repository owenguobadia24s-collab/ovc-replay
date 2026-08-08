from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

try:
    import resource as _resource
except ImportError:  # pragma: no cover
    _resource = None

from .capacity import synthetic_sources
from .capacity_v2 import capture_h0_environment
from .distance import DistanceSpec
from .distance_optimized import batch_compute_prepared, deterministic_parallel_tiles, prepare_records
from .distance_surface import TileHeader, read_exact_tile, write_exact_tile
from .families import DistanceMatrix, FamilyMethodSpec
from .families_optimized import bounded_pam_optimized, hierarchical_optimized, medoid_star_optimized
from .family_capacity import family_capacity_matrix
from .pair_index import exact_pair_count
from .representation import RepresentationPack, compile_representation
from .semantic_cache import TileCompletionLedger
from .serialization import logical_sha256


WP6_RUNGS = (64, 128, 256, 512, 1024)
T0 = {"max_wall_seconds": 14_400.0, "max_peak_rss_bytes": 16 * 1024**3, "max_external_bytes": 10 * 1024**3}
T1 = {"max_wall_seconds": 86_400.0, "max_peak_rss_bytes": 32 * 1024**3, "max_external_bytes": 100 * 1024**3}
REFERENCE_N = 8_598
METHOD_IDS = (
    "AVERAGE_LINKAGE",
    "BOUNDED_PAM",
    "COMPLETE_LINKAGE",
    "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
)


class WP6CapacityError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _peak_rss_bytes() -> int | None:
    if _resource is None:
        return None
    value = _resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss
    if value < 10_000_000:
        return int(value * 1024)
    return int(value)


def _timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    start = time.perf_counter()
    value = fn()
    return value, time.perf_counter() - start


def _representation_pack(dimensions: int) -> RepresentationPack:
    return RepresentationPack(
        "G8R.WP6.REP.RAW.v0_1",
        "SRFDI-R1",
        "R0",
        tuple(f"d{index}" for index in range(dimensions)),
        "FIXTURE_SAME_DOMAIN_v0_1",
    )


def _representations(population_count: int, dimensions: int) -> list[dict[str, Any]]:
    pack = _representation_pack(dimensions)
    return [
        compile_representation(
            item,
            pack,
            source_population_id="SRFD.G8R.WP6.SYNTHETIC",
        )
        for item in synthetic_sources(population_count, dimensions=dimensions)
    ]


def _digest_distance_results(results: Sequence[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for result in results:
        digest.update(str(result.get("pair_id", "")).encode("utf-8"))
        digest.update(b"|")
        digest.update(str(result.get("status", "")).encode("utf-8"))
        digest.update(b"|")
        digest.update(str(result.get("distance", "")).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _profile_representation(population_count: int, dimensions: int) -> dict[str, Any]:
    sources = synthetic_sources(population_count, dimensions=dimensions)
    pack = _representation_pack(dimensions)
    outputs, elapsed = _timed(
        lambda: [
            compile_representation(
                item,
                pack,
                source_population_id="SRFD.G8R.WP6.SYNTHETIC",
            )
            for item in sources
        ]
    )
    return {
        "population_count": population_count,
        "dimensions": dimensions,
        "wall_seconds": elapsed,
        "records_per_second": population_count / elapsed if elapsed else None,
        "output_hash": logical_sha256(outputs),
        "measurement_class": "MEASURED",
        "process_peak_rss_bytes": _peak_rss_bytes(),
    }


def _profile_distance(population_count: int, dimensions: int) -> dict[str, Any]:
    records = _representations(population_count, dimensions)
    spec = DistanceSpec(
        "G8R.WP6.DIST.L1.v0_1",
        "L1_TYPED",
        tuple(f"d{index}" for index in range(dimensions)),
        precision_places=8,
    )
    prepared, prepare_seconds = _timed(lambda: prepare_records(records, spec))
    del prepared
    results, distance_seconds = _timed(lambda: batch_compute_prepared(records, spec))
    pair_count = exact_pair_count(population_count)
    if len(results) != pair_count:
        raise WP6CapacityError("QA_PAIR_COUNT_MISMATCH", f"{len(results)}!={pair_count}")
    digest = _digest_distance_results(results)
    return {
        "population_count": population_count,
        "dimensions": dimensions,
        "pair_count": pair_count,
        "prepare_seconds": prepare_seconds,
        "distance_compute_seconds": distance_seconds,
        "pairs_per_second": pair_count / distance_seconds if distance_seconds else None,
        "compact_payload_bytes": pair_count * 8,
        "compact_payload_bytes_per_pair": 8,
        "logical_output_digest": digest,
        "measurement_class": "MEASURED",
        "sampling": "NONE_FULL_SYNTHETIC_PAIR_POPULATION",
        "process_peak_rss_bytes": _peak_rss_bytes(),
    }


def _family_builders(matrix: DistanceMatrix) -> dict[str, Callable[[], Mapping[str, Any]]]:
    n = len(matrix.ids)
    medoid_spec = FamilyMethodSpec(
        "GREEDY_LEXICOGRAPHIC_MEDOID_STAR", "G8R.WP6", radius="0.08", minimum_support=2
    )
    complete_spec = FamilyMethodSpec(
        "COMPLETE_LINKAGE", "G8R.WP6", radius="0.08", minimum_support=2, linkage="complete"
    )
    average_spec = FamilyMethodSpec(
        "AVERAGE_LINKAGE", "G8R.WP6", radius="0.08", minimum_support=2, linkage="average"
    )
    pam_spec = FamilyMethodSpec(
        "BOUNDED_PAM",
        "G8R.WP6",
        k=min(4, n),
        minimum_support=2,
        max_assignment_distance="0.20",
        max_iterations=8,
    )
    return {
        "GREEDY_LEXICOGRAPHIC_MEDOID_STAR": lambda: medoid_star_optimized(matrix, medoid_spec),
        "COMPLETE_LINKAGE": lambda: hierarchical_optimized(matrix, complete_spec),
        "AVERAGE_LINKAGE": lambda: hierarchical_optimized(matrix, average_spec),
        "BOUNDED_PAM": lambda: bounded_pam_optimized(matrix, pam_spec),
    }


def _profile_family(population_count: int) -> dict[str, Any]:
    matrix, matrix_seconds = _timed(lambda: family_capacity_matrix(population_count))
    methods: dict[str, Any] = {}
    for method_id, builder in _family_builders(matrix).items():
        output, elapsed = _timed(builder)
        methods[method_id] = {
            "wall_seconds": elapsed,
            "logical_hash": logical_sha256(output),
            "family_count": len(output.get("families", [])),
            "residual_count": len(output.get("residual_ids", [])),
            "measurement_class": "MEASURED",
        }
    return {
        "population_count": population_count,
        "distance_matrix_build_seconds": matrix_seconds,
        "methods": methods,
        "process_peak_rss_bytes": _peak_rss_bytes(),
        "measurement_class": "MEASURED",
    }


def _worker_sweep(population_count: int = 256, dimensions: int = 5) -> dict[str, Any]:
    records = _representations(population_count, dimensions)
    spec = DistanceSpec(
        "G8R.WP6.WORKER.L1.v0_1",
        "L1_TYPED",
        tuple(f"d{index}" for index in range(dimensions)),
        precision_places=8,
    )
    pair_count = exact_pair_count(population_count)
    rows: list[dict[str, Any]] = []
    baseline_digest: str | None = None
    for workers in (1, 2, 4):
        results, elapsed = _timed(
            lambda workers=workers: deterministic_parallel_tiles(
                records,
                spec,
                tile_pair_count=8_192,
                worker_count=workers,
            )
        )
        digest = _digest_distance_results(results)
        if baseline_digest is None:
            baseline_digest = digest
        elif digest != baseline_digest:
            raise WP6CapacityError("QA_PARALLEL_DETERMINISM_FAILURE", str(workers))
        rows.append(
            {
                "worker_count": workers,
                "wall_seconds": elapsed,
                "pairs_per_second": pair_count / elapsed if elapsed else None,
                "logical_output_digest": digest,
                "process_peak_rss_bytes": _peak_rss_bytes(),
            }
        )
    best = min(rows, key=lambda row: (row["wall_seconds"], row["worker_count"]))
    return {
        "population_count": population_count,
        "pair_count": pair_count,
        "tile_pair_count": 8_192,
        "rows": rows,
        "best_measured_worker_count": best["worker_count"],
        "measurement_class": "MEASURED",
        "logical_equivalence": True,
    }


def _storage_restart_profile(pair_count: int = 256_000) -> dict[str, Any]:
    coefficients = tuple((index % 100_000_000) for index in range(pair_count))
    header = TileHeader(
        format_version="1",
        endian="big",
        coefficient_width=8,
        precision_places=8,
        population_hash="WP6.POP",
        domain_hash="WP6.DOMAIN",
        distance_spec_hash="WP6.DIST",
        k_start=0,
        k_end=pair_count,
        expected_count=pair_count,
    )
    with tempfile.TemporaryDirectory(prefix="ovc-srfdi-g8r-wp6-") as tmp:
        path = Path(tmp) / "tile.bin"
        receipt, write_seconds = _timed(lambda: write_exact_tile(path, header, coefficients))
        (_, restored), read_seconds = _timed(lambda: read_exact_tile(path, receipt.to_dict()))
        if restored != coefficients:
            raise WP6CapacityError("QA_RESTART_EQUIVALENCE_FAILURE", "tile payload mismatch")
        ledger = TileCompletionLedger()
        ledger.register_complete("WP6.TILE", content_hash=receipt.content_hash, attempt_id="A1")
        reuse_start = time.perf_counter()
        should_compute = ledger.should_compute("WP6.TILE", expected_hash=receipt.content_hash)
        reuse_check_seconds = time.perf_counter() - reuse_start
        if should_compute:
            raise WP6CapacityError("QA_RESTART_RECOMPUTE_FAILURE", "verified complete tile selected for recompute")
        payload_bytes = pair_count * 8
        return {
            "pair_count": pair_count,
            "payload_bytes": payload_bytes,
            "bytes_per_pair": 8,
            "write_seconds": write_seconds,
            "read_seconds": read_seconds,
            "write_mib_per_second": (payload_bytes / 1024**2) / write_seconds if write_seconds else None,
            "read_mib_per_second": (payload_bytes / 1024**2) / read_seconds if read_seconds else None,
            "restart_reuse_check_seconds": reuse_check_seconds,
            "verified_complete_tile_recomputed": False,
            "content_hash": receipt.content_hash,
            "measurement_class": "MEASURED",
        }


def _adjacent_slopes(points: Sequence[tuple[int, float]]) -> list[float]:
    slopes: list[float] = []
    for (n0, t0), (n1, t1) in zip(points, points[1:]):
        if n0 > 0 and n1 > n0 and t0 > 0 and t1 > 0:
            slopes.append(math.log(t1 / t0) / math.log(n1 / n0))
    return slopes


def _project_power(points: Sequence[tuple[int, float]], target_n: int) -> dict[str, Any]:
    if len(points) < 2:
        raise WP6CapacityError("CAPACITY_UNRESOLVED", "at least two measured points required")
    slopes = _adjacent_slopes(points)
    if not slopes:
        raise WP6CapacityError("CAPACITY_UNRESOLVED", "no valid adjacent slopes")
    slope = max(slopes)
    last_n, last_time = points[-1]
    seconds = last_time * (target_n / last_n) ** slope
    return {
        "seconds": seconds,
        "observed_adjacent_slopes": slopes,
        "conservative_observed_slope": slope,
        "anchor_n": last_n,
        "anchor_seconds": last_time,
        "measurement_class": "EXTRAPOLATED",
    }


def _capacity_status(seconds: float, peak_rss_bytes: int, external_bytes: int) -> str:
    if seconds <= T0["max_wall_seconds"] and peak_rss_bytes <= T0["max_peak_rss_bytes"] and external_bytes <= T0["max_external_bytes"]:
        return "SUPPORTED_T0"
    if seconds <= T1["max_wall_seconds"] and peak_rss_bytes <= T1["max_peak_rss_bytes"] and external_bytes <= T1["max_external_bytes"]:
        return "SUPPORTED_T1"
    return "REQUIRES_SEPARATE_CAPACITY_TIER"


def build_wp6_projection(rungs: Mapping[str, Any], storage: Mapping[str, Any]) -> dict[str, Any]:
    ordered = [rungs[str(n)] for n in WP6_RUNGS]
    representation_points = [(row["population_count"], row["representation"]["wall_seconds"]) for row in ordered]
    representation_projection = _project_power(representation_points, REFERENCE_N)

    distance_points = [(row["population_count"], row["distance"]["distance_compute_seconds"]) for row in ordered]
    distance_projection = _project_power(distance_points, REFERENCE_N)

    family_projection: dict[str, Any] = {}
    for method_id in METHOD_IDS:
        points = [(row["population_count"], row["family"]["methods"][method_id]["wall_seconds"]) for row in ordered]
        family_projection[method_id] = _project_power(points, REFERENCE_N)

    target_pairs = exact_pair_count(REFERENCE_N)
    payload_bytes = target_pairs * int(storage["bytes_per_pair"])
    measured_storage_throughput = float(storage["write_mib_per_second"])
    storage_seconds = (payload_bytes / 1024**2) / measured_storage_throughput
    method_sum = sum(item["seconds"] for item in family_projection.values())
    full_dag_seconds = representation_projection["seconds"] + distance_projection["seconds"] + storage_seconds + method_sum
    peak_rss = max(
        int(row[section].get("process_peak_rss_bytes") or 0)
        for row in ordered
        for section in ("representation", "distance", "family")
    )
    external_bytes = math.ceil(payload_bytes * 1.05)
    overall_status = _capacity_status(full_dag_seconds, peak_rss, external_bytes)
    method_statuses = {
        method_id: _capacity_status(item["seconds"], peak_rss, external_bytes)
        for method_id, item in family_projection.items()
    }
    return {
        "reference_population": {
            "population_count": REFERENCE_N,
            "pair_count": target_pairs,
            "binding_status": "NON_BINDING_CAPACITY_REFERENCE_ONLY",
            "qualification": "Existing C2-state reference only; not frozen SRFD or June population.",
        },
        "representation": representation_projection,
        "distance": distance_projection,
        "family_methods": family_projection,
        "storage": {
            "compact_payload_bytes": payload_bytes,
            "external_bytes_with_5pct_manifest_staging_reserve": external_bytes,
            "projected_write_seconds": storage_seconds,
            "measurement_basis": "MEASURED_WP6_EXACT_TILE_WRITE_THROUGHPUT",
            "measurement_class": "EXTRAPOLATED",
        },
        "full_required_dag": {
            "projected_wall_seconds_serial_conservative": full_dag_seconds,
            "projected_wall_hours_serial_conservative": full_dag_seconds / 3600,
            "method_seconds_sum": method_sum,
            "cache_reuse_assumed": False,
            "parallel_speedup_assumed": False,
            "measurement_class": "EXTRAPOLATED",
            "capacity_status": overall_status,
        },
        "method_capacity_statuses": method_statuses,
        "peak_measured_process_rss_bytes": peak_rss,
        "t0": dict(T0),
        "t1": dict(T1),
    }


def profile_wp6_capacity(population_counts: Sequence[int] = WP6_RUNGS, *, dimensions: int = 5) -> dict[str, Any]:
    normalized = tuple(int(value) for value in population_counts)
    if normalized != WP6_RUNGS:
        raise WP6CapacityError("G8R_WP6_RUNG_SET_MISMATCH", str(normalized))
    h0 = capture_h0_environment(io_payload_bytes=4 * 1024 * 1024)
    rungs: dict[str, Any] = {}
    for population_count in normalized:
        representation = _profile_representation(population_count, dimensions)
        distance = _profile_distance(population_count, dimensions)
        family = _profile_family(population_count)
        rungs[str(population_count)] = {
            "population_count": population_count,
            "representation": representation,
            "distance": distance,
            "family": family,
        }
    workers = _worker_sweep()
    storage = _storage_restart_profile()
    projection = build_wp6_projection(rungs, storage)
    payload: dict[str, Any] = {
        "schema": "ovc-srfdi-g8r-wp6-multi-n-capacity-profile/v1",
        "programme_id": "OVC-SRFD-BENCHMARK-v0.1",
        "subprogramme_id": "OVC-SRFDI-G8R-v0.2",
        "packet_id": "SRFDI-G8R-WP6",
        "measurement_class": "MEASURED_MULTI_N_WITH_EXPLICIT_EXTRAPOLATION",
        "environment": h0,
        "population_counts": list(normalized),
        "rungs": rungs,
        "worker_sweep": workers,
        "storage_restart": storage,
        "projection": projection,
        "backend": {
            "distance": "PYTHON_STDLIB_EXACT",
            "family": "PYTHON_STDLIB_EXACT_FAMILY_OPTIMIZED",
            "numpy": "CANDIDATE_UNADMITTED",
        },
        "sampling": "NONE_ON_DECLARED_SYNTHETIC_RUNG_POPULATIONS",
        "scientific_delta": "NONE",
        "june_market_records_read": False,
        "validation_consumed": False,
        "wp9": "DENIED",
        "pr_371": "PRESERVE_DO_NOT_MERGE",
    }
    payload["logical_hash"] = logical_sha256(payload)
    return payload


def render_wp6_profile_line(receipt: Mapping[str, Any]) -> str:
    return "SRFDI_G8R_WP6_CAPACITY_PROFILE=" + json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
