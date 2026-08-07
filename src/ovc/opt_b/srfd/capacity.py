from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from itertools import combinations
import json
import math
import time
import tracemalloc
from typing import Any, Callable, Mapping, Sequence

from .distance import DistanceSpec, compute_distance
from .families import DistanceMatrix, FamilyMethodSpec, bounded_pam, hierarchical, medoid_star
from .orchestration import run_pipeline
from .representation import RepresentationPack, compile_representation
from .serialization import canonical_json_bytes, logical_sha256, stable_id

try:  # POSIX CI/operator-local environments. Kept optional for Windows compatibility.
    import resource as _resource
except ImportError:  # pragma: no cover - exercised on Windows operator machines.
    _resource = None

GIB = 1024 ** 3


class CapacityError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class CapacityBudget:
    max_runtime_seconds: float = 4 * 60 * 60
    max_peak_rss_bytes: int = 16 * GIB
    max_external_bytes: int = 10 * GIB


@dataclass(frozen=True)
class Projection:
    population_count: int
    pair_count: int
    representation_seconds: float
    pairwise_seconds: float
    pairwise_external_bytes: int
    family_method_seconds: Mapping[str, float]
    worst_family_method: str | None
    worst_family_method_seconds: float
    projected_runtime_seconds: float
    capacity_status: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def exact_pair_count(population_count: int) -> int:
    if population_count < 0:
        raise CapacityError("DIST_INVALID_PARAMETER", "population_count must be non-negative")
    return population_count * (population_count - 1) // 2


def _process_peak_rss_bytes() -> int | None:
    if _resource is None:
        return None
    usage = _resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB, macOS reports bytes. GitHub-hosted Linux is the measured CI target.
    if usage < 10_000_000:  # plausible KiB process maximum; convert to bytes.
        return int(usage * 1024)
    return int(usage)


def _timed(fn: Callable[[], Any]) -> tuple[Any, float, int]:
    tracemalloc.start()
    start = time.perf_counter()
    value = fn()
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return value, elapsed, peak


def synthetic_sources(population_count: int, *, dimensions: int = 5) -> list[dict[str, Any]]:
    if population_count < 1 or dimensions < 1:
        raise CapacityError("DIST_INVALID_PARAMETER", "positive population and dimensions required")
    output: list[dict[str, Any]] = []
    for index in range(population_count):
        structural = {
            f"d{dim}": format(Decimal(((index + 1) * (dim + 3)) % 101) / Decimal(100), "f")
            for dim in range(dimensions)
        }
        output.append({
            "record_id": f"FX.C2.{index:06d}",
            "first_valid_time": f"2026-01-{1 + (index % 28):02d}T{(index % 12) * 2:02d}:00:00Z",
            "structural": structural,
            "instrument": "FIXTURE",
            "side": "BID",
            "units": "DIMENSIONLESS",
            "clock": "2H_A_L",
            "representation_schema": "SRFD.FIXTURE.C2.v0_1",
            "source_quality": "COMPLETE",
        })
    return output


def _profile_representation(population_count: int, dimensions: int) -> dict[str, Any]:
    fields = tuple(f"d{dim}" for dim in range(dimensions))
    pack = RepresentationPack(
        "CAP.REP.RAW.v0_1", "SRFDI-R1", "R0", fields, "FIXTURE_SAME_DOMAIN_v0_1"
    )
    sources = synthetic_sources(population_count, dimensions=dimensions)

    def work() -> list[dict[str, Any]]:
        return [compile_representation(item, pack, source_population_id="SRFD.POP.CAPACITY.FIXTURE") for item in sources]

    outputs, elapsed, peak_alloc = _timed(work)
    serialized_bytes = sum(len(canonical_json_bytes(item)) for item in outputs)
    return {
        "population_count": population_count,
        "dimensions": dimensions,
        "elapsed_seconds": elapsed,
        "records_per_second": population_count / elapsed if elapsed else float("inf"),
        "bytes_per_record": serialized_bytes / population_count,
        "tracemalloc_peak_bytes": peak_alloc,
        "process_peak_rss_bytes": _process_peak_rss_bytes(),
        "output_hash": logical_sha256(outputs),
    }


