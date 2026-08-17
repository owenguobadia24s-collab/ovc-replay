from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict
from typing import Any, Mapping, Sequence

from ovc.research_operations.canonical import canonical_json_bytes

from .assurance import CapacityMeasurement


MEASUREMENT_SOURCE = "LINUX_RUSAGE_RU_MAXRSS_FRESH_SUBPROCESS"
PEAK_MEMORY_QUANTITY = "PROCESS_PEAK_RESIDENT_SET_SIZE_BYTES"
PEAK_MEMORY_SCOPE = "FRESH_PYTHON_PROCESS_FROM_INTERPRETER_START_THROUGH_SYNTHETIC_WORKLOAD_COMPLETION"


def _canonical_size(value: Any) -> int:
    return len(canonical_json_bytes(value, trailing_newline=False))


def _validated_dimensions(tier: Mapping[str, Any]) -> tuple[str, int, int, int, int, int, int]:
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
    return (
        tier_id,
        candidate_count,
        surrogate_count,
        representation_count,
        time_partition_count,
        context_partition_count,
        boundary_count,
    )


def _build_synthetic_components(tier: Mapping[str, Any]) -> dict[str, Any]:
    (
        _tier_id,
        candidate_count,
        surrogate_count,
        representation_count,
        time_partition_count,
        context_partition_count,
        boundary_count,
    ) = _validated_dimensions(tier)
    candidate_ids = [f"C{index:04d}" for index in range(candidate_count)]
    family_divisor = max(1, candidate_count // 4)
    return {
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


def _peak_rss_child_output(tier: Mapping[str, Any]) -> dict[str, Any]:
    if not sys.platform.startswith("linux"):
        raise RuntimeError("PRSC_PEAK_RSS_REQUIRES_PINNED_LINUX_EXECUTION_ENVIRONMENT")
    import resource

    components = _build_synthetic_components(tier)
    component_bytes = {name: _canonical_size(value) for name, value in components.items()}
    peak_kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if peak_kib < 1:
        raise RuntimeError("PRSC_PEAK_RSS_MEASUREMENT_INVALID")
    return {
        "peak_memory_bytes": peak_kib * 1024,
        "component_bytes": component_bytes,
        "measurement_source": MEASUREMENT_SOURCE,
        "peak_memory_quantity": PEAK_MEMORY_QUANTITY,
        "measurement_scope": PEAK_MEMORY_SCOPE,
        "isolated_fresh_process": True,
        "os_rss": True,
        "rss_unit_source": "LINUX_RUSAGE_RU_MAXRSS_KIB_CONVERTED_TO_BYTES",
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
    }


def _measure_peak_rss_bytes(tier: Mapping[str, Any]) -> dict[str, Any]:
    if not sys.platform.startswith("linux"):
        raise RuntimeError("PRSC_PEAK_RSS_REQUIRES_PINNED_LINUX_EXECUTION_ENVIRONMENT")
    script = (
        "import json,sys;"
        "from ovc.research_operations.prsc.capacity import _peak_rss_child_output;"
        "print(json.dumps(_peak_rss_child_output(json.loads(sys.argv[1])),"
        "sort_keys=True,separators=(',',':')))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script, json.dumps(dict(tier), sort_keys=True, separators=(",", ":"))],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=dict(os.environ),
    )
    rows = [line for line in proc.stdout.splitlines() if line.strip()]
    if len(rows) != 1:
        raise RuntimeError("PRSC_PEAK_RSS_CHILD_OUTPUT_INVALID")
    output = json.loads(rows[0])
    if (
        output.get("measurement_source") != MEASUREMENT_SOURCE
        or output.get("peak_memory_quantity") != PEAK_MEMORY_QUANTITY
        or int(output.get("peak_memory_bytes", 0)) < 1
    ):
        raise RuntimeError("PRSC_PEAK_RSS_CHILD_MEASUREMENT_INVALID")
    return output


def measure_synthetic_capacity_tier(tier: Mapping[str, Any]) -> tuple[CapacityMeasurement, dict[str, Any]]:
    (
        tier_id,
        candidate_count,
        surrogate_count,
        representation_count,
        time_partition_count,
        context_partition_count,
        boundary_count,
    ) = _validated_dimensions(tier)
    components = _build_synthetic_components(tier)
    component_bytes = {name: _canonical_size(value) for name, value in components.items()}
    artifact_bytes = sum(component_bytes.values())
    memory_evidence = _measure_peak_rss_bytes(tier)
    if memory_evidence["component_bytes"] != component_bytes:
        raise RuntimeError("PRSC_PEAK_RSS_WORKLOAD_MISMATCH")
    peak_memory_bytes = int(memory_evidence["peak_memory_bytes"])
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
        "peak_memory_measurement": {
            key: value
            for key, value in memory_evidence.items()
            if key not in {"peak_memory_bytes", "component_bytes"}
        },
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
