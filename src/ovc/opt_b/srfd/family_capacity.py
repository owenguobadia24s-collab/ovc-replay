from __future__ import annotations

from decimal import Decimal
from itertools import combinations
import json
import time
from typing import Any, Callable, Mapping, Sequence

from .families import DistanceMatrix, FamilyMethodSpec, bounded_pam, hierarchical, medoid_star
from .families_optimized import bounded_pam_optimized, hierarchical_optimized, medoid_star_optimized
from .serialization import logical_sha256


class FamilyCapacityError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def family_capacity_matrix(population_count: int) -> DistanceMatrix:
    if population_count < 2:
        raise FamilyCapacityError(
            "DIST_INVALID_PARAMETER", "family capacity population must be at least 2"
        )
    ids = [f"F{index:06d}" for index in range(population_count)]
    denominator = Decimal(population_count - 1)
    values: dict[str, str] = {}
    for left_index, right_index in combinations(range(population_count), 2):
        values[f"{ids[left_index]}|{ids[right_index]}"] = format(
            Decimal(abs(left_index - right_index)) / denominator,
            "f",
        )
    return DistanceMatrix.from_pairs(ids, values)


def _method_builders(
    matrix: DistanceMatrix,
) -> Sequence[
    tuple[
        str,
        Callable[[], Mapping[str, Any]],
        Callable[[], Mapping[str, Any]],
    ]
]:
    population_count = len(matrix.ids)
    medoid_spec = FamilyMethodSpec(
        "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
        "G8R.CAP",
        radius="0.08",
        minimum_support=2,
    )
    complete_spec = FamilyMethodSpec(
        "COMPLETE_LINKAGE",
        "G8R.CAP",
        radius="0.08",
        minimum_support=2,
        linkage="complete",
    )
    average_spec = FamilyMethodSpec(
        "AVERAGE_LINKAGE",
        "G8R.CAP",
        radius="0.08",
        minimum_support=2,
        linkage="average",
    )
    pam_spec = FamilyMethodSpec(
        "BOUNDED_PAM",
        "G8R.CAP",
        k=min(4, population_count),
        minimum_support=2,
        max_assignment_distance="0.20",
        max_iterations=8,
    )
    return (
        (
            medoid_spec.method_id,
            lambda: medoid_star(matrix, medoid_spec),
            lambda: medoid_star_optimized(matrix, medoid_spec),
        ),
        (
            complete_spec.method_id,
            lambda: hierarchical(matrix, complete_spec),
            lambda: hierarchical_optimized(matrix, complete_spec),
        ),
        (
            average_spec.method_id,
            lambda: hierarchical(matrix, average_spec),
            lambda: hierarchical_optimized(matrix, average_spec),
        ),
        (
            pam_spec.method_id,
            lambda: bounded_pam(matrix, pam_spec),
            lambda: bounded_pam_optimized(matrix, pam_spec),
        ),
    )


def _time_once(
    builder: Callable[[], Mapping[str, Any]],
) -> tuple[Mapping[str, Any], float]:
    start = time.perf_counter()
    result = builder()
    return result, time.perf_counter() - start


def profile_family_method_equivalence(
    population_counts: Sequence[int] = (48, 96),
) -> dict[str, Any]:
    if not population_counts or any(int(value) < 2 for value in population_counts):
        raise FamilyCapacityError(
            "DIST_INVALID_PARAMETER", "population counts must all be at least 2"
        )
    rungs: dict[str, Any] = {}
    for population_count in population_counts:
        matrix = family_capacity_matrix(int(population_count))
        methods: dict[str, Any] = {}
        for method_id, reference_builder, optimized_builder in _method_builders(matrix):
            reference, reference_seconds = _time_once(reference_builder)
            optimized, optimized_seconds = _time_once(optimized_builder)
            if reference != optimized:
                raise FamilyCapacityError(
                    "G8R_FAMILY_REFERENCE_EQUIVALENCE_FAILURE",
                    f"{method_id}@{population_count}",
                )
            methods[method_id] = {
                "reference_wall_seconds": reference_seconds,
                "optimized_wall_seconds": optimized_seconds,
                "speedup_factor": (
                    reference_seconds / optimized_seconds
                    if optimized_seconds
                    else float("inf")
                ),
                "logical_equivalence": True,
                "logical_hash": logical_sha256(reference),
                "family_count": len(reference.get("families", [])),
                "residual_count": len(reference.get("residual_ids", [])),
            }
        rungs[str(population_count)] = {
            "population_count": int(population_count),
            "methods": methods,
        }
    payload: dict[str, Any] = {
        "schema": "ovc-srfdi-g8r-family-method-capacity-profile/v1",
        "measurement_class": "MEASURED_FIXTURE_LOCAL_RUNTIME",
        "reference_oracle": "CURRENT_FAMILY_REFERENCE",
        "optimized_backend": "PYTHON_STDLIB_EXACT_FAMILY_OPTIMIZED",
        "population_counts": [int(value) for value in population_counts],
        "rungs": rungs,
        "scientific_delta": "NONE",
        "sampling": "NONE_FULL_SYNTHETIC_DISTANCE_SURFACE",
        "june_market_records_read": False,
        "validation_consumed": False,
        "numpy_backend": "CANDIDATE_UNADMITTED",
    }
    payload["logical_hash"] = logical_sha256(payload)
    return payload


def render_family_profile_line(receipt: Mapping[str, Any]) -> str:
    return "SRFDI_G8R_WP3_FAMILY_PROFILE=" + json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
