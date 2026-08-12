from __future__ import annotations

import copy
import platform
import statistics
import sys
import time
from dataclasses import asdict, replace
from typing import Any, Iterable, Mapping, Sequence

from .canonical import evidence_frontier_logical_hash, occurrence_record_id
from .model import (
    DependencyRef,
    DependencyRole,
    EvidenceFrontier,
    EvidenceState,
    OccurrenceAnchor,
    OccurrencePack,
    StructuralDimension,
    StructuralFacet,
    StructuralOccurrenceRecord,
)
from .validators import ESLValidationError, parse_utc, validate_occurrence


class OccurrenceCompileError(ValueError):
    pass


BOOTSTRAP_PACK = OccurrencePack(
    occurrence_pack_id="OPTB-ESL-OCCURRENCE-PACK-GBPUSD-BID-15M-v0.1",
    anchor_kind="C2_OBSERVATION",
    required_dimensions=tuple(StructuralDimension),
    required_source_types=("C2Observation",),
    optional_source_types=("C2PObjectAssertion", "C2EEpisode", "OccurrenceContext"),
    comparability_domain_id="CD.GBPUSD.BID.15M.C2.v0.1",
)

_PROHIBITED_EVIDENCE_KEYS = {
    "future",
    "future_value",
    "forward_outcome",
    "outcome",
    "probability",
    "risk",
    "exposure",
    "trade",
    "trading",
    "execution",
}


