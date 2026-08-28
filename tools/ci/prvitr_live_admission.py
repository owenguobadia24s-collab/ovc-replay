from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Iterable, Mapping
import urllib.error
import urllib.parse
import urllib.request

from ovc.development.prvit_remediation import IntegrationAdmissionReceipt, ShadowGRTProof
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_late_binding import (
    BaseIndependentAssuranceGeneration,
    LateBindingPlacement,
)
from ovc.development.skills.vit_routing import validate_vit_lineage_record
from tools.ci.vit_lineage_source import resolve_candidate_lineage

POLICY_ID = "PRVITR-LATE-BINDING-ADMISSION-POLICY-v0.2"
TESTS_WORKFLOW = "tests.yml"
TIERED_WORKFLOW = "ovc-tiered-tests.yml"
TEST_JOB_NAMES = ("VIT routing preflight", "tests", "pytest-unittest-parity", "runner-parity")
PROFILE_JOB_NAME = "OVC profile assurance"
READY_TIMEOUT_SECONDS = 22 * 60
DISCOVERY_POLL_SECONDS = 2.0
ACTIVE_POLL_SECONDS = 2.0


@dataclass
class AssurancePollDiagnostics:
    discovery_cycles: int = 0
    discovery_api_operations: int = 0
    active_cycles: int = 0
    active_api_operations: int = 0


def _repo() -> str:
    value = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if "/" not in value:
        raise RuntimeError("PRVITR_GITHUB_REPOSITORY_INVALID")
    return value


def _token() -> str:
    return os.environ.get("GITHUB_TOKEN", "").strip()


def _api(path: str, *, timeout: float = 15.0) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ovc-prvitr-late-binding-admission/2",
    }
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com{path}", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"PRVITR_GITHUB_API_FAILED:{path}:{exc}") from exc


def _write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT", "").strip()
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")
    print(f"OVC_PRVITR_{name.upper()}={value}")


def _event() -> Mapping[str, Any]:
    path = os.environ.get("GITHUB_EVENT_PATH", "").strip()
    if not path:
        raise RuntimeError("PRVITR_EVENT_PATH_MISSING")
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError("PRVITR_EVENT_INVALID")
    return value


def _event_pr(event: Mapping[str, Any]) -> Mapping[str, Any]:
    value = event.get("pull_request")
    if not isinstance(value, Mapping):
        raise RuntimeError("PRVITR_PULL_REQUEST_EVENT_REQUIRED")
    return value


def _live_pr(pr_number: int) -> Mapping[str, Any]:
    owner, repo = _repo().split("/", 1)
    value = _api(f"/repos/{owner}/{repo}/pulls/{pr_number}")
    if not isinstance(value, Mapping):
        raise RuntimeError("PRVITR_LIVE_PR_INVALID")
    return value


def _branch_sha(branch: str) -> str:
    owner, repo = _repo().split("/", 1)
    value = _api(f"/repos/{owner}/{repo}/branches/{urllib.parse.quote(branch, safe='')}")
    try:
        sha = str(value["commit"]["sha"])
    except (KeyError, TypeError) as exc:
        raise RuntimeError("PRVITR_BRANCH_SHA_MISSING") from exc
    if len(sha) != 40:
        raise RuntimeError("PRVITR_BRANCH_SHA_INVALID")
    return sha


def _git(*args: str, check: bool = True, env: Mapping[str, str] | None = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=dict(os.environ, **dict(env or {})),
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _ensure_commit(sha: str) -> None:
    proc = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], check=False)
    if proc.returncode == 0:
        return
    _git("fetch", "--no-tags", "origin", sha)


def _tree(commit: str) -> str:
    _ensure_commit(commit)
    value = _git("rev-parse", f"{commit}^{{tree}}")
    if len(value) != 40:
        raise RuntimeError("PRVITR_TREE_INVALID")
    return value


