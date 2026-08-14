from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


PROFILES = (
    "BASE_STRUCTURAL",
    "ORGANISATION_ENRICHED",
    "CONSTRAINT_ENRICHED",
    "FULL_RESEARCH",
)


class ProfileComparisonError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _logical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("rb") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ProfileComparisonError(f"SOURCE_JSON_INVALID:{line_number}") from exc
            if not isinstance(value, dict):
                raise ProfileComparisonError(f"SOURCE_ROW_OBJECT_REQUIRED:{line_number}")
            rows.append(value)
    return rows


def environment_snapshot() -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "implementation": sys.implementation.name,
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "libc": list(platform.libc_ver()),
        "processor_count": os.cpu_count(),
    }


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "ovc-esl-june-profile-comparison-manifest/v1":
        raise ProfileComparisonError("PROFILE_MANIFEST_SCHEMA_INVALID")
    if value.get("freeze_state") != "FROZEN_BEFORE_PROFILE_RESULT_INSPECTION":
        raise ProfileComparisonError("PROFILE_MANIFEST_NOT_PREFROZEN")
    if tuple(value.get("profiles", [])) != PROFILES:
        raise ProfileComparisonError("PROFILE_MANIFEST_PROFILE_ORDER_INVALID")
    if value.get("winner_synthesis") != "FORBIDDEN":
        raise ProfileComparisonError("PROFILE_WINNER_SYNTHESIS_FORBIDDEN")
    return value


def _target_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = [dict(row) for row in rows if row.get("target_eligible") is True]
    return sorted(result, key=lambda row: (str(row.get("first_valid_time")), str(row.get("c2_state_id"))))