def _scan_prohibited(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in _PROHIBITED_EVIDENCE_KEYS:
                raise OccurrenceCompileError(f"ESL_PROHIBITED_EVIDENCE_KEY:{path}.{key}")
            _scan_prohibited(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_prohibited(item, f"{path}[{index}]")


def _require_bootstrap_observation(observation: Mapping[str, Any]) -> None:
    if str(observation.get("schema")) != "c2_observation/vnext-r1":
        raise OccurrenceCompileError("ESL_C2_SOURCE_SCHEMA_INVALID")
    if observation.get("instrument") != "GBPUSD" or observation.get("side") != "BID":
        raise OccurrenceCompileError("ESL_BOOTSTRAP_SCOPE_MISMATCH")
    start = str(observation.get("interval_start"))
    end = str(observation.get("interval_end"))
    if not start or not end:
        raise OccurrenceCompileError("ESL_C2_INTERVAL_MISSING")
    start_dt = parse_utc(start, field="c2.interval_start")
    end_dt = parse_utc(end, field="c2.interval_end")
    if (end_dt - start_dt).total_seconds() != 15 * 60:
        raise OccurrenceCompileError("ESL_BOOTSTRAP_SCALE_MISMATCH")
    if observation.get("projection_eligibility", {}).get("eligible") is not True:
        raise OccurrenceCompileError("ESL_REQUIRED_C2_OBSERVATION_NOT_ELIGIBLE")
    if not observation.get("observation_id") or not observation.get("first_valid_time"):
        raise OccurrenceCompileError("ESL_C2_IDENTITY_OR_FVT_MISSING")
    parse_utc(str(observation["first_valid_time"]), field="c2.first_valid_time")


def _facet(axis: StructuralDimension, profiles: Sequence[Mapping[str, Any]], cutoff: str) -> StructuralFacet:
    ordered = sorted((copy.deepcopy(dict(item)) for item in profiles), key=lambda item: str(item.get("profile_output_id")))
    if not ordered:
        return StructuralFacet(axis, EvidenceState.MISSING, (), None, ("C2_AXIS_PROFILE_MISSING",))
    components: list[dict[str, Any]] = []
    source_refs: list[str] = []
    computable = 0
    reasons: set[str] = set()
    cutoff_dt = parse_utc(cutoff, field="evaluation_cutoff")
    for profile in ordered:
        if profile.get("axis") != axis.value:
            raise OccurrenceCompileError("ESL_C2_PROFILE_AXIS_MISMATCH")
        profile_id = str(profile.get("profile_output_id") or "")
        if not profile_id:
            raise OccurrenceCompileError("ESL_C2_PROFILE_ID_MISSING")
        as_of = str(profile.get("as_of_time") or "")
        if not as_of or parse_utc(as_of, field=f"profile:{profile_id}:as_of_time") > cutoff_dt:
            raise OccurrenceCompileError("ESL_C2_PROFILE_AFTER_CUTOFF")
        state = str(profile.get("computability"))
        if state == "COMPUTABLE":
            computable += 1
        elif state != "NOT_COMPUTABLE":
            raise OccurrenceCompileError("ESL_C2_PROFILE_COMPUTABILITY_UNKNOWN")
        profile_reasons = tuple(sorted(str(x) for x in profile.get("reason_codes", [])))
        reasons.update(profile_reasons)
        source_refs.append(profile_id)
        components.append({
            "profile_output_id": profile_id,
            "profile_id": profile.get("profile_id"),
            "computability": state,
            "reason_codes": list(profile_reasons),
            "facts": copy.deepcopy(profile.get("facts")),
        })
    if computable == 0:
        return StructuralFacet(axis, EvidenceState.NOT_EVALUABLE, tuple(source_refs), None, tuple(sorted(reasons or {"C2_AXIS_NOT_COMPUTABLE"})))
    return StructuralFacet(
        axis,
        EvidenceState.AVAILABLE,
        tuple(source_refs),
        {"components": components},
        tuple(sorted(reasons)),
    )


def _frontier_payload(frontier: EvidenceFrontier) -> dict[str, Any]:
    return asdict(frontier)


def _record_payload(record: StructuralOccurrenceRecord) -> dict[str, Any]:
    return asdict(record)


def compile_structural_occurrence(
    c2_observation: Mapping[str, Any],
    profile_outputs: Sequence[Mapping[str, Any]],
    *,
    source_generation_id: str,
    evaluation_cutoff: str | None = None,
    optional_dependencies: Iterable[DependencyRef] = (),
    pack: OccurrencePack = BOOTSTRAP_PACK,
) -> StructuralOccurrenceRecord:
    observation = copy.deepcopy(dict(c2_observation))
    profiles = [copy.deepcopy(dict(item)) for item in profile_outputs]
    _scan_prohibited(observation)
    _scan_prohibited(profiles)
    _require_bootstrap_observation(observation)
    if not source_generation_id:
        raise OccurrenceCompileError("ESL_SOURCE_GENERATION_ID_REQUIRED")
    if any(profile.get("axis") == "QUALITY" for profile in profiles):
        raise OccurrenceCompileError("ESL_GLOBAL_QUALITY_PROFILE_FORBIDDEN")
    unknown_axes = sorted({str(profile.get("axis")) for profile in profiles} - {item.value for item in StructuralDimension})
    if unknown_axes:
        raise OccurrenceCompileError("ESL_UNKNOWN_STRUCTURAL_DIMENSION:" + ",".join(unknown_axes))

    cutoff = evaluation_cutoff or str(observation["first_valid_time"])
    cutoff_dt = parse_utc(cutoff, field="evaluation_cutoff")
    observation_fvt = str(observation["first_valid_time"])
    if parse_utc(observation_fvt, field="c2.first_valid_time") > cutoff_dt:
        raise OccurrenceCompileError("ESL_REQUIRED_C2_AFTER_CUTOFF")

    by_axis: dict[str, list[Mapping[str, Any]]] = {item.value: [] for item in StructuralDimension}
    for profile in profiles:
        by_axis[str(profile["axis"])].append(profile)
    facets = tuple(_facet(axis, by_axis[axis.value], cutoff) for axis in StructuralDimension)

    required_ref = DependencyRef(
        ref_id=str(observation["observation_id"]),
        owner="C2",
        object_type="C2Observation",
        role=DependencyRole.REQUIRED,
        evidence_state=EvidenceState.AVAILABLE,
        first_valid_time=observation_fvt,
        generation_id=source_generation_id,
        comparability_domain_id=pack.comparability_domain_id,
        identity_defining=True,
    )
    optional_refs = tuple(optional_dependencies)
    refs = (required_ref, *optional_refs)
    required_ids = tuple(sorted(ref.ref_id for ref in refs if ref.role is DependencyRole.REQUIRED))
    optional_ids = tuple(sorted(ref.ref_id for ref in refs if ref.role in {
        DependencyRole.OPTIONAL,
        DependencyRole.STRATIFIER,
        DependencyRole.FILTER,
        DependencyRole.DISPLAY_ONLY,
        DependencyRole.PROVENANCE_ONLY,
    }))
    missing_ids = tuple(sorted(ref.ref_id for ref in refs if ref.evidence_state is not EvidenceState.AVAILABLE))
    generations = tuple(sorted({ref.generation_id for ref in refs}))
    required_fvts = [
        parse_utc(str(ref.first_valid_time), field=f"dependency:{ref.ref_id}:first_valid_time")
        for ref in refs
        if ref.role is DependencyRole.REQUIRED and ref.evidence_state is EvidenceState.AVAILABLE and ref.first_valid_time
    ]
    latest_required = max(required_fvts).isoformat().replace("+00:00", "Z") if required_fvts else None
    frontier = EvidenceFrontier(
        evaluation_cutoff=cutoff,
        required_ref_ids=required_ids,
        optional_ref_ids=optional_ids,
        missing_ref_ids=missing_ids,
        source_generation_ids=generations,
        latest_required_fvt=latest_required,
        dependency_roles={ref.ref_id: ref.role for ref in refs},
        comparability_domain_id=pack.comparability_domain_id,
    )
    frontier_hash = evidence_frontier_logical_hash(_frontier_payload(frontier))
    record = StructuralOccurrenceRecord(
        occurrence_record_id=None,
        occurrence_pack_id=pack.occurrence_pack_id,
        anchor=OccurrenceAnchor(
            "C2_OBSERVATION",
            str(observation["observation_id"]),
            "GBPUSD",
            "BID",
            "15M",
        ),
        evaluation_cutoff=cutoff,
        first_valid_time=latest_required or observation_fvt,
        effective_time=str(observation["interval_start"]),
        facets=facets,
        dependency_refs=refs,
        evidence_frontier=frontier,
        source_generation_ids=generations,
        comparability_domain_id=pack.comparability_domain_id,
        authority_state="INACTIVE_CONFORMANCE_ONLY",
        extensions={
            "compiler_id": "ESLI.STRUCTURAL_OCCURRENCE.REFERENCE.v0.1",
            "effective_end": str(observation["interval_end"]),
            "evidence_frontier_logical_hash": frontier_hash,
            "source_schema": str(observation["schema"]),
        },
    )
    try:
        validate_occurrence(record, pack)
    except ESLValidationError as exc:
        raise OccurrenceCompileError(str(exc)) from exc
    record_id = occurrence_record_id(_record_payload(record))
    final = replace(record, occurrence_record_id=record_id)
    validate_occurrence(final, pack)
    return final


def measure_reference_compiler(
    c2_observation: Mapping[str, Any],
    profile_outputs: Sequence[Mapping[str, Any]],
    *,
    source_generation_id: str,
    repetitions: int = 100,
) -> dict[str, Any]:
    if repetitions < 20:
        raise ValueError("ESL_PERFORMANCE_REPETITIONS_TOO_SMALL")
    durations: list[float] = []
    first_id: str | None = None
    for _ in range(repetitions):
        started = time.perf_counter_ns()
        record = compile_structural_occurrence(
            c2_observation,
            profile_outputs,
            source_generation_id=source_generation_id,
        )
        durations.append((time.perf_counter_ns() - started) / 1_000_000.0)
        if first_id is None:
            first_id = record.occurrence_record_id
        elif record.occurrence_record_id != first_id:
            raise RuntimeError("ESL_PERFORMANCE_RUN_IDENTITY_DRIFT")
    ordered = sorted(durations)
    p95_index = max(0, min(len(ordered) - 1, int(0.95 * len(ordered) + 0.999999) - 1))
    return {
        "schema": "ovc-esl-bootstrap-reference-performance/v1",
        "measurement_status": "REFERENCE_MEASUREMENT_NOT_YET_BUDGET",
        "compiler_id": "ESLI.STRUCTURAL_OCCURRENCE.REFERENCE.v0.1",
        "repetitions": repetitions,
        "p50_ms": statistics.median(ordered),
        "p95_ms": ordered[p95_index],
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "occurrence_record_id": first_id,
        "environment": {
            "python_version": platform.python_version(),
            "implementation": sys.implementation.name,
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
        },
        "authority": "MEASUREMENT_ONLY_NO_SLO_OR_BUDGET",
    }