def _fixture_representations(population_count: int, dimensions: int) -> list[dict[str, Any]]:
    fields = tuple(f"d{dim}" for dim in range(dimensions))
    pack = RepresentationPack("CAP.REP.RAW.v0_1", "SRFDI-R1", "R0", fields, "FIXTURE_SAME_DOMAIN_v0_1")
    return [compile_representation(item, pack, source_population_id="SRFD.POP.CAPACITY.FIXTURE") for item in synthetic_sources(population_count, dimensions=dimensions)]


def _profile_pairwise(population_count: int, dimensions: int) -> dict[str, Any]:
    records = _fixture_representations(population_count, dimensions)
    fields = tuple(f"d{dim}" for dim in range(dimensions))
    spec = DistanceSpec("CAP.DIST.L1.v0_1", "L1_TYPED", fields)

    def work() -> tuple[int, int, str]:
        pair_count = 0
        total_bytes = 0
        rolling_hashes: list[str] = []
        for left, right in combinations(records, 2):
            result = compute_distance(left, right, spec)
            pair_count += 1
            total_bytes += len(canonical_json_bytes(result))
            if pair_count <= 16 or pair_count % 257 == 0:
                rolling_hashes.append(result["pair_id"] + ":" + str(result["distance"]))
        return pair_count, total_bytes, logical_sha256(rolling_hashes)

    (pair_count, total_bytes, output_hash), elapsed, peak_alloc = _timed(work)
    expected = exact_pair_count(population_count)
    if pair_count != expected:
        raise CapacityError("QA_SCHEMA_FAILURE", "pairwise profiler did not enumerate exact population")
    return {
        "population_count": population_count,
        "dimensions": dimensions,
        "pair_count": pair_count,
        "elapsed_seconds": elapsed,
        "pairs_per_second": pair_count / elapsed if elapsed else float("inf"),
        "bytes_per_pair": total_bytes / pair_count if pair_count else 0.0,
        "tracemalloc_peak_bytes": peak_alloc,
        "process_peak_rss_bytes": _process_peak_rss_bytes(),
        "output_hash": output_hash,
        "sampling": "NONE_FULL_SYNTHETIC_PAIR_POPULATION",
        "approximation_state": "EXACT_SYNTHETIC_GOLDEN",
    }


def _family_matrix(population_count: int) -> DistanceMatrix:
    ids = [f"F{index:03d}" for index in range(population_count)]
    values: dict[str, str] = {}
    denominator = Decimal(max(1, population_count - 1))
    for left_index in range(population_count):
        for right_index in range(left_index + 1, population_count):
            values[f"{ids[left_index]}|{ids[right_index]}"] = format(
                Decimal(abs(left_index - right_index)) / denominator, "f"
            )
    return DistanceMatrix.from_pairs(ids, values)


def _profile_family_methods(population_count: int) -> dict[str, Any]:
    matrix = _family_matrix(population_count)
    specs_and_builders: list[tuple[str, int, Callable[[], Mapping[str, Any]]]] = [
        (
            "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
            3,
            lambda: medoid_star(matrix, FamilyMethodSpec("GREEDY_LEXICOGRAPHIC_MEDOID_STAR", "CAP", radius="0.08", minimum_support=2)),
        ),
        (
            "COMPLETE_LINKAGE",
            3,
            lambda: hierarchical(matrix, FamilyMethodSpec("COMPLETE_LINKAGE", "CAP", radius="0.08", minimum_support=2, linkage="complete")),
        ),
        (
            "AVERAGE_LINKAGE",
            3,
            lambda: hierarchical(matrix, FamilyMethodSpec("AVERAGE_LINKAGE", "CAP", radius="0.08", minimum_support=2, linkage="average")),
        ),
        (
            "BOUNDED_PAM",
            2,
            lambda: bounded_pam(matrix, FamilyMethodSpec("BOUNDED_PAM", "CAP", k=min(4, population_count), minimum_support=2, max_assignment_distance="0.20", max_iterations=8)),
        ),
    ]
    methods: dict[str, Any] = {}
    for method_id, exponent, builder in specs_and_builders:
        result, elapsed, peak_alloc = _timed(builder)
        methods[method_id] = {
            "elapsed_seconds": elapsed,
            "profile_population_count": population_count,
            "declared_projection_exponent": exponent,
            "family_count": len(result.get("families", [])),
            "residual_count": len(result.get("residual_ids", [])),
            "tracemalloc_peak_bytes": peak_alloc,
            "output_hash": logical_sha256(result),
        }
    return {"population_count": population_count, "methods": methods}


