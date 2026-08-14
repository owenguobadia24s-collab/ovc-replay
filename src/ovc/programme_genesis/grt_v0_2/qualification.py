"""GRT2-WP3E qualification and measurement-before-freeze primitives."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Mapping, Sequence

from .serialization import SERIALIZATION_ID, canonical_sha256

ASSURANCE_AXES = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8")
PERFORMANCE_SURFACES = ("GRT_FAST", "GRT_EXACT", "GRT_REFERENCE", "PROOF_RENEWAL", "READINESS")
MIN_PERFORMANCE_SAMPLES = 20


class QualificationError(ValueError):
    pass


class PerformanceBudgetError(ValueError):
    pass


def build_qualification_target(
    *, constitution_hash: str, runtime_hash: str, scanner_hash: str,
    platform_classes: Sequence[str], mutation_catalogue_hash: str,
) -> dict[str, Any]:
    body = {
        "schema": "grt-qualification-target/v0.2",
        "constitution_hash": constitution_hash,
        "runtime_hash": runtime_hash,
        "scanner_hash": scanner_hash,
        "platform_classes": sorted(set(platform_classes)),
        "mutation_catalogue_hash": mutation_catalogue_hash,
        "assurance_axes": list(ASSURANCE_AXES),
        "required_mutation_survivors": 0,
        "required_reference_incremental_differences": 0,
        "required_unresolved_false_negatives": 0,
        "required_blocking_false_positives": 0,
        "authority_effect": "NONE_QUALIFICATION_TARGET_ONLY",
    }
    return {**body, "target_hash": canonical_sha256(body)}


def build_qualification_record(
    *, target: Mapping[str, Any], axis_results: Mapping[str, str],
    mutation_survivors: int, reference_incremental_differences: int,
    unresolved_false_negatives: int, blocking_false_positives: int,
    capacity_status: str, restart_status: str, platform_status: str, shadow_status: str,
    evidence_refs: Sequence[str],
) -> dict[str, Any]:
    missing_axes = [axis for axis in ASSURANCE_AXES if axis_results.get(axis) not in {"PASS", "FAIL", "NOT_EVALUABLE"}]
    if missing_axes:
        raise QualificationError("GRT_QUALIFICATION_AXIS_RESULT_MISSING:" + ",".join(missing_axes))
    counts = (mutation_survivors, reference_incremental_differences, unresolved_false_negatives, blocking_false_positives)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
        raise QualificationError("GRT_QUALIFICATION_COUNT_INVALID")
    required_statuses = (capacity_status, restart_status, platform_status, shadow_status)
    if any(value not in {"PASS", "FAIL", "NOT_EVALUABLE"} for value in required_statuses):
        raise QualificationError("GRT_QUALIFICATION_STATUS_INVALID")
    passed = (
        all(axis_results[axis] == "PASS" for axis in ASSURANCE_AXES)
        and mutation_survivors == 0
        and reference_incremental_differences == 0
        and unresolved_false_negatives == 0
        and blocking_false_positives == 0
        and all(value == "PASS" for value in required_statuses)
    )
    body = {
        "schema": "grt-qualification-record/v0.2",
        "target_hash": target.get("target_hash"),
        "axis_results": {axis: axis_results[axis] for axis in ASSURANCE_AXES},
        "mutation_survivors": mutation_survivors,
        "reference_incremental_differences": reference_incremental_differences,
        "unresolved_false_negatives": unresolved_false_negatives,
        "blocking_false_positives": blocking_false_positives,
        "capacity_status": capacity_status, "restart_status": restart_status,
        "platform_status": platform_status, "shadow_status": shadow_status,
        "evidence_refs": sorted(set(evidence_refs)),
        "decision": "PASS" if passed else "FAIL",
        "authority_effect": "NONE_QUALIFICATION_EVIDENCE_ONLY",
    }
    return {**body, "qualification_hash": canonical_sha256(body)}


def _nearest_rank(values: Sequence[int], percentile: float) -> int:
    ordered = sorted(values)
    if not ordered:
        raise PerformanceBudgetError("GRT_PERFORMANCE_SAMPLE_EMPTY")
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[min(rank - 1, len(ordered) - 1)]


def freeze_performance_budget(
    *, samples: Sequence[Mapping[str, Any]], environment_hash: str,
    repository_scale: int, cache_storage_ceiling_bytes: int,
    proof_evidence_size_ceiling_bytes: int, capacity_failure_threshold: int,
) -> dict[str, Any]:
    """Freeze numeric budgets only from measured records.

    Each runtime surface needs at least MIN_PERFORMANCE_SAMPLES exact measured
    observations.  Numeric inputs here are themselves measured evidence, not
    defaults; callers must provide their source records separately.
    """
    if not isinstance(repository_scale, int) or repository_scale <= 0:
        raise PerformanceBudgetError("GRT_PERFORMANCE_REPOSITORY_SCALE_INVALID")
    for value in (cache_storage_ceiling_bytes, proof_evidence_size_ceiling_bytes, capacity_failure_threshold):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise PerformanceBudgetError("GRT_PERFORMANCE_CAPACITY_MEASUREMENT_INVALID")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for sample in samples:
        surface = sample.get("surface")
        duration_ms = sample.get("duration_ms")
        peak_memory_bytes = sample.get("peak_memory_bytes")
        if surface not in PERFORMANCE_SURFACES:
            raise PerformanceBudgetError("GRT_PERFORMANCE_SURFACE_INVALID")
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, int) or duration_ms <= 0:
            raise PerformanceBudgetError("GRT_PERFORMANCE_DURATION_INVALID")
        if isinstance(peak_memory_bytes, bool) or not isinstance(peak_memory_bytes, int) or peak_memory_bytes <= 0:
            raise PerformanceBudgetError("GRT_PERFORMANCE_MEMORY_INVALID")
        grouped[surface].append(sample)
    missing = [surface for surface in PERFORMANCE_SURFACES if len(grouped[surface]) < MIN_PERFORMANCE_SAMPLES]
    if missing:
        raise PerformanceBudgetError("GRT_PERFORMANCE_MEASUREMENT_INSUFFICIENT:" + ",".join(missing))
    runtime_budgets = {}
    all_memory = []
    evidence_refs = []
    for surface in PERFORMANCE_SURFACES:
        durations = [int(sample["duration_ms"]) for sample in grouped[surface]]
        memories = [int(sample["peak_memory_bytes"]) for sample in grouped[surface]]
        all_memory.extend(memories)
        evidence_refs.extend(str(sample["evidence_ref"]) for sample in grouped[surface] if sample.get("evidence_ref"))
        runtime_budgets[surface] = {
            "sample_count": len(durations),
            "p50_ms": _nearest_rank(durations, 0.50),
            "p95_ms": _nearest_rank(durations, 0.95),
            "max_ms": max(durations),
        }
    body = {
        "schema": "grt-performance-budget/v0.2",
        "environment_hash": environment_hash,
        "serialization_profile": SERIALIZATION_ID,
        "runtime_budgets": runtime_budgets,
        "peak_memory_ceiling_bytes": max(all_memory),
        "cache_storage_ceiling_bytes": cache_storage_ceiling_bytes,
        "proof_evidence_size_ceiling_bytes": proof_evidence_size_ceiling_bytes,
        "max_supported_repository_scale": repository_scale,
        "capacity_failure_threshold": capacity_failure_threshold,
        "measurement_evidence_refs": sorted(set(evidence_refs)),
        "status": "FROZEN_FROM_MEASURED_EVIDENCE",
        "authority_effect": "NONE_OPERATIONAL_BUDGET_ONLY",
    }
    return {**body, "budget_hash": canonical_sha256(body)}


def evaluate_g2_readiness(*, qualification: Mapping[str, Any], performance_budget: Mapping[str, Any] | None, transition_debt_count: int) -> dict[str, Any]:
    if isinstance(transition_debt_count, bool) or not isinstance(transition_debt_count, int) or transition_debt_count < 0:
        raise QualificationError("GRT_TRANSITION_DEBT_COUNT_INVALID")
    reasons = []
    if qualification.get("decision") != "PASS": reasons.append("QUALIFICATION_NOT_PASS")
    if not performance_budget or performance_budget.get("status") != "FROZEN_FROM_MEASURED_EVIDENCE": reasons.append("PERFORMANCE_BUDGET_NOT_FROZEN")
    if transition_debt_count != 0: reasons.append("PRE_ENFORCEMENT_TRANSITION_DEBT_NONZERO")
    return {
        "schema": "grt-g2-readiness/v0.2",
        "status": "PASS" if not reasons else "BLOCKED",
        "reason_codes": reasons,
        "qualification_hash": qualification.get("qualification_hash"),
        "performance_budget_hash": performance_budget.get("budget_hash") if performance_budget else None,
        "transition_debt_count": transition_debt_count,
        "authority_effect": "NONE_G2_EVIDENCE_ONLY",
    }
