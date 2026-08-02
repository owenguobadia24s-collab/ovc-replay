from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
import zipfile


class AdmissionEvidenceError(ValueError):
    pass


REQUIRED_RUN_FIELDS = {
    "id", "workflow_id", "name", "event", "path", "status", "conclusion",
    "created_at", "run_started_at", "updated_at", "check_suite_id",
}
REQUIRED_JOB_FIELDS = {
    "id", "name", "status", "conclusion", "started_at", "completed_at",
}
SECRET_PATTERNS = {
    "github_token": re.compile(rb"(ghp_|github_pat_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_]{10,}"),
    "private_key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "authorization": re.compile(rb"(?i)authorization\s*[:=]\s*(bearer|token|basic)\s+[A-Za-z0-9._~+/=-]{8,}"),
    "aws_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "openai_key": re.compile(rb"sk-(proj-)?[A-Za-z0-9_-]{20,}"),
}


def parse_time(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise AdmissionEvidenceError("timestamp must be a non-empty string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def exact_seconds(start: str, end: str, label: str) -> float:
    value = (parse_time(end) - parse_time(start)).total_seconds()
    if value < 0:
        raise AdmissionEvidenceError(f"{label} has negative duration")
    return round(value, 7)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def require_fields(record: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(field for field in fields if record.get(field) is None)
    if missing:
        raise AdmissionEvidenceError(f"{label} missing exact fields: {', '.join(missing)}")


def _safe_zip_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise AdmissionEvidenceError(f"unsafe zip path: {name}")
    return normalized


def _flatten_pages(value: Any, key: str, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise AdmissionEvidenceError(f"{label} must be a list of pages")
    output: list[dict[str, Any]] = []
    for page in value:
        if not isinstance(page, dict) or not isinstance(page.get(key), list):
            raise AdmissionEvidenceError(f"{label} page missing {key}")
        output.extend(page[key])
    return output


def verify_zip(evidence_zip: Path) -> dict[str, Any]:
    raw_zip = evidence_zip.read_bytes()
    zip_sha256 = hashlib.sha256(raw_zip).hexdigest()
    with zipfile.ZipFile(evidence_zip, "r") as archive:
        names = [_safe_zip_name(name) for name in archive.namelist()]
        if len(names) != len(set(names)):
            raise AdmissionEvidenceError("duplicate zip member")
        required = {"SHA256_MANIFEST.json", "SHA256_MANIFEST.sha256.txt", "capture-metadata.json"}
        if not required.issubset(set(names)):
            raise AdmissionEvidenceError("zip missing manifest or capture metadata")
        manifest_bytes = archive.read("SHA256_MANIFEST.json")
        manifest = json.loads(manifest_bytes)
        if not isinstance(manifest, list):
            raise AdmissionEvidenceError("manifest must be a list")
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        recorded_manifest_sha = archive.read("SHA256_MANIFEST.sha256.txt").decode("utf-8").strip()
        if recorded_manifest_sha != manifest_sha256:
            raise AdmissionEvidenceError("manifest SHA-256 mismatch")

        entries: dict[str, dict[str, Any]] = {}
        for item in manifest:
            if not isinstance(item, dict):
                raise AdmissionEvidenceError("invalid manifest entry")
            path = _safe_zip_name(str(item.get("relative_path", "")))
            if path in entries:
                raise AdmissionEvidenceError(f"duplicate manifest path: {path}")
            entries[path] = item

        evidence_names = set(names) - {"SHA256_MANIFEST.json", "SHA256_MANIFEST.sha256.txt"}
        if evidence_names != set(entries):
            raise AdmissionEvidenceError("manifest membership mismatch")

        secret_hits: list[dict[str, str]] = []
        for name in sorted(evidence_names):
            payload = archive.read(name)
            item = entries[name]
            if len(payload) != int(item.get("bytes", -1)):
                raise AdmissionEvidenceError(f"byte-size mismatch: {name}")
            digest = hashlib.sha256(payload).hexdigest()
            if digest != item.get("sha256"):
                raise AdmissionEvidenceError(f"SHA-256 mismatch: {name}")
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(payload):
                    secret_hits.append({"path": name, "pattern": label})
        if secret_hits:
            raise AdmissionEvidenceError(f"credential-like material found: {secret_hits}")

        return {
            "zip_sha256": zip_sha256,
            "zip_bytes": len(raw_zip),
            "manifest_sha256": manifest_sha256,
            "manifest_entries": len(manifest),
            "manifest_verified": True,
            "secret_scan": "PASS",
        }


def classify(name: str, registry: dict[str, Any]) -> str:
    matches = [
        label for label, names in registry["classifications"].items()
        if name in names
    ]
    if len(matches) != 1:
        raise AdmissionEvidenceError(f"workflow {name!r} has {len(matches)} classifications")
    return matches[0]


def normalize_job(job: dict[str, Any], run_id: int) -> tuple[dict[str, Any], bool]:
    require_fields(job, REQUIRED_JOB_FIELDS, f"job {job.get('id')} in run {run_id}")
    started = parse_time(job["started_at"])
    completed = parse_time(job["completed_at"])
    inverted = completed < started
    if inverted and job["conclusion"] != "skipped":
        raise AdmissionEvidenceError(f"job {job['id']} in run {run_id} has negative duration")
    if inverted:
        duration = None
        timing_status = "NOT_EVALUABLE_SKIPPED_INVERTED_API_TIMESTAMPS"
    else:
        duration = round((completed - started).total_seconds(), 7)
        timing_status = "EXACT"
    return {
        "id": int(job["id"]),
        "name": job["name"],
        "status": job["status"],
        "conclusion": job["conclusion"],
        "started_at": job["started_at"],
        "completed_at": job["completed_at"],
        "duration_seconds": duration,
        "timing_status": timing_status,
    }, inverted


def load_subject(archive: zipfile.ZipFile, subject_dir: str, subject_spec: dict[str, Any],
                 registry: dict[str, Any]) -> dict[str, Any]:
    summary = json.loads(archive.read(f"raw/{subject_dir}/subject-summary.json"))
    if summary.get("commit_sha") != subject_spec["commit_sha"]:
        raise AdmissionEvidenceError(f"{subject_dir} commit SHA mismatch")

    runs = _flatten_pages(
        json.loads(archive.read(f"raw/{subject_dir}/workflow-runs.pages.json")),
        "workflow_runs",
        f"{subject_dir} workflow runs",
    )
    if len(runs) != int(summary.get("workflow_run_count", -1)):
        raise AdmissionEvidenceError(f"{subject_dir} run count mismatch")

    suites = _flatten_pages(
        json.loads(archive.read(f"raw/{subject_dir}/check-suites.pages.json")),
        "check_suites",
        f"{subject_dir} check suites",
    )
    check_runs = _flatten_pages(
        json.loads(archive.read(f"raw/{subject_dir}/check-runs.pages.json")),
        "check_runs",
        f"{subject_dir} check runs",
    )
    suites_by_id = {int(item["id"]): item for item in suites}
    check_runs_by_suite: dict[int, list[dict[str, Any]]] = {}
    for item in check_runs:
        suite = item.get("check_suite") or {}
        if suite.get("id") is not None:
            check_runs_by_suite.setdefault(int(suite["id"]), []).append(item)

    required_sources = registry["required_context_sources"]
    rows: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []

    for run in runs:
        require_fields(run, REQUIRED_RUN_FIELDS, f"run {run.get('id')}")
        run_id = int(run["id"])
        jobs_path = f"raw/{subject_dir}/jobs/{run_id}.jobs.pages.json"
        jobs = _flatten_pages(json.loads(archive.read(jobs_path)), "jobs", f"run {run_id} jobs")
        if not jobs:
            raise AdmissionEvidenceError(f"run {run_id} has no job evidence")

        normalized_jobs: list[dict[str, Any]] = []
        exact_job_times: list[tuple[datetime, datetime]] = []
        for job in jobs:
            normalized, inverted = normalize_job(job, run_id)
            normalized_jobs.append(normalized)
            if inverted:
                anomalies.append({
                    "type": "SKIPPED_JOB_INVERTED_API_TIMESTAMPS",
                    "run_id": run_id,
                    "job_id": normalized["id"],
                    "workflow_name": run["name"],
                    "started_at": normalized["started_at"],
                    "completed_at": normalized["completed_at"],
                    "resolution": "DURATION_NOT_EVALUABLE_NO_ESTIMATE_USED",
                })
            else:
                exact_job_times.append((parse_time(job["started_at"]), parse_time(job["completed_at"])))

        suite = suites_by_id.get(int(run["check_suite_id"]))
        if not suite:
            raise AdmissionEvidenceError(f"run {run_id} missing check suite")
        suite_app = suite.get("app") or {}
        run_checks = check_runs_by_suite.get(int(run["check_suite_id"]), [])
        run_check_apps = sorted({
            (int((item.get("app") or {}).get("id")), (item.get("app") or {}).get("slug"))
            for item in run_checks if (item.get("app") or {}).get("id") is not None
        })
        check_source = {
            "check_suite_id": int(run["check_suite_id"]),
            "suite_app_id": suite_app.get("id"),
            "suite_app_slug": suite_app.get("slug"),
            "check_run_apps": [
                {"app_id": app_id, "app_slug": app_slug}
                for app_id, app_slug in run_check_apps
            ],
        }

        if run["name"] in required_sources:
            expected = required_sources[run["name"]]
            if (
                check_source["suite_app_id"] != expected["app_id"]
                or check_source["suite_app_slug"] != expected["app_slug"]
                or not any(
                    item["app_id"] == expected["app_id"] and item["app_slug"] == expected["app_slug"]
                    for item in check_source["check_run_apps"]
                )
            ):
                raise AdmissionEvidenceError(f"required context {run['name']!r} source identity mismatch")

        queue_seconds = exact_seconds(run["created_at"], run["run_started_at"], f"run {run_id} queue")
        execution_seconds = exact_seconds(run["run_started_at"], run["updated_at"], f"run {run_id} execution")
        if exact_job_times:
            first_start = min(item[0] for item in exact_job_times)
            last_complete = max(item[1] for item in exact_job_times)
            job_span_seconds: float | None = round((last_complete - first_start).total_seconds(), 7)
        else:
            job_span_seconds = None

        classification = classify(run["name"], registry)
        rows.append({
            "run_id": run_id,
            "workflow_id": int(run["workflow_id"]),
            "workflow_name": run["name"],
            "workflow_path": run["path"],
            "conclusion": run["conclusion"],
            "classification": classification,
            "queue_seconds": queue_seconds,
            "execution_seconds": execution_seconds,
            "job_count": len(normalized_jobs),
            "job_span_seconds": job_span_seconds,
            "job_timing_status": (
                "NOT_EVALUABLE_SKIPPED_INVERSION_PRESENT"
                if any(item["timing_status"] != "EXACT" for item in normalized_jobs)
                else "EXACT"
            ),
            "check_source": check_source if classification == "REQUIRED" else None,
        })

    rows.sort(key=lambda item: item["run_id"])
    required_names = set(required_sources)
    present_names = {item["workflow_name"] for item in rows}
    if not required_names.issubset(present_names):
        raise AdmissionEvidenceError(f"{subject_dir} required contexts absent")

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    earliest_created = min(parse_time(item["created_at"]) for item in runs)
    latest_updated = max(parse_time(item["updated_at"]) for item in runs)
    duplicate_full_suites = max(
        0,
        sum(1 for item in rows if item["workflow_name"] in registry["complete_suite_contexts"]) - 1,
    )
    return {
        "subject_id": subject_spec["subject_id"],
        "pull_request": int(subject_spec["pull_request"]),
        "commit_sha": subject_spec["commit_sha"],
        "runs": rows,
        "timing_anomalies": sorted(anomalies, key=lambda item: (item["run_id"], item["job_id"])),
        "summary": {
            "run_count": len(rows),
            "classification_counts": dict(sorted(counts.items())),
            "unrelated_ratio": counts.get("UNRELATED", 0) / len(rows),
            "duplicate_complete_suite_runs": duplicate_full_suites,
            "queue_seconds_total": round(sum(item["queue_seconds"] for item in rows), 7),
            "execution_seconds_total": round(sum(item["execution_seconds"] for item in rows), 7),
            "critical_path_seconds": round((latest_updated - earliest_created).total_seconds(), 7),
            "skipped_job_timing_anomalies": len(anomalies),
        },
    }


def build(evidence_zip: Path, registry: dict[str, Any], external_reference: dict[str, Any]) -> dict[str, Any]:
    verification = verify_zip(evidence_zip)
    subjects: list[dict[str, Any]] = []
    seen_runs: set[tuple[str, int]] = set()
    with zipfile.ZipFile(evidence_zip, "r") as archive:
        for spec in registry["subjects"]:
            subject = load_subject(archive, spec["evidence_directory"], spec, registry)
            for run in subject["runs"]:
                key = (subject["commit_sha"], run["run_id"])
                if key in seen_runs:
                    raise AdmissionEvidenceError(f"duplicate run: {key}")
                seen_runs.add(key)
            subjects.append(subject)

    counts: dict[str, int] = {}
    all_runs = [run for subject in subjects for run in subject["runs"]]
    for run in all_runs:
        counts[run["classification"]] = counts.get(run["classification"], 0) + 1
    anomalies = [item for subject in subjects for item in subject["timing_anomalies"]]
    unrelated_failed = sum(
        1 for run in all_runs
        if run["classification"] == "UNRELATED" and run["conclusion"] == "failure"
    )

    result = {
        "schema": "ovc-da2-ci-admission-baseline/v2",
        "baseline_id": "OVC.DA2.CI.ADMISSION.BASELINE.v2",
        "programme_id": "OVC-DEV-ACCEL-v0.2",
        "packet_id": "DA2-00",
        "gate_id": "DA2-G0",
        "operator_decision_id": "DA2-G0.OPERATOR.PASS.20260802T213600+0100",
        "status": "PASS",
        "authority_delta": "READ_ONLY_WORKFLOW_TRIGGER_AND_CHECK_PROVENANCE_AUDIT_WITH_COMPACT_REPOSITORY_EVIDENCE",
        "ruleset": registry["ruleset"],
        "subjects": subjects,
        "aggregate": {
            "run_count": len(all_runs),
            "classification_counts": dict(sorted(counts.items())),
            "unrelated_ratio": counts.get("UNRELATED", 0) / len(all_runs),
            "unrelated_failed_runs": unrelated_failed,
            "duplicate_complete_suite_runs": sum(
                subject["summary"]["duplicate_complete_suite_runs"] for subject in subjects
            ),
            "queue_seconds_total": round(sum(run["queue_seconds"] for run in all_runs), 7),
            "execution_seconds_total": round(sum(run["execution_seconds"] for run in all_runs), 7),
            "skipped_job_timing_anomalies": len(anomalies),
            "required_runs": [
                {
                    "pull_request": subject["pull_request"],
                    "run_id": run["run_id"],
                    "workflow_name": run["workflow_name"],
                    "workflow_path": run["workflow_path"],
                    "queue_seconds": run["queue_seconds"],
                    "execution_seconds": run["execution_seconds"],
                    "check_source": run["check_source"],
                }
                for subject in subjects
                for run in subject["runs"]
                if run["classification"] == "REQUIRED"
            ],
        },
        "reproducibility": {
            **verification,
            "raw_api_fields_complete": True,
            "required_source_identities_complete": True,
            "estimated_values_used": False,
            "skipped_job_inversions_preserved_as_not_evaluable": len(anomalies),
            "external_reference": external_reference,
        },
        "qa_recommendation": "PASS",
        "workflow_mutation_authority": "DENIED",
        "ruleset_mutation_authority": "DENIED",
        "rollback": "Supersede non-destructively; preserve raw evidence, hashes, classifications, QA and decisions.",
    }
    result["logical_sha256"] = hashlib.sha256(canonical_bytes(result)).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-zip", required=True, type=Path)
    parser.add_argument("--classifications", required=True, type=Path)
    parser.add_argument("--external-reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    registry = json.loads(args.classifications.read_text(encoding="utf-8"))
    external_reference = json.loads(args.external_reference.read_text(encoding="utf-8"))
    result = build(args.evidence_zip, registry, external_reference)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
