from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import time
from typing import Any, Mapping

from ovc.development.skills.repository_assurance_pilot import (
    build_pilot_certificate,
    classify_candidate,
    load_json,
    validate_pilot_policy,
)
from ovc.development.skills.vit_late_binding import BaseIndependentAssuranceGeneration
from tools.ci.vit_lineage_source import resolve_candidate_lineage
import tools.ci.prvitr_live_admission as live

PILOT_POLICY_PATH = Path(
    "registries/development/skills/REPOSITORY_ASSURANCE_PILOT_POLICY_v0_1.json"
)
PILOT_READY_POLICY_ID = "PRVITR-RAC-PILOT-READY-POLICY-v0.1"


def _wait_required_job(
    workflow: str,
    pr_number: int,
    head_sha: str,
    job_name: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Wait for one exact-head prerequisite without waiting on the reference suite.

    The bounded pilot inherits only the baseline-certified repository/parity claims.
    VIT routing and FINAL_HEAD profile assurance remain fresh prerequisites.  This
    helper deliberately composes the live admission module's current run and job
    state primitives instead of depending on a removed private compatibility API.
    """
    deadline = time.time() + live.READY_TIMEOUT_SECONDS
    while time.time() < deadline:
        run = live._exact_run(workflow, pr_number, head_sha)
        if run is None:
            time.sleep(10)
            continue
        state, jobs = live._run_job_state(run, (job_name,))
        if state == "FAIL":
            raise RuntimeError(f"RAC_PILOT_REQUIRED_JOB_FAILED:{workflow}:{job_name}:{run.get('id')}")
        if state == "PASS":
            return run, jobs[0]
        time.sleep(10)
    raise RuntimeError(f"RAC_PILOT_REQUIRED_JOB_TIMEOUT:{workflow}:{job_name}")


def _pilot_context(
    *,
    root: Path,
    live_pr: Mapping[str, Any],
    head_sha: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any] | None, Mapping[str, Any] | None]:
    policy = validate_pilot_policy(load_json(root / PILOT_POLICY_PATH))
    if policy["status"] != "ACTIVE_BOUNDED_PILOT":
        return policy, None, None

    baseline_path = str(policy.get("baseline_certificate_path") or "")
    baseline_file = root / baseline_path if baseline_path else None
    if baseline_file is None or not baseline_file.is_file():
        return policy, None, None
    baseline = load_json(baseline_file)

    source = resolve_candidate_lineage(
        root=root,
        head_sha=head_sha,
        body=str(live_pr.get("body") or ""),
        require=True,
        allow_legacy_pr_body=False,
    )
    assert source is not None
    if source.source != "DETACHED_QUALIFICATION_LEDGER":
        raise RuntimeError("RAC_PILOT_DETACHED_QUALIFICATION_REQUIRED")
    classification = classify_candidate(
        root=root,
        candidate_head_sha=head_sha,
        lineage_record=source.record,
        policy=policy,
        baseline=baseline,
    )
    return policy, baseline, classification


def _build_verified_certificate(
    *,
    root: Path,
    head_sha: str,
    policy: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> Mapping[str, Any]:
    verified: list[str] = []
    for path in classification.get("receipt_paths", []):
        value = load_json(root / str(path))
        if not value:
            raise RuntimeError(f"RAC_PILOT_EMPTY_RECEIPT:{path}")
        verified.append(str(path))
    return build_pilot_certificate(
        candidate_head_sha=head_sha,
        candidate_tree_sha=live._tree(head_sha),
        classification=classification,
        policy=policy,
        verified_receipt_paths=verified,
    )


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

    root = Path(".").resolve()
    policy, baseline, classification = _pilot_context(
        root=root,
        live_pr=live_pr,
        head_sha=live_head,
    )
    if classification is None or classification.get("eligible") is not True:
        reason = (
            "POLICY_INACTIVE"
            if policy["status"] != "ACTIVE_BOUNDED_PILOT"
            else "BASELINE_MISSING"
            if baseline is None
            else str(classification.get("reason", "NOT_ELIGIBLE"))
        )
        print(f"OVC_RAC_PILOT_READY_DISPOSITION=FALLBACK_CANONICAL_REFERENCE:{reason}")
        return live.command_ready()

    certificate = _build_verified_certificate(
        root=root,
        head_sha=live_head,
        policy=policy,
        classification=classification,
    )

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
        raise RuntimeError(
            f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:qualified {live_head}, live {refreshed_head}"
        )
    (
        _,
        refreshed_lineage,
        refreshed_authority,
        refreshed_frontier,
        refreshed_qualification_id,
    ) = live._payload_context(refreshed)
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
        f"rac-pilot-certificate:{certificate['certificate_id']}",
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
    print(
        "OVC_BASE_INDEPENDENT_ASSURANCE_GENERATION="
        + json.dumps(asdict(generation), sort_keys=True, separators=(",", ":"))
    )
    print(
        "OVC_RAC_PILOT_CERTIFICATE="
        + json.dumps(certificate, sort_keys=True, separators=(",", ":"))
    )
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