def _profile_restart() -> dict[str, Any]:
    stage_functions = {
        "population": lambda state: {**state, "p": len(state["records"])},
        "representation": lambda state: {**state, "r": state["p"] * 2},
        "compatibility": lambda state: {**state, "c": True},
        "distance": lambda state: {**state, "pairs": exact_pair_count(state["p"])},
        "family": lambda state: {**state, "families": []},
        "sensitivity": lambda state: {**state, "sensitivity": "UNRESOLVED"},
        "correspondence": lambda state: {**state, "correspondence": []},
        "invariant_core": lambda state: {**state, "cores": []},
        "stability": lambda state: {**state, "stability": "UNRESOLVED"},
        "failure_attribution": lambda state: {**state, "limiting_layer": "NONE"},
        "packet": lambda state: {**state, "packet": "READY"},
    }
    initial = {"records": [{"record_id": f"R{i:03d}"} for i in range(64)]}
    full, full_elapsed, _ = _timed(lambda: run_pipeline(initial, stage_functions))
    partial = run_pipeline(initial, stage_functions, stop_after="family")
    from .orchestration import CheckpointReceipt
    c = partial["last_checkpoint"]
    checkpoint = CheckpointReceipt(
        c["checkpoint_id"], c["completed_stage_index"], c["completed_stage"],
        c["state"], c["state_logical_hash"], tuple(c["stage_receipts"]), c["authority_state"]
    )
    resumed, resume_elapsed, _ = _timed(lambda: run_pipeline(initial, stage_functions, checkpoint=checkpoint))
    if full["state_logical_hash"] != resumed["state_logical_hash"]:
        raise CapacityError("CAP_RESTART_FAILURE", "restart output differs from uninterrupted output")
    return {
        "full_elapsed_seconds": full_elapsed,
        "resume_elapsed_seconds": resume_elapsed,
        "logical_equivalence": True,
        "byte_equivalence": canonical_json_bytes(full["state"]) == canonical_json_bytes(resumed["state"]),
    }


def project_capacity(receipt: Mapping[str, Any], population_count: int, budget: CapacityBudget) -> Projection:
    if population_count < 1:
        raise CapacityError("DIST_INVALID_PARAMETER", "projection population must be positive")
    representation = receipt["measurements"]["representation"]
    pairwise = receipt["measurements"]["pairwise"]
    family = receipt["measurements"]["family_methods"]
    pair_count = exact_pair_count(population_count)
    rep_seconds = population_count / float(representation["records_per_second"])
    pair_seconds = pair_count / float(pairwise["pairs_per_second"])
    pair_bytes = math.ceil(pair_count * float(pairwise["bytes_per_pair"]))
    projected_methods: dict[str, float] = {}
    for method_id, measured in family["methods"].items():
        profile_n = int(measured["profile_population_count"])
        exponent = int(measured["declared_projection_exponent"])
        scale = (population_count / profile_n) ** exponent
        projected_methods[method_id] = float(measured["elapsed_seconds"]) * scale
    worst_method = max(projected_methods, key=projected_methods.get) if projected_methods else None
    worst_method_seconds = projected_methods[worst_method] if worst_method else 0.0
    projected_runtime = rep_seconds + pair_seconds + worst_method_seconds
    reasons: list[str] = []
    if projected_runtime > budget.max_runtime_seconds:
        reasons.append("CAPACITY_EXCEEDED_RUNTIME")
    if pair_bytes > budget.max_external_bytes:
        reasons.append("CAPACITY_EXCEEDED_EXTERNAL_BYTES")
    measured_rss = receipt["measurements"].get("process_peak_rss_bytes")
    if measured_rss is not None and int(measured_rss) > budget.max_peak_rss_bytes:
        reasons.append("CAPACITY_EXCEEDED_MEASURED_RSS")
    status = "CAPACITY_EXCEEDED" if reasons else "WITHIN_PROVISIONAL_T0_PROJECTION"
    return Projection(
        population_count=population_count,
        pair_count=pair_count,
        representation_seconds=rep_seconds,
        pairwise_seconds=pair_seconds,
        pairwise_external_bytes=pair_bytes,
        family_method_seconds=dict(sorted(projected_methods.items())),
        worst_family_method=worst_method,
        worst_family_method_seconds=worst_method_seconds,
        projected_runtime_seconds=projected_runtime,
        capacity_status=status,
        reasons=tuple(reasons),
    )


