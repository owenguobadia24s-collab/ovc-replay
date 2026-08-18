from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Iterable, Mapping
import urllib.error
import urllib.parse
import urllib.request

from ovc.development.prvit_remediation import (
    IntegrationAdmissionReceipt,
    IntegrationAssuranceGeneration,
    ShadowGRTProof,
    TypedAssuranceResult,
    semantic_dispatch_key,
)
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_predecessor import (
    OpenVitPlacement,
    resolve_vit_train_predecessor,
)
from ovc.development.skills.vit_routing import validate_vit_lineage_record
from tools.ci.vit_lineage_source import resolve_lineage_source

POLICY_ID = "PRVITR-LIVE-ADMISSION-POLICY-v0.1"
TESTS_WORKFLOW = "tests.yml"
TIERED_WORKFLOW = "ovc-tiered-tests.yml"
TEST_JOB_NAMES = (
    "VIT routing preflight",
    "tests",
    "pytest-unittest-parity",
    "runner-parity",
)
PROFILE_JOB_NAME = "OVC profile assurance"
READY_TIMEOUT_SECONDS = 22 * 60
PREDECESSOR_TIMEOUT_SECONDS = 4 * 60


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
        "User-Agent": "ovc-prvitr-live-admission/1",
    }
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"https://api.github.com{path}", headers=headers, method="GET"
    )
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
    value = _api(
        f"/repos/{owner}/{repo}/branches/{urllib.parse.quote(branch, safe='')}"
    )
    try:
        sha = str(value["commit"]["sha"])
    except (KeyError, TypeError) as exc:
        raise RuntimeError("PRVITR_BRANCH_SHA_MISSING") from exc
    if len(sha) != 40:
        raise RuntimeError("PRVITR_BRANCH_SHA_INVALID")
    return sha


def _git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _ensure_commit(sha: str) -> None:
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"], check=False
    )
    if proc.returncode == 0:
        return
    _git("fetch", "--no-tags", "origin", sha)


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    _ensure_commit(ancestor)
    _ensure_commit(descendant)
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    raise RuntimeError("PRVITR_GIT_ANCESTRY_PROOF_FAILED")


def _tree(commit: str) -> str:
    _ensure_commit(commit)
    value = _git("rev-parse", f"{commit}^{{tree}}")
    if len(value) != 40:
        raise RuntimeError("PRVITR_TREE_INVALID")
    return value


def _workflow_runs(workflow: str, head_sha: str) -> list[Mapping[str, Any]]:
    owner, repo = _repo().split("/", 1)
    query = urllib.parse.urlencode(
        {"event": "pull_request", "head_sha": head_sha, "per_page": 100}
    )
    value = _api(f"/repos/{owner}/{repo}/actions/workflows/{workflow}/runs?{query}")
    rows = value.get("workflow_runs", []) if isinstance(value, Mapping) else []
    return [row for row in rows if isinstance(row, Mapping)]


def _run_matches_pr(
    run: Mapping[str, Any], pr_number: int, head_sha: str
) -> bool:
    if str(run.get("head_sha", "")) != head_sha:
        return False
    pulls = run.get("pull_requests", [])
    if not isinstance(pulls, list):
        return False
    return any(
        isinstance(row, Mapping) and int(row.get("number", -1)) == pr_number
        for row in pulls
    )


def _exact_run(
    workflow: str, pr_number: int, head_sha: str
) -> Mapping[str, Any] | None:
    candidates = [
        row
        for row in _workflow_runs(workflow, head_sha)
        if _run_matches_pr(row, pr_number, head_sha)
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda row: (
            int(row.get("run_number", 0)),
            int(row.get("run_attempt", 0)),
            int(row.get("id", 0)),
        ),
        reverse=True,
    )
    return candidates[0]


