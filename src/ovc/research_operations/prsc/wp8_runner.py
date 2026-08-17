from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Mapping, Sequence

from .assurance import (
    CapacityMeasurement,
    EquivalenceResult,
    PRSCAssuranceError,
    assert_fixture_catalogue_complete,
    build_mechanical_conformance_bundle,
    capacity_status,
    evaluate_reference_equivalence,
)

EXPECTED_AV_FIXTURES = tuple(f"AV-PRSC-{i:02d}" for i in range(1, 16))


def freeze_operational_budget(
    measurements: Sequence[CapacityMeasurement],
    *,
    headroom_ratio: float = 1.25,
) -> dict[str, Any]:
    if not measurements:
        raise PRSCAssuranceError("cannot freeze operational budget without measurements")
    if headroom_ratio < 1.0:
        raise PRSCAssuranceError("headroom_ratio must be >= 1")
    limits = {
        "candidate_count": int(max(m.candidate_count for m in measurements) * headroom_ratio),
        "surrogate_count": int(max(m.surrogate_count for m in measurements) * headroom_ratio),
        "artifact_bytes": int(max(m.artifact_bytes for m in measurements) * headroom_ratio),
        "peak_memory_bytes": int(max(m.peak_memory_bytes for m in measurements) * headroom_ratio),
        "review_units": int(max(m.review_units for m in measurements) * headroom_ratio),
    }
    return {
        "schema_version": "prsc_operational_budget/v0.1",
        "budget_id": "PRSCI-WP8-MEASURED-OPERATIONAL-BUDGET-v0.1",
        "source": "MEASURED_NON_SCIENTIFIC_SYNTHETIC_EVIDENCE",
        "synthetic_tiers": [m.tier_id for m in measurements],
        "limits": limits,
        "scope_reduction_permitted": False,
        "sampling_permitted": False,
        "authority_effect": "NONE",
    }


def freeze_review_budget(
    measurements: Sequence[CapacityMeasurement],
    *,
    headroom_ratio: float = 1.25,
) -> dict[str, Any]:
    if not measurements:
        raise PRSCAssuranceError("cannot freeze review budget without measurements")
    return {
        "schema_version": "prsc_review_budget/v0.1",
        "budget_id": "PRSCI-WP8-MEASURED-REVIEW-BUDGET-v0.1",
        "source": "MEASURED_NON_SCIENTIFIC_SYNTHETIC_EVIDENCE",
        "review_limits": {
            "review_units": int(max(m.review_units for m in measurements) * headroom_ratio),
            "candidate_count": int(max(m.candidate_count for m in measurements) * headroom_ratio),
        },
        "top_n_permitted": False,
        "deterministic_batching_required": True,
        "authority_effect": "NONE",
    }


def execute_registered_fixtures(
    fixture_handlers: Mapping[str, Callable[[], Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    assert_fixture_catalogue_complete(EXPECTED_AV_FIXTURES, list(fixture_handlers))
    out: list[dict[str, Any]] = []
    for fixture_id in EXPECTED_AV_FIXTURES:
        result = dict(fixture_handlers[fixture_id]())
        result.setdefault("fixture_id", fixture_id)
        if result["fixture_id"] != fixture_id:
            raise PRSCAssuranceError(f"fixture handler identity mismatch for {fixture_id}")
        if "status" not in result:
            raise PRSCAssuranceError(f"fixture {fixture_id} omitted status")
        out.append(result)
    return out


def execute_wp8_assurance(
    *,
    bundle_id: str,
    fixture_handlers: Mapping[str, Callable[[], Mapping[str, Any]]],
    equivalence_families: Mapping[str, tuple[Sequence[Any], Callable[[Any], Any], Callable[[Any], Any]]],
    measurements: Sequence[CapacityMeasurement],
    protected_source_survivors: int,
) -> dict[str, Any]:
    fixture_results = execute_registered_fixtures(fixture_handlers)
    equivalence_results: list[EquivalenceResult] = []
    for family, (inputs, reference, optimized) in equivalence_families.items():
        equivalence_results.extend(evaluate_reference_equivalence(family, inputs, reference, optimized))

    operational_budget = freeze_operational_budget(measurements)
    review_budget = freeze_review_budget(measurements)
    capacity_results = []
    for measurement in measurements:
        capacity_results.append({
            **asdict(measurement),
            "status": capacity_status(measurement, operational_budget["limits"]),
        })

    bundle = build_mechanical_conformance_bundle(
        bundle_id=bundle_id,
        fixture_results=fixture_results,
        equivalence_results=equivalence_results,
        capacity_results=capacity_results,
        protected_source_survivors=protected_source_survivors,
    )
    bundle["operational_budget"] = operational_budget
    bundle["review_budget"] = review_budget
    return bundle
