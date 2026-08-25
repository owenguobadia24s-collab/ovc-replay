from __future__ import annotations

from dataclasses import asdict
import json
import time
from typing import Any, Mapping

from ovc.development.skills.vit_late_binding import BaseIndependentAssuranceGeneration
import tools.ci.prvitr_live_admission as live

PILOT_WORKFLOW = "rac-delta-assurance-pilot.yml"
PILOT_ELIGIBILITY_JOB = "RAC pilot eligibility"
PILOT_ADMISSION_JOB = "RAC pilot admission"
PILOT_READY_POLICY_ID = "PRVITR-RAC-PILOT-READY-POLICY-v0.1"
WAIT_SECONDS = 5
WAIT_TIMEOUT_SECONDS = 22 * 60


def pilot_job_disposition(
    eligibility: Mapping[str, Any] | None,
    admission: Mapping[str, Any] | None,
) -> str:
    """Pure fail-closed disposition used by tests and the live selector."""
    if eligibility is None:
        return "PENDING"
    if str(eligibility.get("status", "")) != "completed":
        return "PENDING"
    eligibility_conclusion = str(eligibility.get("conclusion", ""))
    if eligibility_conclusion != "success":
        return "BLOCK"
    if admission is None or str(admission.get("status", "")) != "completed":
        return "PENDING"
    conclusion = str(admission.get("conclusion", ""))
    if conclusion == "success":
        return "PILOT"
    if conclusion == "skipped":
        return "FALLBACK"
    return "BLOCK"


def _wait_pilot(pr_number: int, head_sha: str) -> tuple[str, Mapping[str, Any], Mapping[str, Any] | None]:
    deadline = time.time() + WAIT_TIMEOUT_SECONDS
    while time.time() < deadline:
        run = live._exact_run(PILOT_WORKFLOW, pr_number, head_sha)
        if run is None:
            time.sleep(WAIT_SECONDS)
            continue
        jobs = live._jobs(int(run["id"]))
        eligibility = live._job_by_name(jobs, PILOT_ELIGIBILITY_JOB)
        admission = live._job_by_name(jobs, PILOT_ADMISSION_JOB)
        disposition = pilot_job_disposition(eligibility, admission)
        if disposition == "PENDING":
            time.sleep(WAIT_SECONDS)
            continue
        return disposition, run, admission
    raise RuntimeError("RAC_PILOT_READY_TIMEOUT")


def _wait_required_job(workflow: str, pr_number: int, head_sha: str, job_name: str) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    deadline = time.time() + WAIT_TIMEOUT_SECONDS
    while time.time() < deadline:
        run = live._exact_run(workflow, pr_number, head_sha)
        if run is None:
            time.sleep(WAIT_SECONDS)
            continue
        job = live._job_by_name(live._jobs(int(run["id"])), job_name)
        if job is None or str(job.get("status", "")) != "completed":
            time.sleep(WAIT_SECONDS)
            continue
        if str(job.get("conclusion", "")) != "success":
            raise RuntimeError(f"RAC_PILOT_REQUIRED_JOB_FAILED:{workflow}:{job_name}:{run.get('id')}")
        return run, job
    raise RuntimeError(f"RAC_PILOT_REQUIRED_JOB_TIMEOUT:{workflow}:{job_name}")


def command_ready() -> int:
    event = live._event()
    event_pr = live._event_pr(event)
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    event_head = str((event_pr.get("head") or {}).get("sha", ""))
    live_pr = live._live_pr(pr_number)
    live_head = str((live_pr.get("head") or {}).get("sha", ""))
    if live_head != event_head:
        raise RuntimeError(f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:event {event_head}, live {live_head}")
    if str(live_pr.get("state", "")) != "open":
        raise RuntimeError(f"OVC_SIQ_PR_NOT_OPEN:{pr_number}")

    disposition, pilot_run, admission_job = _wait_pilot(pr_number, live_head)
    if disposition == "FALLBACK":
        print("OVC_RAC_PILOT_READY_DISPOSITION=FALLBACK_CANONICAL_REFERENCE")
        return live.command_ready()
    if disposition != "PILOT" or admission_job is None:
        raise RuntimeError("RAC_PILOT_ASSURANCE_BLOCKED")

    record, lineage, authority, frontier, qualification_id = live._payload_context(live_pr)
    tests_run, vit_job = _wait_required_job(
        live.TESTS_WORKFLOW,
        pr_number,
        live_head,
        "VIT routing preflight",
    )
    tiered_run, profile_job = _wait_required_job(
        live.TIERED_WORKFLOW,
        pr_number,
        live_head,
        live.PROFILE_JOB_NAME,
    )

    refreshed = live._live_pr(pr_number)
    refreshed_head = str((refreshed.get("head") or {}).get("sha", ""))
    if refreshed_head != live_head:
        raise RuntimeError(f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:qualified {live_head}, live {refreshed_head}")
    _, refreshed_lineage, refreshed_authority, refreshed_frontier, refreshed_qualification_id = live._payload_context(refreshed)
    if refreshed_qualification_id != qualification_id:
        raise RuntimeError("VIT_QUALIFICATION_CHANGED_DURING_ASSURANCE")
    if (
        refreshed_lineage.pip_id != lineage.pip_id
        or refreshed_authority != authority
        or refreshed_frontier != frontier
    ):
        raise RuntimeError("VIT_QUALIFICATION_CONTENT_CHANGED_DURING_ASSURANCE")

    source_run_ids = (
        f"github-actions-run:{tests_run['id']}:job:{vit_job['id']}",
        f"github-actions-run:{tiered_run['id']}:job:{profile_job['id']}",
        f"github-actions-run:{pilot_run['id']}:job:{admission_job['id']}",
    )
    generation = BaseIndependentAssuranceGeneration(
        pip_id=lineage.pip_id,
        candidate_head_sha=live_head,
        candidate_head_tree=live._tree(live_head),
        authority_manifest_id=authority,
        dependency_frontier_id=frontier,
        policy_id=PILOT_READY_POLICY_ID,
        source_run_ids=source_run_ids,
    )
    print("OVC_BASE_INDEPENDENT_ASSURANCE_GENERATION=" + json.dumps(asdict(generation), sort_keys=True, separators=(",", ":")))
    live._write_output("head_sha", live_head)
    live._write_output("pip_id", lineage.pip_id)
    live._write_output("qualification_id", qualification_id)
    live._write_output("assurance_generation_id", generation.generation_id)
    live._write_output("tests_run_id", str(tests_run["id"]))
    live._write_output("profile_run_id", str(tiered_run["id"]))
    print("OVC_RAC_PILOT_READY_DISPOSITION=PILOT_CERTIFICATE_ACCEPTED")
    print("OVC_RAC_PILOT_CANONICAL_REFERENCE=CONCURRENT_NOT_READY_BLOCKING")
    return 0


def main() -> int:
    return command_ready()


if __name__ == "__main__":
    raise SystemExit(main())
