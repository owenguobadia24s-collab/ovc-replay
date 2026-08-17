from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping, Sequence

from ovc.research_operations.canonical import canonical_json_bytes

from .assurance import CapacityMeasurement


MEASUREMENT_SOURCE = "CANONICAL_LOGICAL_SYNTHETIC_WORKLOAD_BYTES"


def _canonical_size(value: Any) -> int:
    return len(canonical_json_bytes(value, trailing_newline=False))


def measure_synthetic_capacity_tier(tier: Mapping[str, Any]) -> tuple[CapacityMeasurement, dict[str, Any]]:
    tier_id = str(tier["tier_id"])
    candidate_count = int(tier["candidate_count"])
    surrogate_count = int(tier["surrogate_count"])
    representation_count = int(tier["representation_count"])
    time_partition_count = int(tier["time_partition_count"])
    context_partition_count = int(tier["context_partition_count"])
    boundary_count = int(tier["boundary_count"])

    if min(
        candidate_count,
        surrogate_count,
        representation_count,
        time_partition_count,
        context_partition_count,
        boundary_count,
    ) < 1:
        raise ValueError("synthetic capacity tiers require strictly positive dimensions")

    candidate_ids = [f"C{index:04d}" for index in range(candidate_count)]
    family_divisor = max(1, candidate_count // 4)
    components = {
        "candidate_family": [
            {"candidate_ref": candidate_ref, "family_ref": f"F{index % family_divisor:04d}"}
            for index, candidate_ref in enumerate(candidate_ids)
        ],
        "surrogate_work": [
            [candidate_ref, draw_index]
            for candidate_ref in candidate_ids
            for draw_index in range(surrogate_count)
        ],
        "representation_work": [
            [candidate_ref, representation_index]
            for candidate_ref in candidate_ids
            for representation_index in range(representation_count)
        ],
        "temporal_context_work": [
            [candidate_ref, time_index, context_index]
            for candidate_ref in candidate_ids
            for time_index in range(time_partition_count)
            for context_index in range(context_partition_count)
        ],
        "boundary_work": [
            [left_index, right_index]
            for left_index in range(boundary_count)
            for right_index in range(boundary_count)
        ],
    }
    component_bytes = {name: _canonical_size(value) for name, value in components.items()}
    artifact_bytes = sum(component_bytes.values())
    peak_memory_bytes = max(component_bytes.values())
    review_units = (
        candidate_count
        + candidate_count * representation_count
        + candidate_count * time_partition_count * context_partition_count
        + boundary_count
    )
    work_units = (
        candidate_count
        + candidate_count * surrogate_count
        + candidate_count * representation_count
        + candidate_count * time_partition_count * context_partition_count
        + boundary_count * boundary_count
    )
    measurement = CapacityMeasurement(
        tier_id=tier_id,
        candidate_count=candidate_count,
        surrogate_count=surrogate_count,
        representation_count=representation_count,
        time_partition_count=time_partition_count,
        context_partition_count=context_partition_count,
        boundary_count=boundary_count,
        artifact_bytes=artifact_bytes,
        peak_memory_bytes=peak_memory_bytes,
        review_units=review_units,
    )
    evidence = {
        **asdict(measurement),
        "work_units": work_units,
        "component_bytes": component_bytes,
        "measurement_source": MEASUREMENT_SOURCE,
        "scientific_effect": "NONE",
        "authority_effect": "NONE",
    }
    return measurement, evidence


def measure_synthetic_capacity_tiers(
    tiers: Sequence[Mapping[str, Any]],
) -> tuple[tuple[CapacityMeasurement, ...], tuple[dict[str, Any], ...]]:
    measurements = []
    evidence = []
    for tier in tiers:
        measurement, row = measure_synthetic_capacity_tier(tier)
        measurements.append(measurement)
        evidence.append(row)
    return tuple(measurements), tuple(evidence)