def _workflow_runs(workflow: str, head_sha: str) -> list[Mapping[str, Any]]:
    owner, repo = _repo().split("/", 1)
    query = urllib.parse.urlencode({"event": "pull_request", "head_sha": head_sha, "per_page": 100})
    value = _api(f"/repos/{owner}/{repo}/actions/workflows/{workflow}/runs?{query}")
    rows = value.get("workflow_runs", []) if isinstance(value, Mapping) else []
    return [row for row in rows if isinstance(row, Mapping)]


def _run_matches_pr(run: Mapping[str, Any], pr_number: int, head_sha: str) -> bool:
    if str(run.get("head_sha", "")) != head_sha:
        return False
    pulls = run.get("pull_requests", [])
    if not isinstance(pulls, list):
        return False
    return any(isinstance(row, Mapping) and int(row.get("number", -1)) == pr_number for row in pulls)


def _select_exact_run(
    runs: Iterable[Mapping[str, Any]],
    pr_number: int,
    head_sha: str,
) -> Mapping[str, Any] | None:
    candidates = [row for row in runs if _run_matches_pr(row, pr_number, head_sha)]
    if not candidates:
        return None
    candidates.sort(
        key=lambda row: (int(row.get("run_number", 0)), int(row.get("run_attempt", 0)), int(row.get("id", 0))),
        reverse=True,
    )
    return candidates[0]


def _exact_run(workflow: str, pr_number: int, head_sha: str) -> Mapping[str, Any] | None:
    return _select_exact_run(_workflow_runs(workflow, head_sha), pr_number, head_sha)


def resolve_exact_assurance_runs(
    pr_number: int,
    head_sha: str,
    *,
    tests_run: Mapping[str, Any] | None = None,
    tiered_run: Mapping[str, Any] | None = None,
    diagnostics: AssurancePollDiagnostics | None = None,
) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None]:
    """Discover each exact PR/head workflow run once, then retain its identity."""
    if tests_run is None:
        if diagnostics is not None:
            diagnostics.discovery_api_operations += 1
        tests_run = _exact_run(TESTS_WORKFLOW, pr_number, head_sha)
    if tiered_run is None:
        if diagnostics is not None:
            diagnostics.discovery_api_operations += 1
        tiered_run = _exact_run(TIERED_WORKFLOW, pr_number, head_sha)
    return tests_run, tiered_run


