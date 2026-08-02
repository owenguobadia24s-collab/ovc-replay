from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_CONTEXTS = {"tests", "OVC tiered test selection shadow"}
REQUIRED_RUN_FIELDS = {
    "id", "workflow_id", "name", "event", "path", "status", "conclusion",
    "created_at", "run_started_at", "updated_at",
}
REQUIRED_JOB_FIELDS = {
    "id", "name", "status", "conclusion", "started_at", "completed_at",
}


class AdmissionEvidenceError(ValueError):
    pass


def parse_time(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise AdmissionEvidenceError("timestamp must be a non-empty string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seconds(start: str, end: str) -> float:
    result = (parse_time(end) - parse_time(start)).total_seconds()
    if result < 0:
        raise AdmissionEvidenceError("negative duration")
    return round(result, 7)


def require_fields(record: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(field for field in fields if record.get(field) is None)
    if missing:
        raise AdmissionEvidenceError(f"{label} missing exact fields: {', '.join(missing)}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def classify(name: str, registry: dict[str, Any]) -> str:
    matches = [
        label for label, names in registry["classifications"].items()
        if name in names
    ]
    if len(matches) != 1:
        raise AdmissionEvidenceError(f"workflow {name!r} has {len(matches)} classifications")
    return matches[0]


def build(subjects: list[dict[str, Any]], classification_registry: dict[str, Any]) -> dict[str, Any]:
    output_subjects: list[dict[str, Any]] = []
    seen_global: set[tuple[str, int]] = set()

    for subject in subjects:
        sha = subject["commit_sha"]
        raw_runs = subject["workflow_runs"]
        rows: list[dict[str, Any]] = []
        for run in raw_runs:
            require_fields(run, REQUIRED_RUN_FIELDS, f"run {run.get('id')}")
            key = (sha, int(run["id"]))
            if key in seen_global:
                raise AdmissionEvidenceError(f"duplicate run: {key}")
            seen_global.add(key)

            jobs = run.get("jobs")
            if not isinstance(jobs, list) or not jobs:
                raise AdmissionEvidenceError(f"run {run['id']} has no job evidence")
            for job in jobs:
                require_fields(job, REQUIRED_JOB_FIELDS, f"job {job.get('id')}")

            source = run.get("check_source")
            if run["name"] in REQUIRED_CONTEXTS:
                if not isinstance(source, dict) or source.get("app_id") is None:
                    raise AdmissionEvidenceError(
                        f"required context {run['name']!r} missing accepted app identity"
                    )

            earliest_job = min(parse_time(job["started_at"]) for job in jobs)
            latest_job = max(parse_time(job["completed_at"]) for job in jobs)
            queue_seconds = seconds(run["created_at"], run["run_started_at"])
            execution_seconds = seconds(run["run_started_at"], run["updated_at"])
            job_execution_seconds = round((latest_job - earliest_job).total_seconds(), 7)

            rows.append({
                "run_id": int(run["id"]),
                "workflow_id": int(run["workflow_id"]),
                "workflow_name": run["name"],
                "workflow_path": run["path"],
                "event": run["event"],
                "status": run["status"],
                "conclusion": run["conclusion"],
                "classification": classify(run["name"], classification_registry),
                "created_at": run["created_at"],
                "run_started_at": run["run_started_at"],
                "updated_at": run["updated_at"],
                "queue_seconds": queue_seconds,
                "execution_seconds": execution_seconds,
                "job_execution_seconds": job_execution_seconds,
                "check_source": source,
                "jobs": sorted(jobs, key=lambda x: int(x["id"])),
            })

        rows.sort(key=lambda x: x["run_id"])
        names = {row["workflow_name"] for row in rows}
        if not REQUIRED_CONTEXTS.issubset(names):
            raise AdmissionEvidenceError("required contexts absent")

        counts: dict[str, int] = {}
        for row in rows:
            counts[row["classification"]] = counts.get(row["classification"], 0) + 1
        output_subjects.append({
            "subject_id": subject["subject_id"],
            "pull_request": int(subject["pull_request"]),
            "commit_sha": sha,
            "runs": rows,
            "summary": {
                "run_count": len(rows),
                "classification_counts": counts,
                "unrelated_ratio": counts.get("UNRELATED", 0) / len(rows),
                "duplicate_complete_suite_runs": max(
                    0, sum(1 for row in rows if row["workflow_name"] in REQUIRED_CONTEXTS) - 1
                ),
            },
        })

    result = {
        "schema": "ovc-da2-ci-admission-baseline/v1",
        "baseline_id": "OVC.DA2.CI.ADMISSION.BASELINE.v1",
        "programme_id": "OVC-DEV-ACCEL-v0.2",
        "packet_id": "DA2-00",
        "gate_id": "DA2-G0",
        "status": "PASS",
        "subjects": output_subjects,
        "reproducibility": {
            "estimated_values_used": False,
            "raw_api_fields_complete": True,
            "required_source_identities_complete": True,
        },
        "qa_recommendation": "PASS",
        "workflow_mutation_authority": "DENIED",
        "ruleset_mutation_authority": "DENIED",
    }
    result["logical_sha256"] = hashlib.sha256(canonical_bytes(result)).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subjects", required=True, type=Path)
    parser.add_argument("--classifications", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    subjects = json.loads(args.subjects.read_text(encoding="utf-8"))
    classifications = json.loads(args.classifications.read_text(encoding="utf-8"))
    result = build(subjects["subjects"], classifications)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