def _jobs(run_id: int) -> list[Mapping[str, Any]]:
    owner, repo = _repo().split("/", 1)
    value = _api(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs?per_page=100")
    rows = value.get("jobs", []) if isinstance(value, Mapping) else []
    return [row for row in rows if isinstance(row, Mapping)]


def _job_by_name(
    jobs: Iterable[Mapping[str, Any]], name: str
) -> Mapping[str, Any] | None:
    rows = [row for row in jobs if str(row.get("name", "")) == name]
    if not rows:
        return None
    rows.sort(key=lambda row: int(row.get("id", 0)), reverse=True)
    return rows[0]


def _run_job_state(
    run: Mapping[str, Any], required_names: Iterable[str]
) -> tuple[str, tuple[Mapping[str, Any], ...]]:
    jobs = _jobs(int(run.get("id", 0)))
    selected: list[Mapping[str, Any]] = []
    for name in required_names:
        job = _job_by_name(jobs, name)
        if job is None:
            return "PENDING", tuple(selected)
        selected.append(job)
        if (
            str(job.get("status", "")) == "completed"
            and str(job.get("conclusion", "")) != "success"
        ):
            return "FAIL", tuple(selected)
        if str(job.get("status", "")) != "completed":
            return "PENDING", tuple(selected)
    return "PASS", tuple(selected)


def _wait_exact_assurance(
    pr_number: int, head_sha: str
) -> tuple[
    Mapping[str, Any],
    tuple[Mapping[str, Any], ...],
    Mapping[str, Any],
    Mapping[str, Any],
]:
    deadline = time.time() + READY_TIMEOUT_SECONDS
    while time.time() < deadline:
        tests_run = _exact_run(TESTS_WORKFLOW, pr_number, head_sha)
        tiered_run = _exact_run(TIERED_WORKFLOW, pr_number, head_sha)
        if tests_run is None or tiered_run is None:
            time.sleep(10)
            continue
        tests_state, test_jobs = _run_job_state(tests_run, TEST_JOB_NAMES)
        profile_state, profile_jobs = _run_job_state(
            tiered_run, (PROFILE_JOB_NAME,)
        )
        if tests_state == "FAIL":
            raise RuntimeError(
                f"SIQ_EXACT_TESTS_WORKFLOW_FAILED:{tests_run.get('id')}"
            )
        if profile_state == "FAIL":
            raise RuntimeError(
                f"SIQ_EXACT_PROFILE_WORKFLOW_FAILED:{tiered_run.get('id')}"
            )
        if tests_state == "PASS" and profile_state == "PASS":
            return tests_run, test_jobs, tiered_run, profile_jobs[0]
        time.sleep(10)
    raise RuntimeError(
        "SIQ_READY_ADMISSION_TIMEOUT: exact required assurance did not complete"
    )


def _lineage_from_pr(pr: Mapping[str, Any]) -> tuple[Mapping[str, Any], Any]:
    source = resolve_lineage_source(str(pr.get("body") or ""), require=True)
    assert source is not None
    return source.record, validate_vit_lineage_record(source.record)


def _typed_result(
    name: str, job: Mapping[str, Any], frontier: str, run_id: int
) -> TypedAssuranceResult:
    state = "PASS" if str(job.get("conclusion", "")) == "success" else "FAIL"
    return TypedAssuranceResult(
        assertion_id=name,
        state=state,
        dependency_frontier_id=frontier,
        evidence_id=f"github-actions-job:{job.get('id')}",
        required=True,
        source_run_id=f"github-actions-run:{run_id}:job:{job.get('id')}",
    )


def command_ready() -> int:
    event = _event()
    event_pr = _event_pr(event)
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    event_head = str((event_pr.get("head") or {}).get("sha", ""))
    live = _live_pr(pr_number)
    live_head = str((live.get("head") or {}).get("sha", ""))
    if live_head != event_head:
        raise RuntimeError(
            f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:event {event_head}, live {live_head}"
        )
    if str(live.get("state", "")) != "open":
        raise RuntimeError(f"OVC_SIQ_PR_NOT_OPEN:{pr_number}")

    record, lineage = _lineage_from_pr(live)
    tests_run, test_jobs, tiered_run, profile_job = _wait_exact_assurance(
        pr_number, live_head
    )
    frontier = str(record["pip"]["dependency_frontier_id"])
    authority = str(record["pip"]["authority_manifest_id"])
    results = [
        _typed_result(str(job.get("name", "")), job, frontier, int(tests_run["id"]))
        for job in test_jobs
    ]
    results.append(
        _typed_result(PROFILE_JOB_NAME, profile_job, frontier, int(tiered_run["id"]))
    )
    generation = IntegrationAssuranceGeneration(
        pip_id=lineage.pip_id,
        head_tree=_tree(live_head),
        placement_id=lineage.placement_id,
        predecessor_tree=str(
            record["generation"]["predecessor_tree"]["tree_sha"]
        ),
        authority_manifest_id=authority,
        dependency_frontier_id=frontier,
        policy_id=POLICY_ID,
        assurance_result_ids=tuple(item.result_id for item in results),
        source_run_ids=tuple(
            str(item.source_run_id) for item in results if item.source_run_id
        ),
    )
    base_ref = str((live.get("base") or {}).get("ref", "main"))
    current_main = _branch_sha(base_ref)
    if not _is_ancestor(current_main, live_head):
        dispatch = semantic_dispatch_key(
            str(record["programme_id"]), str(record["packet_id"]), lineage.pip_id
        )
        print(
            f"OVC_PLACEMENT_RECOMPUTE_ONLY_REQUEUE dispatch_key={dispatch} "
            f"base={current_main} head={live_head}"
        )
        raise RuntimeError(
            f"OVC_RECONCILE_REQUIRED: candidate {live_head} does not contain live "
            f"{base_ref}@{current_main}; PLACEMENT_RECOMPUTE_ONLY selective renewal is required"
        )
    print(
        "OVC_INTEGRATION_ASSURANCE_GENERATION="
        + json.dumps(asdict(generation), sort_keys=True, separators=(",", ":"))
    )
    _write_output("base_sha", current_main)
    _write_output("head_sha", live_head)
    _write_output("assurance_generation_id", generation.generation_id)
    _write_output("tests_run_id", str(tests_run["id"]))
    _write_output("profile_run_id", str(tiered_run["id"]))
    print(
        f"OVC_SIQ_READY_ADMITTED: {live_head} exact tests run {tests_run['id']} + "
        f"profile run {tiered_run['id']} -> assurance_generation "
        f"{generation.generation_id}; contains live {base_ref}@{current_main}"
    )
    return 0


def _open_pulls(base_ref: str) -> list[Mapping[str, Any]]:
    owner, repo = _repo().split("/", 1)
    value = _api(
        f"/repos/{owner}/{repo}/pulls?state=open&base="
        f"{urllib.parse.quote(base_ref, safe='')}&per_page=100"
    )
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _open_vit_placements(
    base_ref: str, *, current_pr_number: int
) -> tuple[OpenVitPlacement, ...]:
    placements: list[OpenVitPlacement] = []
    for candidate in _open_pulls(base_ref):
        number = int(candidate.get("number", -1))
        if number == current_pr_number:
            continue
        head_sha = str((candidate.get("head") or {}).get("sha", ""))
        if len(head_sha) != 40:
            continue
        try:
            source = resolve_lineage_source(
                str(candidate.get("body") or ""), require=False
            )
            if source is None:
                print(
                    f"OVC_FINAL_INTEGRATION_NON_VIT_PR_IGNORED: PR #{number} has no "
                    "canonical VIT lineage and cannot own a VIT placement predecessor lease."
                )
                continue
            validate_vit_lineage_record(source.record)
        except (RuntimeError, ValueError) as exc:
            print(
                f"OVC_FINAL_INTEGRATION_INVALID_VIT_PR_IGNORED: PR #{number}: {exc}"
            )
            continue
        placements.append(
            OpenVitPlacement(
                pr_number=number,
                head_sha=head_sha,
                lineage_record=source.record,
            )
        )
    return tuple(placements)


def _find_predecessor(
    current_pr: Mapping[str, Any], base_ref: str, main_sha: str
) -> Mapping[str, Any] | None:
    current_number = int(current_pr.get("number", -1))
    record, _ = _lineage_from_pr(current_pr)
    main_tree = _tree(main_sha)
    expected_tree = str(record["generation"]["predecessor_tree"]["tree_sha"])

    # The exact placement predecessor is already physical.  This is the normal
    # path and intentionally does not scan/sort unrelated open PRs.
    if main_tree == expected_tree:
        print(
            "OVC_FINAL_INTEGRATION_NO_VIT_PLACEMENT_PREDECESSOR: "
            f"physical main tree {main_tree} is the exact VIT predecessor tree for PR "
            f"#{current_number}."
        )
        return None

    predecessor = resolve_vit_train_predecessor(
        current_lineage_record=record,
        current_main_tree=main_tree,
        open_placements=_open_vit_placements(
            base_ref, current_pr_number=current_number
        ),
    )
    if predecessor is None:
        return None
    return {
        "number": predecessor.pr_number,
        "head_sha": predecessor.head_sha,
        "base_sha": main_sha,
        "generation_id": predecessor.generation_id,
        "placement_id": predecessor.placement_id,
        "train_generation_id": predecessor.train_generation_id,
        "result_tree": predecessor.result_tree,
    }


def command_acquire() -> int:
    event = _event()
    event_pr = _event_pr(event)
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    expected_head = os.environ.get("OVC_READY_HEAD_SHA", "").strip() or str(
        (event_pr.get("head") or {}).get("sha", "")
    )
    ready_base = os.environ.get("OVC_READY_BASE_SHA", "").strip()
    live = _live_pr(pr_number)
    live_head = str((live.get("head") or {}).get("sha", ""))
    if live_head != expected_head:
        raise RuntimeError(
            f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:READY {expected_head}, live {live_head}"
        )
    base_ref = str((live.get("base") or {}).get("ref", "main"))
    started = time.time()
    deadline = started + PREDECESSOR_TIMEOUT_SECONDS
    lease_owner: Mapping[str, Any] | None = None

    while time.time() < deadline:
        current_live = _live_pr(pr_number)
        current_head = str((current_live.get("head") or {}).get("sha", ""))
        if current_head != expected_head:
            raise RuntimeError(
                f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:READY {expected_head}, live {current_head}"
            )
        current_main = _branch_sha(base_ref)
        if lease_owner is None:
            lease_owner = _find_predecessor(current_live, base_ref, current_main)
            if lease_owner is None:
                print(
                    "OVC_CI_METRIC "
                    + json.dumps(
                        {
                            "schema": "ovc-ci-metric/v1",
                            "metric": "final_integration_predecessor_lease_wait_ms",
                            "value_ms": int((time.time() - started) * 1000),
                            "head_sha": expected_head,
                            "predecessor_pr": None,
                            "result": "NO_VIT_PLACEMENT_PREDECESSOR",
                        },
                        separators=(",", ":"),
                    )
                )
                break
            print(
                "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_HELD: "
                f"PR #{lease_owner['number']} head {lease_owner['head_sha']} "
                f"placement {lease_owner['placement_id']}."
            )

        terminal = _live_pr(int(lease_owner["number"]))
        new_main = _branch_sha(base_ref)
        terminal_head = str((terminal.get("head") or {}).get("sha", ""))
        if terminal_head != lease_owner["head_sha"]:
            print(
                "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_SUPERSEDED: "
                f"PR #{lease_owner['number']}."
            )
            lease_owner = None
            continue
        if terminal.get("merged_at") and new_main != lease_owner["base_sha"]:
            print(
                "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_MERGED: "
                f"PR #{lease_owner['number']}; successor re-resolves exact placement."
            )
            lease_owner = None
            continue
        if str(terminal.get("state", "")) == "closed":
            print(
                "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_RELEASED_UNMERGED: "
                f"PR #{lease_owner['number']}; current placement must re-resolve."
            )
            lease_owner = None
            continue
        if new_main != lease_owner["base_sha"]:
            print(
                "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_INVALIDATED: "
                f"PR #{lease_owner['number']}; physical main moved."
            )
            lease_owner = None
            continue
        time.sleep(5)

    if lease_owner is not None:
        raise RuntimeError(
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_TERMINAL_TIMEOUT: "
            f"PR #{lease_owner['number']}"
        )

    main_snapshot = _branch_sha(base_ref)
    if not _is_ancestor(main_snapshot, expected_head):
        raise RuntimeError(
            f"OVC_RECONCILE_REQUIRED: candidate {expected_head} does not contain acquired "
            f"{base_ref}@{main_snapshot}; READY base was {ready_base}"
        )
    if ready_base and main_snapshot != ready_base:
        print(
            f"OVC_READY_BASE_REFRESHED_BEFORE_FINAL_LEASE: READY {ready_base} -> "
            f"live {main_snapshot}; candidate {expected_head} already contains newer base."
        )
    _write_output("base_sha", main_snapshot)
    _write_output("head_sha", expected_head)
    print(
        f"OVC_SIQ_BASE_SENSITIVE_LEASE_ACQUIRED: {base_ref}@{main_snapshot} "
        f"for {expected_head}."
    )
    return 0


def command_finalize() -> int:
    event = _event()
    event_pr = _event_pr(event)
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    head_sha = os.environ.get("OVC_WINDOW_HEAD_SHA", "").strip()
    base_sha = os.environ.get("OVC_WINDOW_BASE_SHA", "").strip()
    assurance_generation_id = os.environ.get(
        "OVC_ASSURANCE_GENERATION_ID", ""
    ).strip()
    if (
        len(head_sha) != 40
        or len(base_sha) != 40
        or len(assurance_generation_id) != 64
    ):
        raise RuntimeError("PRVITR_FINALIZE_INPUT_INVALID")
    live = _live_pr(pr_number)
    live_head = str((live.get("head") or {}).get("sha", ""))
    if live_head != head_sha:
        raise RuntimeError(
            f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:lease {head_sha}, live {live_head}"
        )
    base_ref = str((live.get("base") or {}).get("ref", "main"))
    final_main = _branch_sha(base_ref)
    if final_main != base_sha:
        raise RuntimeError(
            f"OVC_BASE_MOVED_DURING_READINESS: {base_ref} moved from "
            f"{base_sha} to {final_main}"
        )
    if not _is_ancestor(base_sha, head_sha):
        raise RuntimeError("OVC_CANDIDATE_NOT_RECONCILED_TO_CURRENT_MAIN")
    record, lineage = _lineage_from_pr(live)
    head_tree = _tree(head_sha)
    if str(record["generation"]["result_tree"]["tree_sha"]) != head_tree:
        raise RuntimeError("PRVITR_FINAL_RESULT_TREE_MISMATCH")
    grt = ShadowGRTProof(
        result_tree=head_tree,
        proof_id=(
            f"exact-tree:{os.environ.get('GITHUB_RUN_ID', 'unknown')}:"
            f"{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
        ),
        constitution_id="GRT-v0.2-exact-tree",
        state="PASS",
    )
    receipt = IntegrationAdmissionReceipt(
        assurance_generation_id=assurance_generation_id,
        pip_id=lineage.pip_id,
        placement_id=lineage.placement_id,
        result_tree=head_tree,
        grt_proof_binding_id=grt.proof_binding_id,
        disposition="SHADOW_READY",
        reason_codes=(
            "LIVE_SWITCH_OPERATOR_PASS",
            "EXACT_ASSURANCE_BOUND",
            "LOCAL_GIT_ANCESTRY_PASS",
            "BASE_STABLE",
        ),
    )
    print(
        "OVC_INTEGRATION_ADMISSION_RECEIPT="
        + json.dumps(asdict(receipt), sort_keys=True, separators=(",", ":"))
    )
    _write_output("admission_receipt_id", receipt.receipt_id)
    _write_output("grt_proof_binding_id", grt.proof_binding_id)
    print(
        f"OVC_FINAL_INTEGRATION_WINDOW_PASS: exact-final assurance bound by "
        f"admission receipt {receipt.receipt_id} on {head_sha} while {base_ref} "
        f"remained {base_sha}."
    )
    print(
        f"OVC_SIQ_BASE_SENSITIVE_LEASE_RELEASED: {head_sha}; immediate successor "
        "advancement is eligible."
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
        print(f"::error title=PRVITR live admission::{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
