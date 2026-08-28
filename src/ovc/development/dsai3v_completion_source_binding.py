"""Direct GitHub source binding for canonical DSAI3V completion receipt v2.

The helper consumes already-fetched GitHub PR/workflow/job payloads. It does not
perform I/O and does not infer timestamps from adjacent events. Missing job
surfaces remain absent; PR creation and merge timestamps are mandatory because
they are the authoritative endpoints for PR_OPEN_TO_MATERIALISED.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.development.dsai3v_completion_observability_v2 import (
    CANONICAL_COMPLETION_SCHEMA_V2,
)


_JOB_TIMING_FIELDS = {
    "canonical pytest shard assurance plan": "aa0_reuse_observed_at_utc",
    "OVC profile assurance": "profile_passed_at_utc",
    "SIQ READY admission": "siq_ready_at_utc",
    "OVC merge readiness": "merge_readiness_passed_at_utc",
}


def _job_observation(
    *,
    workflow_runs: Sequence[Mapping[str, Any]],
    jobs_by_run: Mapping[int, Sequence[Mapping[str, Any]]],
    job_name: str,
) -> tuple[int, Mapping[str, Any]] | None:
    candidates: list[tuple[int, int, Mapping[str, Any]]] = []
    for run in workflow_runs:
        try:
            run_id = int(run.get("id"))
        except (TypeError, ValueError):
            continue
        for job in jobs_by_run.get(run_id, ()):
            if (
                str(job.get("name", "")) != job_name
                or str(job.get("status", "")) != "completed"
                or str(job.get("conclusion", "")) != "success"
                or not job.get("completed_at")
            ):
                continue
            try:
                job_id = int(job.get("id"))
            except (TypeError, ValueError):
                continue
            candidates.append((job_id, run_id, dict(job)))
    if not candidates:
        return None
    _, run_id, job = max(candidates, key=lambda row: row[0])
    return run_id, job


def build_github_completion_source_binding(
    *,
    pr: Mapping[str, Any],
    workflow_runs: Sequence[Mapping[str, Any]],
    jobs_by_run: Mapping[int, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Return authoritative v2 timing source rows and AA0 identifiers.

    The PR's ``created_at`` and ``merged_at`` fields are used directly. Assurance
    event times are taken only from the corresponding successful GitHub Actions
    jobs. No source row is synthesized when its exact job is unavailable.
    """
    try:
        pr_number = int(pr["number"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("GitHub PR number is required for completion source binding") from exc
    pr_opened = pr.get("created_at")
    merged_at = pr.get("merged_at")
    if not isinstance(pr_opened, str) or not pr_opened:
        raise ValueError("GitHub PR created_at is required for completion source binding")
    if not isinstance(merged_at, str) or not merged_at:
        raise ValueError("GitHub PR merged_at is required for completion source binding")

    timing_sources: list[dict[str, str]] = [
        {
            "field": "pr_opened_at_utc",
            "source_type": "GITHUB_PR",
            "source_id": f"github:pr:{pr_number}:created_at",
            "observed_at_utc": pr_opened,
            "authority": "OBSERVATIONAL_ONLY",
        },
        {
            "field": "physical_materialised_at_utc",
            "source_type": "GITHUB_PR",
            "source_id": f"github:pr:{pr_number}:merged_at",
            "observed_at_utc": merged_at,
            "authority": "OBSERVATIONAL_ONLY",
        },
    ]

    pr_assurance_run_id: str | None = None
    canonical_shards_executed: bool | None = None
    for job_name, field in _JOB_TIMING_FIELDS.items():
        observed = _job_observation(
            workflow_runs=workflow_runs,
            jobs_by_run=jobs_by_run,
            job_name=job_name,
        )
        if observed is None:
            continue
        run_id, job = observed
        job_id = int(job["id"])
        timing_sources.append(
            {
                "field": field,
                "source_type": "GITHUB_WORKFLOW_JOB",
                "source_id": f"github:actions:run:{run_id}:job:{job_id}",
                "observed_at_utc": str(job["completed_at"]),
                "authority": "OBSERVATIONAL_ONLY",
            }
        )
        if job_name == "canonical pytest shard assurance plan":
            pr_assurance_run_id = str(run_id)
            shard_jobs = jobs_by_run.get(run_id, ())
            canonical_shards_executed = any(
                str(row.get("name", "")).startswith("canonical pytest shard ")
                and str(row.get("name", ""))
                not in {
                    "canonical pytest shard assurance plan",
                    "canonical pytest shard manifest",
                }
                and str(row.get("conclusion", "")) == "success"
                for row in shard_jobs
            )

    aa0_observability: dict[str, Any] = {}
    if pr_assurance_run_id is not None:
        aa0_observability["pr_assurance_run_id"] = pr_assurance_run_id
    if canonical_shards_executed is not None:
        aa0_observability["canonical_shards_executed"] = canonical_shards_executed
    return {
        "timing_sources": tuple(timing_sources),
        "aa0_observability": aa0_observability,
    }


def has_source_bound_pr_to_materialised(receipt: Mapping[str, Any]) -> bool:
    """True when a v2 receipt safely evaluates PR_OPEN_TO_MATERIALISED."""
    if receipt.get("schema") != CANONICAL_COMPLETION_SCHEMA_V2:
        return False
    timing = receipt.get("timing")
    if not isinstance(timing, Mapping):
        return False
    derived = timing.get("derived_latency_ms")
    return bool(
        timing.get("pr_opened_at_utc")
        and timing.get("physical_materialised_at_utc")
        and isinstance(derived, Mapping)
        and derived.get("pr_open_to_materialised_ms") is not None
    )
