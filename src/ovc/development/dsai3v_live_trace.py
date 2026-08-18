"""Observed-only DEVOBS trace assembly for eligible DSAI3V completions.

This module converts already-fetched GitHub Actions timing payloads into the
existing DevelopmentTrace/trace_summary representation. It does not infer
model-reasoning time, local-test time, remediation causality, or execution
activity that is absent from the supplied observations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from ovc.development.diagnostic_observability import (
    DevelopmentTrace,
    ingest_github_workflow_jobs,
)

TRACE_SCOPE = "INTEGRATION_ASSURANCE_TO_PHYSICAL_MERGE"


def _parse_utc(value: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _duration_ms(started_at: str, completed_at: str) -> int:
    value = int(round((_parse_utc(completed_at) - _parse_utc(started_at)).total_seconds() * 1000))
    if value < 0:
        raise ValueError("completed_at precedes started_at")
    return value


def build_observed_completion_trace(
    *,
    programme_id: str,
    packet_id: str,
    pr_number: int,
    head_sha: str,
    merged_at_utc: str,
    workflow_runs: Sequence[Mapping[str, Any]],
    jobs_by_run: Mapping[int, Sequence[Mapping[str, Any]]],
) -> dict[str, Any] | None:
    """Build a scoped trace from observed GitHub Actions timestamps only.

    ``total_wall_ms`` is deliberately scoped to the interval from the earliest
    observed PR-head Actions job creation to the observed physical merge time.
    It is not represented as total human/model packet-development time.
    """
    observed_starts: list[str] = []
    successful_completions: list[str] = []
    normalized_runs: list[Mapping[str, Any]] = []

    for run in workflow_runs:
        run_id_raw = run.get("id")
        if isinstance(run_id_raw, bool):
            continue
        try:
            run_id = int(run_id_raw)
        except (TypeError, ValueError):
            continue
        jobs = tuple(dict(job) for job in jobs_by_run.get(run_id, ()))
        if not jobs:
            continue
        normalized_runs.append(run)
        for job in jobs:
            started = job.get("created_at") or job.get("started_at")
            completed = job.get("completed_at")
            if started:
                observed_starts.append(str(started))
            if completed and str(job.get("conclusion", "")).lower() == "success":
                successful_completions.append(str(completed))

    if not observed_starts:
        return None

    started_at = min(observed_starts, key=_parse_utc)
    merged_at = str(merged_at_utc)
    if _parse_utc(merged_at) < _parse_utc(started_at):
        raise ValueError("physical merge precedes observed assurance start")

    trace = DevelopmentTrace(
        run_id=f"DSAI3V:{TRACE_SCOPE}:PR{int(pr_number)}:{head_sha}",
        programme_id=programme_id,
        packet_id=packet_id,
        started_at_utc=started_at,
    )
    for run in normalized_runs:
        run_id = int(run["id"])
        ingest_github_workflow_jobs(
            trace,
            workflow_run=run,
            jobs=jobs_by_run.get(run_id, ()),
        )

    latest_green: str | None = None
    if successful_completions:
        latest_green = max(successful_completions, key=_parse_utc)
        if _parse_utc(merged_at) >= _parse_utc(latest_green):
            trace.record_external_interval(
                category="OTHER",
                operation="workflow_green_to_physical_merge_elapsed",
                started_at_utc=latest_green,
                completed_at_utc=merged_at,
                activity_class="WAIT",
                source="GITHUB_PULL_REQUEST",
                evidence_class="MEASURED",
                evidence_ref=f"github-pr:{int(pr_number)}",
                metadata={
                    "trace_scope": TRACE_SCOPE,
                    "head_sha": str(head_sha),
                    "interpretation": "ELAPSED_ONLY_NOT_CAUSE_ATTRIBUTED",
                },
            )

    summary = trace.finish_run(completed_at_utc=merged_at)
    workflow_green_to_materialisation_ms = (
        _duration_ms(latest_green, merged_at) if latest_green is not None else None
    )
    return {
        "trace_scope": TRACE_SCOPE,
        "trace_summary": summary,
        "trace_events": list(trace.events),
        "async_assurance_metrics": {
            "workflow_green_to_materialisation_ms": workflow_green_to_materialisation_ms,
        },
        "evidence_rule": "OBSERVED_GITHUB_TIMESTAMPS_ONLY_NO_CAUSAL_INFERENCE",
        "authority_effect": "NONE",
    }
