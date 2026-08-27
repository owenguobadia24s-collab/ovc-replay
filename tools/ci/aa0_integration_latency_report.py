#!/usr/bin/env python3
"""Compile deterministic AA0 prewarm integration latency evidence.

The compiler is intentionally read-only.  A caller collects GitHub and receipt
evidence through an already-authorised read path, stores it in one normalized
JSON envelope, and supplies that envelope here.  This module validates exact
identity and timing relationships; it does not contact GitHub or write files.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


REPORT_SCHEMA = "ovc-aa0-integration-latency-report/v1"
EVIDENCE_SCHEMA = "ovc-aa0-integration-latency-evidence/v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
SURFACES = ("repository", "unittest_parity", "runner_parity")
FRESH_JOBS = {
    "vit_routing": "VIT routing preflight",
    "profile": "OVC profile assurance",
    "siq_ready": "SIQ READY admission",
    "merge_readiness": "OVC merge readiness",
}
REUSE_FAILURES = {
    "HEAD_IDENTITY_MISS",
    "PIP_IDENTITY_MISS",
    "QUALIFICATION_GENERATION_MISS",
    "HARNESS_IDENTITY_MISS",
    "CACHE_SCOPE_MISS",
    "CACHE_RESTORE_MISS",
    "OTHER_EXACT_REUSE_FAILURE",
}


class LatencyReportError(RuntimeError):
    """Raised when decision-bearing evidence is missing, ambiguous, or mismatched."""


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LatencyReportError(f"{field}:OBJECT_REQUIRED")
    return value


def _sequence(value: Any, field: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise LatencyReportError(f"{field}:ARRAY_REQUIRED")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise LatencyReportError(f"{field}:NONEMPTY_STRING_REQUIRED")
    return value


def _sha(value: Any, field: str, pattern: re.Pattern[str]) -> str:
    text = _text(value, field)
    if not pattern.fullmatch(text):
        raise LatencyReportError(f"{field}:INVALID_IDENTITY")
    return text


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise LatencyReportError(f"{field}:INTEGER_REQUIRED")
    return value


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise LatencyReportError(f"{field}:BOOLEAN_REQUIRED")
    return value


def _parse_timestamp(value: Any, field: str) -> tuple[datetime, str]:
    raw = _text(value, field)
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise LatencyReportError(f"{field}:RFC3339_REQUIRED") from exc
    if parsed.tzinfo is None:
        raise LatencyReportError(f"{field}:TIMEZONE_REQUIRED")
    utc = parsed.astimezone(timezone.utc)
    normalized = utc.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return utc, normalized


def _duration(start: datetime, end: datetime, field: str) -> float:
    seconds = (end - start).total_seconds()
    if seconds < 0:
        raise LatencyReportError(f"{field}:NEGATIVE_DURATION")
    return round(seconds, 6)


def _identity(value: Any, field: str) -> dict[str, str]:
    row = _mapping(value, field)
    return {
        "candidate_head_sha": _sha(row.get("candidate_head_sha"), f"{field}.candidate_head_sha", SHA40),
        "qualified_prospective_tree": _sha(
            row.get("qualified_prospective_tree"),
            f"{field}.qualified_prospective_tree",
            SHA40,
        ),
        "pip_id": _sha(row.get("pip_id"), f"{field}.pip_id", SHA64),
        "qualification_id": _sha(row.get("qualification_id"), f"{field}.qualification_id", SHA64),
        "qualification_generation_id": _sha(
            row.get("qualification_generation_id"),
            f"{field}.qualification_generation_id",
            SHA64,
        ),
        "aa0_harness_id": _sha(row.get("aa0_harness_id"), f"{field}.aa0_harness_id", SHA64),
    }


def _require_same_identity(expected: Mapping[str, str], observed: Mapping[str, str], field: str) -> None:
    for key in sorted(expected):
        if expected[key] != observed.get(key):
            raise LatencyReportError(f"{field}.{key}:IDENTITY_MISMATCH")


def _workflow(
    value: Any,
    field: str,
    *,
    event: str,
    candidate_head_sha: str,
    prewarm: bool,
) -> tuple[dict[str, Any], datetime, datetime]:
    row = _mapping(value, field)
    if row.get("name") != "tests" or row.get("event") != event:
        raise LatencyReportError(f"{field}:WRONG_WORKFLOW_RUN")
    bound_key = "target_head_sha" if prewarm else "head_sha"
    if row.get(bound_key) != candidate_head_sha:
        raise LatencyReportError(f"{field}.{bound_key}:HEAD_MISMATCH")
    if row.get("status") != "completed" or row.get("conclusion") != "success":
        raise LatencyReportError(f"{field}:SUCCESSFUL_COMPLETION_REQUIRED")
    started, started_text = _parse_timestamp(row.get("started_at"), f"{field}.started_at")
    completed, completed_text = _parse_timestamp(row.get("completed_at"), f"{field}.completed_at")
    duration = _duration(started, completed, f"{field}.duration")
    return {
        "workflow_run_id": _integer(row.get("id"), f"{field}.id", minimum=1),
        "started_at": started_text,
        "completed_at": completed_text,
        "duration_seconds": duration,
    }, started, completed


def _surface_rows(
    value: Any,
    field: str,
    *,
    expected_disposition: str,
) -> tuple[dict[str, dict[str, Any]], list[str], list[datetime]]:
    rows = _mapping(value, field)
    result: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    observed_times: list[datetime] = []
    for name in SURFACES:
        row = _mapping(rows.get(name), f"{field}.{name}")
        disposition = _text(row.get("disposition"), f"{field}.{name}.disposition")
        executed = _boolean(
            row.get("canonical_reference_executed"),
            f"{field}.{name}.canonical_reference_executed",
        )
        observed, observed_text = _parse_timestamp(
            row.get("observed_at"), f"{field}.{name}.observed_at"
        )
        observed_times.append(observed)
        result[name] = {
            "disposition": disposition,
            "canonical_reference_executed": executed,
            "observed_at": observed_text,
        }
        if disposition != expected_disposition:
            failure = str(row.get("failure_reason") or "OTHER_EXACT_REUSE_FAILURE")
            if failure not in REUSE_FAILURES:
                failure = "OTHER_EXACT_REUSE_FAILURE"
            failures.append(failure)
    return result, sorted(set(failures)), observed_times


def _fresh_jobs(
    value: Any, candidate_head_sha: str, pr_opened: datetime
) -> tuple[dict[str, dict[str, Any]], dict[str, datetime]]:
    rows = _sequence(value, "fresh_assurance.jobs")
    output: dict[str, dict[str, Any]] = {}
    completions: dict[str, datetime] = {}
    for key, required_name in FRESH_JOBS.items():
        matches = [row for row in rows if isinstance(row, Mapping) and row.get("name") == required_name]
        if len(matches) != 1:
            raise LatencyReportError(f"fresh_assurance.{key}:REQUIRED_JOB_AMBIGUOUS:{len(matches)}")
        row = matches[0]
        if row.get("head_sha") != candidate_head_sha:
            raise LatencyReportError(f"fresh_assurance.{key}:HEAD_MISMATCH")
        if row.get("conclusion") != "success":
            raise LatencyReportError(f"fresh_assurance.{key}:SUCCESS_REQUIRED")
        started, started_text = _parse_timestamp(row.get("started_at"), f"fresh_assurance.{key}.started_at")
        completed, completed_text = _parse_timestamp(
            row.get("completed_at"), f"fresh_assurance.{key}.completed_at"
        )
        _duration(started, completed, f"fresh_assurance.{key}.duration")
        _duration(pr_opened, completed, f"fresh_assurance.{key}.after_pr_open")
        output[key] = {
            "run_id": _integer(row.get("run_id"), f"fresh_assurance.{key}.run_id", minimum=1),
            "job_id": _integer(row.get("job_id"), f"fresh_assurance.{key}.job_id", minimum=1),
            "started_at": started_text,
            "completed_at": completed_text,
            "duration_seconds": _duration(started, completed, f"fresh_assurance.{key}.duration"),
            "result": "PASS",
        }
        completions[key] = completed
    return output, completions


def _receipt_id(value: Any, field: str) -> str:
    return _sha(value, field, SHA64)


def compile_latency_report(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one evidence envelope and return deterministic report content."""
    if evidence.get("schema") != EVIDENCE_SCHEMA:
        raise LatencyReportError("schema:EVIDENCE_SCHEMA_MISMATCH")
    packet_id = _text(evidence.get("packet_id"), "packet_id")
    identity = _identity(evidence.get("identity"), "identity")
    candidate = identity["candidate_head_sha"]

    prewarm = _mapping(evidence.get("prewarm"), "prewarm")
    _require_same_identity(identity, _identity(prewarm.get("identity"), "prewarm.identity"), "prewarm.identity")
    prewarm_workflow, prewarm_started, prewarm_completed = _workflow(
        prewarm.get("workflow"),
        "prewarm.workflow",
        event="workflow_dispatch",
        candidate_head_sha=candidate,
        prewarm=True,
    )
    prewarm_surfaces, prewarm_failures, _ = _surface_rows(
        prewarm.get("surfaces"), "prewarm.surfaces", expected_disposition="RUN_AA0"
    )
    prewarm_executed = all(row["canonical_reference_executed"] for row in prewarm_surfaces.values())

    pr = _mapping(evidence.get("pr"), "pr")
    metadata = _mapping(pr.get("metadata"), "pr.metadata")
    pr_number = _integer(metadata.get("number"), "pr.metadata.number", minimum=1)
    if metadata.get("head_sha") != candidate or pr.get("current_head_sha") != candidate:
        raise LatencyReportError("pr:STALE_OR_MISMATCHED_HEAD")
    opened, opened_text = _parse_timestamp(metadata.get("opened_at"), "pr.metadata.opened_at")
    _require_same_identity(identity, _identity(pr.get("identity"), "pr.identity"), "pr.identity")
    pr_workflow, _, _ = _workflow(
        pr.get("assurance_workflow"),
        "pr.assurance_workflow",
        event="pull_request",
        candidate_head_sha=candidate,
        prewarm=False,
    )
    pr_surfaces, reuse_failures, reuse_times = _surface_rows(
        pr.get("surfaces"), "pr.surfaces", expected_disposition="EXACT_GENERATION_REUSE"
    )
    if any(row["canonical_reference_executed"] for row in pr_surfaces.values()):
        reuse_failures.append("OTHER_EXACT_REUSE_FAILURE")
    reuse_observed = max(reuse_times)
    _duration(opened, reuse_observed, "derived_metrics.pr_open_to_aa0_reuse_seconds")
    shard_rows = _mapping(pr.get("canonical_shard_jobs"), "pr.canonical_shard_jobs")
    canonical_shards: dict[str, str] = {}
    for key in ("manifest", "shard_0", "shard_1", "shard_2", "shard_3"):
        status = _text(shard_rows.get(key), f"pr.canonical_shard_jobs.{key}")
        canonical_shards[key] = status
        if status != "SKIPPED":
            reuse_failures.append("OTHER_EXACT_REUSE_FAILURE")

    fresh, fresh_completed = _fresh_jobs(
        _mapping(evidence.get("fresh_assurance"), "fresh_assurance").get("jobs"),
        candidate,
        opened,
    )

    materialisation = _mapping(evidence.get("materialisation"), "materialisation")
    prospective_tree = _sha(
        materialisation.get("prospective_tree"), "materialisation.prospective_tree", SHA40
    )
    physical_tree = _sha(materialisation.get("physical_tree"), "materialisation.physical_tree", SHA40)
    if prospective_tree != identity["qualified_prospective_tree"]:
        raise LatencyReportError("materialisation:QUALIFIED_PROSPECTIVE_TREE_MISMATCH")
    if prospective_tree != physical_tree:
        raise LatencyReportError("materialisation:PROSPECTIVE_PHYSICAL_TREE_MISMATCH")
    merged, merged_text = _parse_timestamp(materialisation.get("merged_at"), "materialisation.merged_at")
    _duration(opened, merged, "derived_metrics.pr_open_to_materialised_seconds")

    completion = _mapping(evidence.get("completion"), "completion")
    receipts = _mapping(completion.get("receipts"), "completion.receipts")
    warnings: list[dict[str, str]] = []
    completion_timestamp: str | None = None
    completion_dt: datetime | None = None
    timestamp_record = completion.get("timestamp")
    timestamp_source: str | None = None
    if timestamp_record is None:
        warnings.append(
            {
                "code": "COMPLETION_TIMESTAMP_UNAVAILABLE",
                "field": "completion.completion_timestamp_if_available",
            }
        )
    else:
        timestamp_row = _mapping(timestamp_record, "completion.timestamp")
        timestamp_source = _text(timestamp_row.get("source"), "completion.timestamp.source")
        if timestamp_source not in {"GITHUB_API", "OWNER_LOCAL_RECEIPT", "EXACT_LOG", "CONTROLLER_OBSERVATION"}:
            raise LatencyReportError("completion.timestamp.source:INVALID_PROVENANCE")
        completion_dt, completion_timestamp = _parse_timestamp(
            timestamp_row.get("value"), "completion.timestamp.value"
        )
        _duration(merged, completion_dt, "derived_metrics.materialised_to_completion_seconds_if_available")

    controls = _mapping(evidence.get("controls"), "controls")
    controls_pass = (
        controls.get("repository_protection_active") is True
        and _integer(controls.get("bypass_actor_count"), "controls.bypass_actor_count") == 0
        and _integer(controls.get("physical_writer_count"), "controls.physical_writer_count") == 1
        and controls.get("racpr_mode") == "FALLBACK_CANONICAL_REFERENCE"
        and controls.get("assurance_meaning_unchanged") is True
        and controls.get("new_service_store_or_control_plane") is False
        and all(
            _integer(controls.get(name), f"controls.{name}") == 0
            for name in ("diasi_runtime_use_count", "pes_runtime_use_count", "cers_runtime_use_count")
        )
    )

    metrics: dict[str, float | None] = {
        "prewarm_full_duration_seconds": _duration(
            prewarm_started, prewarm_completed, "derived_metrics.prewarm_full_duration_seconds"
        ),
        "pr_open_to_vit_pass_seconds": _duration(
            opened, fresh_completed["vit_routing"], "derived_metrics.pr_open_to_vit_pass_seconds"
        ),
        "pr_open_to_profile_pass_seconds": _duration(
            opened, fresh_completed["profile"], "derived_metrics.pr_open_to_profile_pass_seconds"
        ),
        "pr_open_to_aa0_reuse_seconds": _duration(
            opened, reuse_observed, "derived_metrics.pr_open_to_aa0_reuse_seconds"
        ),
        "pr_open_to_siq_ready_seconds": _duration(
            opened, fresh_completed["siq_ready"], "derived_metrics.pr_open_to_siq_ready_seconds"
        ),
        "pr_open_to_merge_readiness_seconds": _duration(
            opened,
            fresh_completed["merge_readiness"],
            "derived_metrics.pr_open_to_merge_readiness_seconds",
        ),
        "pr_open_to_materialised_seconds": _duration(
            opened, merged, "derived_metrics.pr_open_to_materialised_seconds"
        ),
        "merge_readiness_to_materialised_seconds": _duration(
            fresh_completed["merge_readiness"],
            merged,
            "derived_metrics.merge_readiness_to_materialised_seconds",
        ),
        "materialised_to_completion_seconds_if_available": (
            None
            if completion_dt is None
            else _duration(
                merged,
                completion_dt,
                "derived_metrics.materialised_to_completion_seconds_if_available",
            )
        ),
    }

    failures = sorted(set(prewarm_failures + reuse_failures))
    if failures:
        classification = f"AA0_PREWARM_{failures[0]}"
    elif not prewarm_executed or not controls_pass:
        classification = "AA0_PREWARM_CORRECTNESS_BLOCKED"
    elif metrics["pr_open_to_materialised_seconds"] <= 60.0:
        classification = "POST_DIASI_AA0_PREWARM_PASS_SUB60"
    else:
        classification = "AA0_PREWARM_FUNCTIONAL_PASS_PERFORMANCE_MISS"

    output_completion = {
        "physical_materialisation_receipt": _receipt_id(
            receipts.get("physical_materialisation_receipt"),
            "completion.receipts.physical_materialisation_receipt",
        ),
        "packet_completion_receipt": _receipt_id(
            receipts.get("packet_completion_receipt"),
            "completion.receipts.packet_completion_receipt",
        ),
        "devobs_receipt": _receipt_id(
            receipts.get("devobs_receipt"), "completion.receipts.devobs_receipt"
        ),
        "completion_proof": _receipt_id(
            receipts.get("completion_proof"), "completion.receipts.completion_proof"
        ),
        "completion_timestamp_if_available": completion_timestamp,
        "completion_timestamp_source": timestamp_source,
    }

    return {
        "schema": REPORT_SCHEMA,
        "packet_id": packet_id,
        "pip_id": identity["pip_id"],
        "candidate_head_sha": candidate,
        "qualified_prospective_tree": identity["qualified_prospective_tree"],
        "qualification_id": identity["qualification_id"],
        "qualification_generation_id": identity["qualification_generation_id"],
        "aa0_harness_id": identity["aa0_harness_id"],
        "prewarm": {
            **prewarm_workflow,
            "repository_assurance_disposition": prewarm_surfaces["repository"]["disposition"],
            "unittest_parity_disposition": prewarm_surfaces["unittest_parity"]["disposition"],
            "runner_parity_disposition": prewarm_surfaces["runner_parity"]["disposition"],
            "canonical_reference_executed": prewarm_executed,
        },
        "pr": {
            "number": pr_number,
            "opened_at": opened_text,
            "head_sha": candidate,
            "assurance_workflow_run_id": pr_workflow["workflow_run_id"],
            "cache_reuse": pr_surfaces,
            "canonical_shard_jobs": canonical_shards,
        },
        "fresh_assurance": fresh,
        "materialisation": {
            "merged_at": merged_text,
            "merge_commit": _sha(
                materialisation.get("merge_commit"), "materialisation.merge_commit", SHA40
            ),
            "prospective_tree": prospective_tree,
            "physical_tree": physical_tree,
            "exact_tree_equality": True,
        },
        "completion": output_completion,
        "derived_metrics": metrics,
        "controls": {
            "repository_protection_active": controls.get("repository_protection_active"),
            "ruleset_id": _integer(controls.get("ruleset_id"), "controls.ruleset_id", minimum=1),
            "bypass_actor_count": controls.get("bypass_actor_count"),
            "physical_writer_count": controls.get("physical_writer_count"),
            "racpr_mode": controls.get("racpr_mode"),
            "diasi_runtime_use_count": controls.get("diasi_runtime_use_count"),
            "pes_runtime_use_count": controls.get("pes_runtime_use_count"),
            "cers_runtime_use_count": controls.get("cers_runtime_use_count"),
            "authority_delta": "NONE",
        },
        "classification": classification,
        "warnings": sorted(warnings, key=lambda row: (row["code"], row["field"])),
    }


def canonical_json(report: Mapping[str, Any]) -> str:
    return json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True, help="Read-only normalized evidence JSON")
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.evidence.read_text(encoding="utf-8"))
        report = compile_latency_report(_mapping(raw, "evidence"))
    except (OSError, json.JSONDecodeError, LatencyReportError) as exc:
        parser.error(str(exc))
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