def _jobs(run_id: int) -> list[Mapping[str, Any]]:
    owner, repo = _repo().split("/", 1)
    value = _api(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs?per_page=100")
    rows = value.get("jobs", []) if isinstance(value, Mapping) else []
    return [row for row in rows if isinstance(row, Mapping)]


def _job_by_name(jobs: Iterable[Mapping[str, Any]], name: str) -> Mapping[str, Any] | None:
    rows = [row for row in jobs if str(row.get("name", "")) == name]
    if not rows:
        return None
    rows.sort(key=lambda row: int(row.get("id", 0)), reverse=True)
    return rows[0]


def evaluate_required_jobs(
    jobs: Iterable[Mapping[str, Any]],
    required_names: Iterable[str],
    *,
    expected_run_attempt: int | None = None,
) -> tuple[str, tuple[Mapping[str, Any], ...]]:
    """Pure required-job evaluator preserving the existing PASS/PENDING/FAIL law."""
    job_rows = tuple(jobs)
    selected: list[Mapping[str, Any]] = []
    for name in required_names:
        job = _job_by_name(job_rows, name)
        if job is None:
            return "PENDING", tuple(selected)
        selected.append(job)
        observed_attempt = int(job.get("run_attempt", 0) or 0)
        if expected_run_attempt is not None and observed_attempt not in (0, expected_run_attempt):
            return "FAIL", tuple(selected)
        if str(job.get("status", "")) == "completed" and str(job.get("conclusion", "")) != "success":
            return "FAIL", tuple(selected)
        if str(job.get("status", "")) != "completed":
            return "PENDING", tuple(selected)
    return "PASS", tuple(selected)


def _run_job_state(run: Mapping[str, Any], required_names: Iterable[str]) -> tuple[str, tuple[Mapping[str, Any], ...]]:
    attempt = int(run.get("run_attempt", 0) or 0) or None
    return evaluate_required_jobs(
        _jobs(int(run.get("id", 0))),
        required_names,
        expected_run_attempt=attempt,
    )


def _bounded_poll_sleep(
    deadline: float,
    cadence: float,
    *,
    now: Any,
    sleep: Any,
) -> None:
    remaining = deadline - float(now())
    if remaining > 0:
        sleep(min(cadence, remaining))


def wait_exact_assurance(
    pr_number: int,
    head_sha: str,
    *,
    timeout_seconds: float = READY_TIMEOUT_SECONDS,
    discovery_poll_seconds: float = DISCOVERY_POLL_SECONDS,
    active_poll_seconds: float = ACTIVE_POLL_SECONDS,
    now: Any | None = None,
    sleep: Any | None = None,
    diagnostics: AssurancePollDiagnostics | None = None,
) -> tuple[Mapping[str, Any], tuple[Mapping[str, Any], ...], Mapping[str, Any], Mapping[str, Any]]:
    """Pin exact runs, then poll only their required job sets until terminal state."""
    if discovery_poll_seconds <= 0 or active_poll_seconds <= 0 or timeout_seconds <= 0:
        raise ValueError("SIQ_READY_POLL_CONFIGURATION_INVALID")
    clock = now or time.monotonic
    sleeper = sleep or time.sleep
    counters = diagnostics or AssurancePollDiagnostics()
    deadline = float(clock()) + timeout_seconds
    tests_run: Mapping[str, Any] | None = None
    tiered_run: Mapping[str, Any] | None = None

    while float(clock()) < deadline and (tests_run is None or tiered_run is None):
        counters.discovery_cycles += 1
        tests_run, tiered_run = resolve_exact_assurance_runs(
            pr_number,
            head_sha,
            tests_run=tests_run,
            tiered_run=tiered_run,
            diagnostics=counters,
        )
        if tests_run is not None and tiered_run is not None:
            break
        _bounded_poll_sleep(
            deadline,
            discovery_poll_seconds,
            now=clock,
            sleep=sleeper,
        )

    while float(clock()) < deadline and tests_run is not None and tiered_run is not None:
        counters.active_cycles += 1
        counters.active_api_operations += 1
        tests_state, test_jobs = evaluate_required_jobs(
            _jobs(int(tests_run.get("id", 0))),
            TEST_JOB_NAMES,
            expected_run_attempt=int(tests_run.get("run_attempt", 0) or 0) or None,
        )
        if tests_state == "FAIL":
            raise RuntimeError(f"SIQ_EXACT_TESTS_WORKFLOW_FAILED:{tests_run.get('id')}")
        counters.active_api_operations += 1
        profile_state, profile_jobs = evaluate_required_jobs(
            _jobs(int(tiered_run.get("id", 0))),
            (PROFILE_JOB_NAME,),
            expected_run_attempt=int(tiered_run.get("run_attempt", 0) or 0) or None,
        )
        if profile_state == "FAIL":
            raise RuntimeError(f"SIQ_EXACT_PROFILE_WORKFLOW_FAILED:{tiered_run.get('id')}")
        if tests_state == "PASS" and profile_state == "PASS":
            print(
                "OVC_SIQ_READY_POLL_DIAGNOSTICS="
                + json.dumps(asdict(counters), sort_keys=True, separators=(",", ":"))
            )
            return tests_run, test_jobs, tiered_run, profile_jobs[0]
        _bounded_poll_sleep(
            deadline,
            active_poll_seconds,
            now=clock,
            sleep=sleeper,
        )
    raise RuntimeError("SIQ_READY_ADMISSION_TIMEOUT: exact required assurance did not complete")


def _wait_exact_assurance(pr_number: int, head_sha: str) -> tuple[Mapping[str, Any], tuple[Mapping[str, Any], ...], Mapping[str, Any], Mapping[str, Any]]:
    return wait_exact_assurance(pr_number, head_sha)


def _lineage_from_pr(pr: Mapping[str, Any]) -> tuple[Mapping[str, Any], Any, str]:
    head_sha = str((pr.get("head") or {}).get("sha", "")).strip()
    if len(head_sha) != 40:
        raise RuntimeError("PRVITR_HEAD_SHA_INVALID")
    root = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    allow_legacy_body = os.environ.get("OVC_VIT_ALLOW_LEGACY_PR_BODY_LINEAGE", "").lower() == "true"
    source = resolve_candidate_lineage(
        root=root,
        head_sha=head_sha,
        body=str(pr.get("body") or ""),
        require=True,
        allow_legacy_pr_body=allow_legacy_body,
    )
    assert source is not None
    qualification_id = source.immutable_ref if source.source == "DETACHED_QUALIFICATION_LEDGER" else source.content_sha256
    return source.record, validate_vit_lineage_record(source.record), qualification_id


def _payload_context(pr: Mapping[str, Any]) -> tuple[Mapping[str, Any], Any, str, str, str]:
    record, lineage, qualification_id = _lineage_from_pr(pr)
    pip = record.get("pip")
    if not isinstance(pip, Mapping):
        raise RuntimeError("PRVITR_PIP_INVALID")
    authority = str(pip.get("authority_manifest_id", ""))
    frontier = str(pip.get("dependency_frontier_id", ""))
    if len(authority) != 64 or len(frontier) != 64 or len(qualification_id) != 64:
        raise RuntimeError("PRVITR_QUALIFICATION_FRONTIER_INVALID")
    return record, lineage, authority, frontier, qualification_id


def _compose_late_binding(base_sha: str, head_sha: str, *, pip_id: str, authority: str, frontier: str) -> tuple[LateBindingPlacement, str]:
    _ensure_commit(base_sha)
    _ensure_commit(head_sha)
    proc = subprocess.run(
        ["git", "merge-tree", "--write-tree", base_sha, head_sha],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().replace("\n", " | ")
        raise RuntimeError(f"VIT_LATE_BINDING_CONTENT_CONFLICT:{detail}")
    rows = [row.strip() for row in proc.stdout.splitlines() if row.strip()]
    result_tree = rows[0] if rows else ""
    if len(result_tree) != 40:
        raise RuntimeError("VIT_LATE_BINDING_RESULT_TREE_INVALID")
    placement = LateBindingPlacement(
        pip_id=pip_id,
        candidate_head_sha=head_sha,
        physical_base_sha=base_sha,
        physical_base_tree=_tree(base_sha),
        prospective_tree_sha=result_tree,
        authority_manifest_id=authority,
        dependency_frontier_id=frontier,
    )
    env = {
        "GIT_AUTHOR_NAME": "OVC VIT Late Binding",
        "GIT_AUTHOR_EMAIL": "vit@ovc.invalid",
        "GIT_COMMITTER_NAME": "OVC VIT Late Binding",
        "GIT_COMMITTER_EMAIL": "vit@ovc.invalid",
    }
    synthetic_commit = _git(
        "commit-tree",
        result_tree,
        "-p",
        base_sha,
        "-m",
        f"OVC ephemeral late-binding placement {placement.placement_id}",
        env=env,
    )
    if len(synthetic_commit) != 40:
        raise RuntimeError("VIT_LATE_BINDING_SYNTHETIC_COMMIT_INVALID")
    return placement, synthetic_commit


def command_ready() -> int:
    event = _event()
    event_pr = _event_pr(event)
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    event_head = str((event_pr.get("head") or {}).get("sha", ""))
    live = _live_pr(pr_number)
    live_head = str((live.get("head") or {}).get("sha", ""))
    if live_head != event_head:
        raise RuntimeError(f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:event {event_head}, live {live_head}")
    if str(live.get("state", "")) != "open":
        raise RuntimeError(f"OVC_SIQ_PR_NOT_OPEN:{pr_number}")

    record, lineage, authority, frontier, qualification_id = _payload_context(live)
    tests_run, test_jobs, tiered_run, profile_job = _wait_exact_assurance(pr_number, live_head)

    # Qualification is immutable for one assurance generation. A same-head pointer
    # replacement is lawful, but it requires a new assurance generation rather than
    # mutating the identity beneath an already-running READY decision.
    refreshed = _live_pr(pr_number)
    refreshed_head = str((refreshed.get("head") or {}).get("sha", ""))
    if refreshed_head != live_head:
        raise RuntimeError(f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:qualified {live_head}, live {refreshed_head}")
    _, refreshed_lineage, refreshed_authority, refreshed_frontier, refreshed_qualification_id = _payload_context(refreshed)
    if refreshed_qualification_id != qualification_id:
        raise RuntimeError("VIT_QUALIFICATION_CHANGED_DURING_ASSURANCE")
    if refreshed_lineage.pip_id != lineage.pip_id or refreshed_authority != authority or refreshed_frontier != frontier:
        raise RuntimeError("VIT_QUALIFICATION_CONTENT_CHANGED_DURING_ASSURANCE")

    run_ids = tuple(
        [f"github-actions-run:{tests_run['id']}:job:{job.get('id')}" for job in test_jobs]
        + [f"github-actions-run:{tiered_run['id']}:job:{profile_job.get('id')}"]
    )
    generation = BaseIndependentAssuranceGeneration(
        pip_id=lineage.pip_id,
        candidate_head_sha=live_head,
        candidate_head_tree=_tree(live_head),
        authority_manifest_id=authority,
        dependency_frontier_id=frontier,
        policy_id=POLICY_ID,
        source_run_ids=run_ids,
    )
    print("OVC_BASE_INDEPENDENT_ASSURANCE_GENERATION=" + json.dumps(asdict(generation), sort_keys=True, separators=(",", ":")))
    _write_output("head_sha", live_head)
    _write_output("pip_id", lineage.pip_id)
    _write_output("qualification_id", qualification_id)
    _write_output("assurance_generation_id", generation.generation_id)
    _write_output("tests_run_id", str(tests_run["id"]))
    _write_output("profile_run_id", str(tiered_run["id"]))
    binding = "LATE" if lineage.late_binding else "LEGACY_RECORD_TREATED_AS_PAYLOAD_ONLY"
    print(
        f"OVC_VIT_QUALIFIED_PAYLOAD_READY: qualification={qualification_id} pip={lineage.pip_id} head={live_head} "
        f"binding={binding}; no physical-main predecessor is acquired during qualification."
    )
    return 0


def command_acquire() -> int:
    event = _event()
    event_pr = _event_pr(event)
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    expected_head = os.environ.get("OVC_READY_HEAD_SHA", "").strip() or str((event_pr.get("head") or {}).get("sha", ""))
    expected_pip = os.environ.get("OVC_READY_PIP_ID", "").strip()
    expected_qualification = os.environ.get("OVC_READY_QUALIFICATION_ID", "").strip()
    live = _live_pr(pr_number)
    live_head = str((live.get("head") or {}).get("sha", ""))
    if live_head != expected_head:
        raise RuntimeError(f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:READY {expected_head}, live {live_head}")
    record, lineage, authority, frontier, qualification_id = _payload_context(live)
    if expected_qualification and qualification_id != expected_qualification:
        raise RuntimeError("VIT_QUALIFICATION_CHANGED_AFTER_ASSURANCE")
    if expected_pip and lineage.pip_id != expected_pip:
        raise RuntimeError("VIT_LATE_BINDING_PIP_CHANGED_AFTER_QUALIFICATION")
    base_ref = str((live.get("base") or {}).get("ref", "main"))
    current_main = _branch_sha(base_ref)
    placement, synthetic_commit = _compose_late_binding(
        current_main,
        expected_head,
        pip_id=lineage.pip_id,
        authority=authority,
        frontier=frontier,
    )
    _write_output("base_sha", current_main)
    _write_output("candidate_head_sha", expected_head)
    _write_output("qualification_id", qualification_id)
    _write_output("placement_commit_sha", synthetic_commit)
    _write_output("placement_tree_sha", placement.prospective_tree_sha)
    _write_output("placement_id", placement.placement_id)
    print(
        "OVC_VIT_LATE_BINDING_PLACEMENT_ACQUIRED="
        + json.dumps(asdict(placement), sort_keys=True, separators=(",", ":"))
    )
    print(
        f"OVC_SIQ_BASE_SENSITIVE_LEASE_ACQUIRED: {base_ref}@{current_main}; "
        f"qualification={qualification_id} pip={lineage.pip_id} placement={placement.placement_id}."
    )
    return 0


def command_finalize() -> int:
    event = _event()
    event_pr = _event_pr(event)
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    candidate_head = os.environ.get("OVC_CANDIDATE_HEAD_SHA", "").strip()
    base_sha = os.environ.get("OVC_WINDOW_BASE_SHA", "").strip()
    placement_tree = os.environ.get("OVC_PLACEMENT_TREE_SHA", "").strip()
    placement_id = os.environ.get("OVC_PLACEMENT_ID", "").strip()
    assurance_generation_id = os.environ.get("OVC_ASSURANCE_GENERATION_ID", "").strip()
    expected_qualification = os.environ.get("OVC_QUALIFICATION_ID", "").strip()
    if any(len(value) != length for value, length in (
        (candidate_head, 40), (base_sha, 40), (placement_tree, 40), (placement_id, 64),
        (assurance_generation_id, 64), (expected_qualification, 64)
    )):
        raise RuntimeError("PRVITR_FINALIZE_INPUT_INVALID")
    live = _live_pr(pr_number)
    live_head = str((live.get("head") or {}).get("sha", ""))
    if live_head != candidate_head:
        raise RuntimeError(f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:qualified {candidate_head}, live {live_head}")
    base_ref = str((live.get("base") or {}).get("ref", "main"))
    final_main = _branch_sha(base_ref)
    if final_main != base_sha:
        raise RuntimeError(
            f"OVC_BASE_MOVED_DURING_READINESS: {base_ref} moved from {base_sha} to {final_main}; "
            "discard the ephemeral placement and retry the same qualified payload."
        )
    record, lineage, authority, frontier, qualification_id = _payload_context(live)
    if qualification_id != expected_qualification:
        raise RuntimeError("VIT_QUALIFICATION_CHANGED_DURING_FINAL_INTEGRATION")
    recomposed, _ = _compose_late_binding(base_sha, candidate_head, pip_id=lineage.pip_id, authority=authority, frontier=frontier)
    if recomposed.prospective_tree_sha != placement_tree or recomposed.placement_id != placement_id:
        raise RuntimeError("PRVITR_LATE_BINDING_PLACEMENT_MISMATCH")
    grt = ShadowGRTProof(
        result_tree=placement_tree,
        proof_id=f"exact-tree:{os.environ.get('GITHUB_RUN_ID', 'unknown')}:{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}",
        constitution_id="GRT-v0.2-exact-tree",
        state="PASS",
    )
    receipt = IntegrationAdmissionReceipt(
        assurance_generation_id=assurance_generation_id,
        pip_id=lineage.pip_id,
        placement_id=placement_id,
        result_tree=placement_tree,
        grt_proof_binding_id=grt.proof_binding_id,
        disposition="SHADOW_READY",
        reason_codes=("EXACT_ASSURANCE_BOUND", "DETACHED_QUALIFICATION_BOUND", "LATE_BINDING_PLACEMENT", "BASE_STABLE"),
    )
    print("OVC_INTEGRATION_ADMISSION_RECEIPT=" + json.dumps(asdict(receipt), sort_keys=True, separators=(",", ":")))
    _write_output("admission_receipt_id", receipt.receipt_id)
    _write_output("grt_proof_binding_id", grt.proof_binding_id)
    print(
        f"OVC_FINAL_INTEGRATION_WINDOW_PASS: qualification {qualification_id} / pip {lineage.pip_id} was late-bound "
        f"to {base_ref}@{base_sha} as placement {placement_id}; exact prospective tree {placement_tree}."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("ready", "acquire", "finalize"))
    args = parser.parse_args()
    try:
        if args.command == "ready":
            return command_ready()
        if args.command == "acquire":
            return command_acquire()
        return command_finalize()
    except (RuntimeError, VitContractError) as exc:
        print(f"::error title=PRVITR late-binding admission::{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