def profile_fixture_capacity(
    *,
    representation_population_count: int = 256,
    pairwise_population_count: int = 128,
    family_population_count: int = 48,
    dimensions: int = 5,
    reference_population_count: int | None = None,
    reference_population_basis: Mapping[str, Any] | None = None,
    budget: CapacityBudget | None = None,
) -> dict[str, Any]:
    active_budget = budget or CapacityBudget()
    representation = _profile_representation(representation_population_count, dimensions)
    pairwise = _profile_pairwise(pairwise_population_count, dimensions)
    family = _profile_family_methods(family_population_count)
    restart = _profile_restart()
    rss_candidates = [item for item in (representation.get("process_peak_rss_bytes"), pairwise.get("process_peak_rss_bytes"), _process_peak_rss_bytes()) if item is not None]
    payload: dict[str, Any] = {
        "schema": "ovc-srfdi-capacity-receipt/v1",
        "object_type": "SRFDCapacityReceipt",
        "authority_state": "FIXTURE_ONLY",
        "mode": "SYNTHETIC_GOLDEN_FULL_ENUMERATION",
        "sampling": "NONE",
        "approximation_state": "EXACT_SYNTHETIC_GOLDEN",
        "budget": asdict(active_budget),
        "measurements": {
            "representation": representation,
            "pairwise": pairwise,
            "family_methods": family,
            "checkpoint_restart": restart,
            "process_peak_rss_bytes": max(rss_candidates) if rss_candidates else None,
        },
        "reference_population": {
            "population_count": reference_population_count,
            "basis": dict(reference_population_basis or {}),
            "binding_status": "NON_BINDING_CAPACITY_REFERENCE_ONLY" if reference_population_count is not None else "NOT_BOUND",
            "srfd_eligible_population": "NOT_BOUND_AT_WP8",
        },
        "june_market_records_read": False,
        "june_benchmark_executed": False,
        "validation_consumed": False,
        "canonical_method_selected": False,
    }
    if reference_population_count is not None:
        payload["reference_projection"] = project_capacity(payload, reference_population_count, active_budget).to_dict()
    identity = {
        "mode": payload["mode"],
        "sampling": payload["sampling"],
        "approximation_state": payload["approximation_state"],
        "profile_shapes": {
            "representation_population_count": representation_population_count,
            "pairwise_population_count": pairwise_population_count,
            "family_population_count": family_population_count,
            "dimensions": dimensions,
        },
        "budget": payload["budget"],
        "reference_population": payload["reference_population"],
    }
    payload["capacity_profile_id"] = stable_id("SRFD.CAPACITY.PROFILE.", identity)
    payload["measurement_logical_hash"] = logical_sha256(payload["measurements"])
    return payload


def render_measurement_line(receipt: Mapping[str, Any]) -> str:
    """Stable marker used to extract exact-head CI measurements into the G8 packet."""
    return "SRFDI_WP8_MEASUREMENT=" + json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)
