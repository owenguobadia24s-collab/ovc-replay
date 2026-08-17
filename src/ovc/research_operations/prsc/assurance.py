from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence


class PRSCAssuranceError(ValueError):
    pass


@dataclass(frozen=True)
class EquivalenceResult:
    family: str
    status: str
    reference: Any
    optimized: Any


@dataclass(frozen=True)
class CapacityMeasurement:
    tier_id: str
    candidate_count: int
    surrogate_count: int
    representation_count: int
    time_partition_count: int
    context_partition_count: int
    boundary_count: int
    artifact_bytes: int
    peak_memory_bytes: int
    review_units: int


def evaluate_reference_equivalence(
    family: str,
    inputs: Iterable[Any],
    reference: Callable[[Any], Any],
    optimized: Callable[[Any], Any],
) -> list[EquivalenceResult]:
    results: list[EquivalenceResult] = []
    for item in inputs:
        ref = reference(item)
        opt = optimized(item)
        status = "PASS" if ref == opt else "MISMATCH_QUARANTINE_OPTIMIZED"
        results.append(EquivalenceResult(family=family, status=status, reference=ref, optimized=opt))
    return results


def assert_fixture_catalogue_complete(
    registered_fixture_ids: Sequence[str], executed_fixture_ids: Sequence[str]
) -> None:
    registered = set(registered_fixture_ids)
    executed = set(executed_fixture_ids)
    missing = registered - executed
    unexpected = executed - registered
    if missing or unexpected:
        raise PRSCAssuranceError(
            f"fixture catalogue mismatch: missing={sorted(missing)} unexpected={sorted(unexpected)}"
        )


def capacity_status(
    measurement: CapacityMeasurement,
    operational_limits: Mapping[str, int | float],
) -> str:
    checks = {
        "candidate_count": measurement.candidate_count,
        "surrogate_count": measurement.surrogate_count,
        "artifact_bytes": measurement.artifact_bytes,
        "peak_memory_bytes": measurement.peak_memory_bytes,
        "review_units": measurement.review_units,
    }
    for key, value in checks.items():
        limit = operational_limits.get(key)
        if limit is not None and value > limit:
            return "CAPACITY_EXCEEDED"
    return "PASS"


def build_mechanical_conformance_bundle(
    *,
    bundle_id: str,
    fixture_results: Sequence[Mapping[str, Any]],
    equivalence_results: Sequence[EquivalenceResult],
    capacity_results: Sequence[Mapping[str, Any]],
    protected_source_survivors: int,
) -> dict[str, Any]:
    if protected_source_survivors < 0:
        raise PRSCAssuranceError("protected_source_survivors cannot be negative")

    eq_payload = [
        {
            "family": item.family,
            "status": item.status,
            "reference": item.reference,
            "optimized": item.optimized,
        }
        for item in equivalence_results
    ]
    mismatch = any(item.status != "PASS" for item in equivalence_results)
    capacity_incomplete = any(
        item.get("status") in {"CAPACITY_EXCEEDED", "REVIEW_CAPACITY_EXCEEDED"}
        for item in capacity_results
    )
    fixture_block = any(item.get("status") in {"BLOCK", "QUARANTINE"} for item in fixture_results)

    if protected_source_survivors:
        status = "QUARANTINED"
        reachability = "BLOCKING_SURVIVORS"
    elif mismatch or fixture_block:
        status = "BLOCKED"
        reachability = "ZERO_SURVIVORS"
    elif capacity_incomplete:
        status = "CAPACITY_INCOMPLETE"
        reachability = "ZERO_SURVIVORS"
    else:
        status = "PASS_CANDIDATE"
        reachability = "ZERO_SURVIVORS"

    return {
        "schema_version": "prsc_mechanical_conformance_bundle/v0.1",
        "bundle_id": bundle_id,
        "fixture_results": list(fixture_results),
        "equivalence_results": eq_payload,
        "capacity_results": list(capacity_results),
        "protected_source_reachability": reachability,
        "status": status,
        "authority_effect": "NONE",
    }