def _load_source(source_path: Path, manifest: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source = manifest["source"]
    observed_size = source_path.stat().st_size
    if observed_size != int(source["byte_size"]):
        raise ProfileComparisonError("SOURCE_BYTE_SIZE_MISMATCH")
    if _sha256_file(source_path) != source["sha256"]:
        raise ProfileComparisonError("SOURCE_SHA256_MISMATCH")
    rows = _jsonl(source_path)
    targets = _target_rows(rows)
    population = manifest["population"]
    if len(targets) != int(population["eligible_record_count"]):
        raise ProfileComparisonError("PROFILE_COMPARABILITY_BROKEN:ELIGIBLE_COUNT")
    ids = sorted(str(row["c2_state_id"]) for row in targets)
    if _logical_hash(ids) != population["eligible_ids_sha256"]:
        raise ProfileComparisonError("PROFILE_COMPARABILITY_BROKEN:ELIGIBLE_IDS")
    cutoffs = sorted((str(row["c2_state_id"]), str(row["first_valid_time"])) for row in targets)
    if _logical_hash(cutoffs) != manifest["cutoff_schedule"]["sha256"]:
        raise ProfileComparisonError("PROFILE_COMPARABILITY_BROKEN:CUTOFF_SCHEDULE")
    for row in targets:
        if row.get("source_slice_id") != source["source_slice_id"]:
            raise ProfileComparisonError("PROFILE_COMPARABILITY_BROKEN:SOURCE_SLICE")
        if row.get("side") != source["side"] or row.get("clock") != source["clock"]:
            raise ProfileComparisonError("PROFILE_COMPARABILITY_BROKEN:SCOPE")
    return rows, targets


def _axis_summary(targets: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for axis in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY"):
        states: Counter[str] = Counter()
        values: Counter[str] = Counter()
        reasons: Counter[str] = Counter()
        for row in targets:
            axis_row = row.get("axes", {}).get(axis, {})
            state = str(axis_row.get("evidence_state") or axis_row.get("status") or "UNKNOWN")
            states[state] += 1
            value = axis_row.get("value")
            if value is not None:
                values[json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)] += 1
            for reason in axis_row.get("reason_codes", []) or []:
                reasons[str(reason)] += 1
        summary[axis] = {
            "evidence_states": dict(sorted(states.items())),
            "distinct_value_count": len(values),
            "reason_codes": dict(sorted(reasons.items())),
        }
    return summary


def _p0_information(targets: list[dict[str, Any]], manifest: Mapping[str, Any]) -> dict[str, Any]:
    structural_axes = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")
    any_evaluated = 0
    all_structural_evaluated = 0
    level_refs = 0
    container_refs = 0
    persistence_refs = 0
    continuity: Counter[str] = Counter()
    for row in targets:
        states = []
        for axis in structural_axes:
            axis_row = row.get("axes", {}).get(axis, {})
            state = str(axis_row.get("evidence_state") or axis_row.get("status") or "UNKNOWN")
            states.append(state)
        evaluated = [state not in {"NOT_EVALUATED", "NOT_EVALUABLE", "MISSING", "UNKNOWN"} for state in states]
        any_evaluated += int(any(evaluated))
        all_structural_evaluated += int(all(evaluated))
        level_refs += len(row.get("level_ids") or [])
        container_refs += len(row.get("container_ids") or [])
        persistence_refs += len(row.get("persistence") or []) if isinstance(row.get("persistence"), list) else int(bool(row.get("persistence")))
        continuity[str(row.get("continuity") or "UNKNOWN")] += 1
    payload = {
        "schema": "ovc-esl-profile-information-entry/v1",
        "profile": "BASE_STRUCTURAL",
        "execution_status": "EXECUTED_SOURCE_BOUND_SUMMARY",
        "common_population": {
            "eligible_record_count": len(targets),
            "eligible_ids_sha256": manifest["population"]["eligible_ids_sha256"],
            "cutoff_schedule_sha256": manifest["cutoff_schedule"]["sha256"],
        },
        "information_vector": {
            "axis_summary": _axis_summary(targets),
            "records_with_any_structural_axis_evaluated": any_evaluated,
            "records_with_all_four_structural_axes_evaluated": all_structural_evaluated,
            "level_reference_count": level_refs,
            "container_reference_count": container_refs,
            "persistence_reference_count": persistence_refs,
            "continuity_counts": dict(sorted(continuity.items())),
        },
        "structural_occurrence_projection": {
            "execution_status": "NOT_EXECUTABLE_FROM_THIS_ACCEPTED_SOURCE_SURFACE",
            "reason_code": "SOURCE_SURFACE_IS_C2_STATE_SUMMARY_NOT_C2_OBSERVATION_VNEXT_R1",
            "no_synthetic_observation_conversion": True,
        },
        "c3_projection": {
            "execution_status": "NOT_EXECUTABLE_UPSTREAM_STRUCTURAL_OCCURRENCE_NOT_MATERIALIZED",
            "c3_bridge_maturity": "INACTIVE_REFERENCE",
        },
    }
    return {**payload, "logical_hash": _logical_hash(payload)}


def _typed_absence(profile: str, reason: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "ovc-esl-profile-information-entry/v1",
        "profile": profile,
        "execution_status": "NOT_EXECUTABLE_UNDER_CURRENT_PACK",
        "reason_code": reason,
        "common_population": {
            "eligible_record_count": manifest["population"]["eligible_record_count"],
            "eligible_ids_sha256": manifest["population"]["eligible_ids_sha256"],
            "cutoff_schedule_sha256": manifest["cutoff_schedule"]["sha256"],
        },
        "information_vector": {"typed_absence": True},
    }
    return {**payload, "logical_hash": _logical_hash(payload)}


def _p3_handoff(p0: Mapping[str, Any], p1: Mapping[str, Any], p2: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    handoff = {
        "schema": "ovc-esl-full-research-handoff/v1",
        "handoff_status": "FULL_RESEARCH_HANDOFF",
        "source_profile_hashes": {
            "BASE_STRUCTURAL": p0["logical_hash"],
            "ORGANISATION_ENRICHED": p1["logical_hash"],
            "CONSTRAINT_ENRICHED": p2["logical_hash"],
        },
        "source_population_sha256": manifest["population"]["eligible_ids_sha256"],
        "research_candidate_generation": "NOT_PERFORMED",
        "structural_term_admission": "NONE",
        "mechanism_claim": "NONE",
        "downstream_runtime": "DOWNSTREAM_RUNTIME_NOT_MATERIALIZED",
        "authority_effect": "NONE",
    }
    handoff = {**handoff, "logical_hash": _logical_hash(handoff)}
    payload = {
        "schema": "ovc-esl-profile-information-entry/v1",
        "profile": "FULL_RESEARCH",
        "execution_status": "FULL_RESEARCH_HANDOFF",
        "reason_code": "DOWNSTREAM_RUNTIME_NOT_MATERIALIZED",
        "common_population": {
            "eligible_record_count": manifest["population"]["eligible_record_count"],
            "eligible_ids_sha256": manifest["population"]["eligible_ids_sha256"],
            "cutoff_schedule_sha256": manifest["cutoff_schedule"]["sha256"],
        },
        "information_vector": {"handoff_object_count": 1, "handoff": handoff},
    }
    return {**payload, "logical_hash": _logical_hash(payload)}


def _measure(fn) -> tuple[Any, dict[str, Any]]:
    before_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    start_cpu = time.process_time_ns()
    start_wall = time.perf_counter_ns()
    value = fn()
    end_wall = time.perf_counter_ns()
    end_cpu = time.process_time_ns()
    after_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value, {
        "wall_seconds": (end_wall - start_wall) / 1_000_000_000,
        "process_cpu_seconds": (end_cpu - start_cpu) / 1_000_000_000,
        "peak_rss_kib": max(before_rss, after_rss),
    }


def execute(source_path: Path, manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    environment = environment_snapshot()
    if environment != manifest["execution_environment"]:
        raise ProfileComparisonError("PROFILE_CAPACITY_NOT_COMPARABLE:ENVIRONMENT_MISMATCH")

    (source_rows, targets), source_cold = _measure(lambda: _load_source(source_path, manifest))
    (_, targets_warm), source_warm = _measure(lambda: _load_source(source_path, manifest))
    if [row["c2_state_id"] for row in targets] != [row["c2_state_id"] for row in targets_warm]:
        raise ProfileComparisonError("PROFILE_COMPARABILITY_BROKEN:WARM_SOURCE_DRIFT")

    p0, p0_capacity = _measure(lambda: _p0_information(targets, manifest))
    p1 = _typed_absence("ORGANISATION_ENRICHED", "MATCHING_SFC_FAMILY_CATALOG_NOT_MATERIALIZED_FOR_FROZEN_POPULATION", manifest)
    p2 = _typed_absence("CONSTRAINT_ENRICHED", "CONSTRAINT_COMPARATOR_NOT_MATERIALIZED", manifest)
    p3, p3_capacity = _measure(lambda: _p3_handoff(p0, p1, p2, manifest))

    information = {
        "schema": "ovc-esl-profile-information-ledger/v1",
        "manifest_id": manifest["manifest_id"],
        "entries": [p0, p1, p2, p3],
        "winner_synthesis": "FORBIDDEN",
        "authority_effect": "NONE",
    }
    information = {**information, "logical_hash": _logical_hash(information)}

    generated_information_bytes = len(_canonical(information))
    capacity_entries = [
        {"profile": "BASE_STRUCTURAL", "status": "EXECUTED_SOURCE_BOUND_SUMMARY", "measurement": p0_capacity},
        {"profile": "ORGANISATION_ENRICHED", "status": "NOT_EXECUTABLE_UNDER_CURRENT_PACK", "measurement": None},
        {"profile": "CONSTRAINT_ENRICHED", "status": "NOT_EXECUTABLE_UNDER_CURRENT_PACK", "measurement": None},
        {"profile": "FULL_RESEARCH", "status": "FULL_RESEARCH_HANDOFF", "measurement": p3_capacity},
    ]
    capacity = {
        "schema": "ovc-esl-profile-capacity-ledger/v1",
        "manifest_id": manifest["manifest_id"],
        "execution_environment": environment,
        "source_measurements": {"cold": source_cold, "warm": source_warm},
        "profile_measurements": capacity_entries,
        "generated_information_bytes": generated_information_bytes,
        "cache_policy": manifest["cache_policy"],
        "checkpoint_policy": manifest["checkpoint_policy"],
        "authority_effect": "NONE",
    }

    marginal = {
        "schema": "ovc-esl-marginal-profile-delta-ledger/v1",
        "manifest_id": manifest["manifest_id"],
        "baseline_profile": "BASE_STRUCTURAL",
        "entries": [
            {"profile": "ORGANISATION_ENRICHED", "baseline": "BASE_STRUCTURAL", "information_delta": "TYPED_ABSENCE_NOT_ZERO", "capacity_delta": "NOT_COMPARABLE_PROFILE_NOT_EXECUTABLE"},
            {"profile": "CONSTRAINT_ENRICHED", "baseline": "BASE_STRUCTURAL", "information_delta": "TYPED_ABSENCE_NOT_ZERO", "capacity_delta": "NOT_COMPARABLE_PROFILE_NOT_EXECUTABLE"},
            {"profile": "FULL_RESEARCH", "baseline": "BASE_STRUCTURAL", "information_delta": {"handoff_objects_added": 1}, "capacity_delta": p3_capacity},
        ],
        "winner_synthesis": "FORBIDDEN",
        "authority_effect": "NONE",
    }

    absence = {
        "schema": "ovc-esl-profile-absence-disagreement-ledger/v1",
        "manifest_id": manifest["manifest_id"],
        "entries": [
            {"profile": "BASE_STRUCTURAL", "state": "PARTIAL_EXECUTABILITY", "reason_code": "SOURCE_SURFACE_IS_C2_STATE_SUMMARY_NOT_C2_OBSERVATION_VNEXT_R1"},
            {"profile": "ORGANISATION_ENRICHED", "state": "NOT_EXECUTABLE_UNDER_CURRENT_PACK", "reason_code": "MATCHING_SFC_FAMILY_CATALOG_NOT_MATERIALIZED_FOR_FROZEN_POPULATION"},
            {"profile": "CONSTRAINT_ENRICHED", "state": "NOT_EXECUTABLE_UNDER_CURRENT_PACK", "reason_code": "CONSTRAINT_COMPARATOR_NOT_MATERIALIZED"},
            {"profile": "FULL_RESEARCH", "state": "FULL_RESEARCH_HANDOFF", "reason_code": "DOWNSTREAM_RUNTIME_NOT_MATERIALIZED"},
        ],
        "winner_synthesis": "FORBIDDEN",
        "authority_effect": "NONE",
    }

    receipt = {
        "schema": "ovc-esl-wp13-reproducibility-authority-receipt/v1",
        "manifest_id": manifest["manifest_id"],
        "source": {
            "sha256": _sha256_file(source_path),
            "byte_size": source_path.stat().st_size,
            "row_count": len(source_rows),
            "eligible_record_count": len(targets),
            "eligible_ids_sha256": manifest["population"]["eligible_ids_sha256"],
            "cutoff_schedule_sha256": manifest["cutoff_schedule"]["sha256"],
        },
        "profile_information_hashes": {entry["profile"]: entry["logical_hash"] for entry in information["entries"]},
        "information_ledger_logical_hash": information["logical_hash"],
        "authority": {
            "validation": "LOCKED_UNCONSUMED",
            "provider_fetch": "DENIED",
            "selector_change": "NONE",
            "scientific_method_or_family_promotion": "NONE",
            "semantic_admission": "NONE",
            "c3_activation": "NONE",
            "publication": "NONE",
            "probability_risk_exposure_execution": "NONE",
            "winner_synthesis": "FORBIDDEN",
        },
    }

    outputs = {
        "ProfileInformationLedger_v1.json": information,
        "ProfileCapacityLedger_v1.json": capacity,
        "MarginalProfileDeltaLedger_v1.json": marginal,
        "ProfileAbsenceDisagreementLedger_v1.json": absence,
        "ESLI_WP13_REPRODUCIBILITY_AUTHORITY_RECEIPT.json": receipt,
    }
    for name, value in outputs.items():
        (output_dir / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {name: _sha256_file(output_dir / name) for name in sorted(outputs)}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3:
        raise SystemExit("usage: profile_comparison.py SOURCE.jsonl MANIFEST.json OUTPUT_DIR")
    hashes = execute(Path(args[0]), Path(args[1]), Path(args[2]))
    print(json.dumps(hashes, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
