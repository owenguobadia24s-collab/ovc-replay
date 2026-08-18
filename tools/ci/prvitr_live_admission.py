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
    ShadowGRTProof,
    TypedAssuranceResult,
)
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_frontier_decoupling import (
    FrontierIntegrationAdmissionReceipt,
    FrontierIntegrationAssuranceGeneration,
    SourceHead,
    a1_proof_id,
    assurance_generation_from_record,
    build_a2_proof,
    build_frontier_ledger_envelope,
    build_frontier_lineage,
    classify_frontier_movement,
    compose_pip_tree,
    create_prospective_commit,
    decode_record,
    diff_tree_paths,
    encode_record,
    git_tree,
    tree_is_in_commit_ancestry,
    validate_a2_proof,
)
from ovc.development.skills.vit_local_completion_executor import (
    build_live_transaction_freeze,
    encode_freeze_marker,
)
from ovc.development.skills.vit_predecessor import (
    OpenVitPlacement,
    resolve_vit_train_predecessor,
)
from ovc.development.skills.vit_routing import validate_vit_lineage_record
from tools.ci.vit_lineage_source import resolve_lineage_source

POLICY_ID = "PRVITR-VIT-FRONTIER-DECOUPLING-POLICY-v0.1"
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
        "User-Agent": "ovc-prvitr-live-admission/2",
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


def _write_output(name: str, value: str, *, echo: bool = True) -> None:
    output = os.environ.get("GITHUB_OUTPUT", "").strip()
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")
    if echo:
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
                f"SIQ_EXACT_A0_TESTS_WORKFLOW_FAILED:{tests_run.get('id')}"
            )
        if profile_state == "FAIL":
            raise RuntimeError(
                f"SIQ_EXACT_A0_PROFILE_WORKFLOW_FAILED:{tiered_run.get('id')}"
            )
        if tests_state == "PASS" and profile_state == "PASS":
            return tests_run, test_jobs, tiered_run, profile_jobs[0]
        time.sleep(10)
    raise RuntimeError(
        "SIQ_READY_ADMISSION_TIMEOUT: exact PIP-bound A0 assurance did not complete"
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


def _source_head(
    pr: Mapping[str, Any], record: Mapping[str, Any]
) -> SourceHead:
    number = int(pr.get("number", -1))
    head = pr.get("head")
    if not isinstance(head, Mapping):
        raise RuntimeError("PRVITR_LIVE_PR_HEAD_INVALID")
    head_sha = str(head.get("sha", ""))
    head_ref = str(head.get("ref", ""))
    head_tree = _tree(head_sha)
    raw = record.get("source_head")
    if isinstance(raw, Mapping):
        source = SourceHead(**dict(raw))
        if (
            source.commit_sha != head_sha
            or source.tree_sha != head_tree
            or source.pr_number != number
        ):
            raise RuntimeError("VIT_SOURCE_HEAD_PROVENANCE_MISMATCH")
        return source
    return SourceHead(
        commit_sha=head_sha,
        tree_sha=head_tree,
        pr_number=number,
        head_ref=head_ref,
    )


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


def _exact_open_predecessor(
    *,
    record: Mapping[str, Any],
    base_ref: str,
    current_pr_number: int,
    current_main_tree: str,
):
    return resolve_vit_train_predecessor(
        current_lineage_record=record,
        current_main_tree=current_main_tree,
        open_placements=_open_vit_placements(
            base_ref, current_pr_number=current_pr_number
        ),
    )


def _resolve_frontier(
    *, pr: Mapping[str, Any], base_ref: str, current_main_sha: str
) -> tuple[Mapping[str, Any], SourceHead, str]:
    source_record, source_lineage = _lineage_from_pr(pr)
    source_head = _source_head(pr, source_record)
    source_generation = source_record["generation"]
    source_result_tree = str(source_generation["result_tree"]["tree_sha"])
    if source_result_tree != source_head.tree_sha:
        raise RuntimeError("VIT_SOURCE_LINEAGE_RESULT_NOT_SOURCE_HEAD_TREE")

    current_main_tree = _tree(current_main_sha)
    source_predecessor_tree = str(source_generation["predecessor_tree"]["tree_sha"])
    historical = source_predecessor_tree == current_main_tree or tree_is_in_commit_ancestry(
        Path.cwd(),
        tree_sha=source_predecessor_tree,
        descendant_commit=current_main_sha,
    )

    if historical:
        changed_paths = diff_tree_paths(
            Path.cwd(), source_predecessor_tree, current_main_tree
        )
        movement = classify_frontier_movement(
            pip=source_record["pip"],
            source_predecessor_tree=source_predecessor_tree,
            current_predecessor_tree=current_main_tree,
            changed_paths=changed_paths,
        )
        if movement.disposition == "PAYLOAD_REBUILD_REQUIRED":
            raise RuntimeError(
                f"VIT_PAYLOAD_REBUILD_REQUIRED:{movement.decision_id}:"
                f"same PIP cannot overwrite changed frontier paths"
            )
        if movement.disposition == "AUTHORITY_REVIEW_REQUIRED":
            raise RuntimeError(
                f"VIT_AUTHORITY_REVIEW_REQUIRED:{movement.decision_id}"
            )
        prospective_tree = compose_pip_tree(
            Path.cwd(), current_main_tree, source_record["pip"]["logical_changes"]
        )
        frontier = build_frontier_lineage(
            source_lineage_record=source_record,
            source_head=source_head,
            predecessor_commit=current_main_sha,
            predecessor_tree=current_main_tree,
            prospective_result_tree=prospective_tree,
            movement=movement,
        )
        return frontier, source_head, movement.disposition

    predecessor = _exact_open_predecessor(
        record=source_record,
        base_ref=base_ref,
        current_pr_number=int(pr.get("number", -1)),
        current_main_tree=current_main_tree,
    )
    if predecessor is None:
        raise RuntimeError("VIT_PLACEMENT_PREDECESSOR_RESOLUTION_INVALID")
    # The source generation remains the exact planned generation until its encoded
    # predecessor becomes physical.  It is wrapped in current frontier provenance
    # without changing PIP/generation/placement identity.
    from ovc.development.skills.vit_frontier_decoupling import FrontierMovementDecision

    movement = FrontierMovementDecision(
        disposition="NO_MOVEMENT",
        source_predecessor_tree=source_predecessor_tree,
        current_predecessor_tree=source_predecessor_tree,
        a1_renewal_required=False,
        a2_renewal_required=True,
    )
    frontier = build_frontier_lineage(
        source_lineage_record=source_record,
        source_head=source_head,
        predecessor_commit=predecessor.head_sha,
        predecessor_tree=source_predecessor_tree,
        prospective_result_tree=source_result_tree,
        movement=movement,
    )
    return frontier, source_head, "WAITING_VIT_PREDECESSOR"


def _assurance_generation(
    *,
    frontier: Mapping[str, Any],
    source_head: SourceHead,
    tests_run: Mapping[str, Any],
    test_jobs: Iterable[Mapping[str, Any]],
    tiered_run: Mapping[str, Any],
    profile_job: Mapping[str, Any],
    supersedes: str | None = None,
) -> FrontierIntegrationAssuranceGeneration:
    lineage = validate_vit_lineage_record(frontier)
    pip = frontier["pip"]
    dependency_frontier = str(pip["dependency_frontier_id"])
    results = [
        _typed_result(
            str(job.get("name", "")),
            job,
            dependency_frontier,
            int(tests_run["id"]),
        )
        for job in test_jobs
    ]
    results.append(
        _typed_result(
            PROFILE_JOB_NAME,
            profile_job,
            dependency_frontier,
            int(tiered_run["id"]),
        )
    )
    resolution = frontier["frontier_resolution"]
    return FrontierIntegrationAssuranceGeneration(
        source_head_id=source_head.source_head_id,
        source_head_commit=source_head.commit_sha,
        pip_id=lineage.pip_id,
        vit_generation_id=lineage.generation_id,
        placement_id=lineage.placement_id,
        predecessor_commit=str(resolution["current_predecessor_commit"]),
        predecessor_tree=str(resolution["current_predecessor_tree"]),
        prospective_result_tree=str(resolution["prospective_result_tree"]),
        authority_manifest_id=str(pip["authority_manifest_id"]),
        dependency_frontier_id=dependency_frontier,
        policy_id=POLICY_ID,
        a0_result_ids=tuple(item.result_id for item in results),
        a1_proof_id=a1_proof_id(frontier),
        assurance_stage="A0_A1_BOUND",
        source_run_ids=tuple(
            str(item.source_run_id) for item in results if item.source_run_id
        ),
        supersedes_assurance_generation_id=supersedes,
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

    tests_run, test_jobs, tiered_run, profile_job = _wait_exact_assurance(
        pr_number, live_head
    )
    base_ref = str((live.get("base") or {}).get("ref", "main"))
    current_main = _branch_sha(base_ref)
    frontier, source_head, movement = _resolve_frontier(
        pr=live, base_ref=base_ref, current_main_sha=current_main
    )
    assurance = _assurance_generation(
        frontier=frontier,
        source_head=source_head,
        tests_run=tests_run,
        test_jobs=test_jobs,
        tiered_run=tiered_run,
        profile_job=profile_job,
    )
    lineage = validate_vit_lineage_record(frontier)
    resolution = frontier["frontier_resolution"]
    print(
        "OVC_FRONTIER_INTEGRATION_ASSURANCE_GENERATION="
        + json.dumps(asdict(assurance), sort_keys=True, separators=(",", ":"))
    )
    _write_output("base_sha", current_main)
    _write_output("source_head_sha", source_head.commit_sha)
    _write_output("head_sha", source_head.commit_sha)
    _write_output("frontier_generation_id", lineage.generation_id)
    _write_output("placement_id", lineage.placement_id)
    _write_output("predecessor_commit_sha", str(resolution["current_predecessor_commit"]))
    _write_output("predecessor_tree", str(resolution["current_predecessor_tree"]))
    _write_output("prospective_result_tree", str(resolution["prospective_result_tree"]))
    _write_output("frontier_lineage_b64", encode_record(frontier), echo=False)
    _write_output("assurance_generation_b64", encode_record(asdict(assurance)), echo=False)
    _write_output("assurance_generation_id", assurance.assurance_generation_id)
    _write_output("tests_run_id", str(tests_run["id"]))
    _write_output("profile_run_id", str(tiered_run["id"]))
    _write_output("movement_disposition", movement)
    print(
        f"OVC_SIQ_READY_ADMITTED: source_head={source_head.commit_sha} "
        f"pip={lineage.pip_id} frontier_generation={lineage.generation_id} "
        f"placement={lineage.placement_id} result_tree={resolution['prospective_result_tree']} "
        f"movement={movement}; PR identity retained."
    )
    return 0


def command_acquire() -> int:
    event = _event()
    event_pr = _event_pr(event)
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    expected_source_head = os.environ.get("OVC_READY_SOURCE_HEAD_SHA", "").strip() or str(
        (event_pr.get("head") or {}).get("sha", "")
    )
    live = _live_pr(pr_number)
    live_head = str((live.get("head") or {}).get("sha", ""))
    if live_head != expected_source_head:
        raise RuntimeError(
            f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:READY {expected_source_head}, live {live_head}"
        )
    base_ref = str((live.get("base") or {}).get("ref", "main"))
    started = time.time()
    deadline = started + PREDECESSOR_TIMEOUT_SECONDS
    lease_owner: Mapping[str, Any] | None = None
    selected_frontier: Mapping[str, Any] | None = None
    selected_source: SourceHead | None = None
    main_snapshot = ""

    while time.time() < deadline:
        current_live = _live_pr(pr_number)
        current_head = str((current_live.get("head") or {}).get("sha", ""))
        if current_head != expected_source_head:
            raise RuntimeError(
                f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:READY {expected_source_head}, live {current_head}"
            )
        current_main = _branch_sha(base_ref)
        current_main_tree = _tree(current_main)
        frontier, source_head, movement = _resolve_frontier(
            pr=current_live, base_ref=base_ref, current_main_sha=current_main
        )
        predecessor = resolve_vit_train_predecessor(
            current_lineage_record=frontier,
            current_main_tree=current_main_tree,
            open_placements=_open_vit_placements(
                base_ref, current_pr_number=pr_number
            ),
        )
        if predecessor is None:
            selected_frontier = frontier
            selected_source = source_head
            main_snapshot = current_main
            print(
                "OVC_CI_METRIC "
                + json.dumps(
                    {
                        "schema": "ovc-ci-metric/v1",
                        "metric": "final_integration_predecessor_lease_wait_ms",
                        "value_ms": int((time.time() - started) * 1000),
                        "source_head_sha": expected_source_head,
                        "predecessor_pr": None,
                        "result": "CURRENT_VIT_PREDECESSOR_PHYSICAL",
                        "movement": movement,
                    },
                    separators=(",", ":"),
                )
            )
            break

        lease_owner = {
            "number": predecessor.pr_number,
            "head_sha": predecessor.head_sha,
            "base_sha": current_main,
            "generation_id": predecessor.generation_id,
            "placement_id": predecessor.placement_id,
            "result_tree": predecessor.result_tree,
        }
        print(
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_HELD: "
            f"PR #{predecessor.pr_number} head {predecessor.head_sha} "
            f"placement {predecessor.placement_id}."
        )
        terminal = _live_pr(predecessor.pr_number)
        new_main = _branch_sha(base_ref)
        terminal_head = str((terminal.get("head") or {}).get("sha", ""))
        if terminal_head != predecessor.head_sha:
            print(
                "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_SUPERSEDED: "
                f"PR #{predecessor.pr_number}."
            )
            lease_owner = None
            continue
        if terminal.get("merged_at") and new_main != current_main:
            print(
                "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_MERGED: "
                f"PR #{predecessor.pr_number}; same PIP re-resolves on new frontier."
            )
            lease_owner = None
            continue
        if str(terminal.get("state", "")) == "closed":
            print(
                "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_RELEASED_UNMERGED: "
                f"PR #{predecessor.pr_number}; placement must re-resolve."
            )
            lease_owner = None
            continue
        if new_main != current_main:
            print(
                "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_INVALIDATED: "
                f"PR #{predecessor.pr_number}; physical main moved."
            )
            lease_owner = None
            continue
        time.sleep(5)

    if selected_frontier is None or selected_source is None:
        owner = lease_owner["number"] if lease_owner is not None else "UNKNOWN"
        raise RuntimeError(
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_TERMINAL_TIMEOUT: "
            f"PR #{owner}"
        )

    # Rebind the same completed A0 evidence to the exact current A1 placement.
    tests_run, test_jobs, tiered_run, profile_job = _wait_exact_assurance(
        pr_number, expected_source_head
    )
    ready_assurance = os.environ.get("OVC_READY_ASSURANCE_GENERATION_ID", "").strip()
    assurance = _assurance_generation(
        frontier=selected_frontier,
        source_head=selected_source,
        tests_run=tests_run,
        test_jobs=test_jobs,
        tiered_run=tiered_run,
        profile_job=profile_job,
        supersedes=(ready_assurance if len(ready_assurance) == 64 else None),
    )
    lineage = validate_vit_lineage_record(selected_frontier)
    resolution = selected_frontier["frontier_resolution"]
    result_tree = str(resolution["prospective_result_tree"])
    prospective_commit = create_prospective_commit(
        Path.cwd(),
        predecessor_commit=main_snapshot,
        result_tree=result_tree,
        generation_id=lineage.generation_id,
    )
    _write_output("base_sha", main_snapshot)
    _write_output("base_tree", str(resolution["current_predecessor_tree"]))
    _write_output("source_head_sha", selected_source.commit_sha)
    _write_output("head_sha", selected_source.commit_sha)
    _write_output("frontier_generation_id", lineage.generation_id)
    _write_output("placement_id", lineage.placement_id)
    _write_output("prospective_result_tree", result_tree)
    _write_output("prospective_commit_sha", prospective_commit)
    _write_output("frontier_lineage_b64", encode_record(selected_frontier), echo=False)
    _write_output("assurance_generation_b64", encode_record(asdict(assurance)), echo=False)
    _write_output("assurance_generation_id", assurance.assurance_generation_id)
    print(
        f"OVC_SIQ_BASE_SENSITIVE_LEASE_ACQUIRED: {base_ref}@{main_snapshot} "
        f"tree={resolution['current_predecessor_tree']} generation={lineage.generation_id} "
        f"result_tree={result_tree} source_head={selected_source.commit_sha}."
    )
    return 0


def command_finalize() -> int:
    event = _event()
    event_pr = _event_pr(event)
    pr_number = int(event.get("number", event_pr.get("number", -1)))
    source_head_sha = os.environ.get("OVC_WINDOW_SOURCE_HEAD_SHA", "").strip()
    base_sha = os.environ.get("OVC_WINDOW_BASE_SHA", "").strip()
    base_tree = os.environ.get("OVC_WINDOW_BASE_TREE", "").strip()
    prospective_commit = os.environ.get("OVC_WINDOW_PROSPECTIVE_COMMIT_SHA", "").strip()
    prospective_tree = os.environ.get("OVC_WINDOW_PROSPECTIVE_RESULT_TREE", "").strip()
    preliminary_assurance_id = os.environ.get(
        "OVC_ASSURANCE_GENERATION_ID", ""
    ).strip()
    preliminary_assurance_token = os.environ.get(
        "OVC_ASSURANCE_GENERATION_B64", ""
    ).strip()
    frontier_token = os.environ.get("OVC_FRONTIER_LINEAGE_B64", "").strip()
    if any(
        len(value) != length
        for value, length in (
            (source_head_sha, 40),
            (base_sha, 40),
            (base_tree, 40),
            (prospective_commit, 40),
            (prospective_tree, 40),
            (preliminary_assurance_id, 64),
        )
    ) or not frontier_token or not preliminary_assurance_token:
        raise RuntimeError("PRVITR_FINALIZE_INPUT_INVALID")

    live = _live_pr(pr_number)
    live_head = str((live.get("head") or {}).get("sha", ""))
    if live_head != source_head_sha:
        raise RuntimeError(
            f"OVC_SIQ_SUPERSEDED_EVENT_HEAD:lease source {source_head_sha}, live {live_head}"
        )
    base_ref = str((live.get("base") or {}).get("ref", "main"))
    final_main = _branch_sha(base_ref)
    final_main_tree = _tree(final_main)
    if final_main != base_sha or final_main_tree != base_tree:
        raise RuntimeError(
            f"PREDECESSOR_MOVED: {base_ref} moved from {base_sha}/{base_tree} "
            f"to {final_main}/{final_main_tree}; recompose the same PIP."
        )

    frontier = decode_record(frontier_token)
    lineage = validate_vit_lineage_record(frontier)
    resolution = frontier.get("frontier_resolution")
    if not isinstance(resolution, Mapping):
        raise RuntimeError("PRVITR_FRONTIER_RESOLUTION_MISSING")
    if str(resolution.get("current_predecessor_commit")) != base_sha:
        raise RuntimeError("PRVITR_FRONTIER_PREDECESSOR_COMMIT_MISMATCH")
    if str(resolution.get("current_predecessor_tree")) != base_tree:
        raise RuntimeError("PRVITR_FRONTIER_PREDECESSOR_TREE_MISMATCH")
    if str(resolution.get("prospective_result_tree")) != prospective_tree:
        raise RuntimeError("PRVITR_FRONTIER_RESULT_TREE_MISMATCH")
    recomposed = compose_pip_tree(
        Path.cwd(), base_tree, frontier["pip"]["logical_changes"]
    )
    if recomposed != prospective_tree:
        raise RuntimeError("PRVITR_QUALIFIED_PROSPECTIVE_TREE_RECOMPOSITION_MISMATCH")
    if git_tree(Path.cwd(), prospective_commit) != prospective_tree:
        raise RuntimeError("PRVITR_PROSPECTIVE_COMMIT_TREE_MISMATCH")

    preliminary_record = decode_record(preliminary_assurance_token)
    preliminary = assurance_generation_from_record(
        preliminary_record, expected_id=preliminary_assurance_id
    )
    if preliminary.pip_id != lineage.pip_id:
        raise RuntimeError("PRVITR_PRELIMINARY_ASSURANCE_PIP_MISMATCH")
    if preliminary.vit_generation_id != lineage.generation_id:
        raise RuntimeError("PRVITR_PRELIMINARY_ASSURANCE_GENERATION_MISMATCH")
    if preliminary.placement_id != lineage.placement_id:
        raise RuntimeError("PRVITR_PRELIMINARY_ASSURANCE_PLACEMENT_MISMATCH")
    if preliminary.prospective_result_tree != prospective_tree:
        raise RuntimeError("PRVITR_PRELIMINARY_ASSURANCE_RESULT_TREE_MISMATCH")

    a2_proof = build_a2_proof(
        frontier_lineage=frontier,
        workflow_run_id=os.environ.get("GITHUB_RUN_ID", ""),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", ""),
    )
    a2_proof_id = validate_a2_proof(a2_proof, frontier_lineage=frontier)
    final_assurance = FrontierIntegrationAssuranceGeneration(
        source_head_id=preliminary.source_head_id,
        source_head_commit=preliminary.source_head_commit,
        pip_id=preliminary.pip_id,
        vit_generation_id=preliminary.vit_generation_id,
        placement_id=preliminary.placement_id,
        predecessor_commit=preliminary.predecessor_commit,
        predecessor_tree=preliminary.predecessor_tree,
        prospective_result_tree=preliminary.prospective_result_tree,
        authority_manifest_id=preliminary.authority_manifest_id,
        dependency_frontier_id=preliminary.dependency_frontier_id,
        policy_id=preliminary.policy_id,
        a0_result_ids=preliminary.a0_result_ids,
        a1_proof_id=preliminary.a1_proof_id,
        assurance_stage="A2_QUALIFIED",
        a2_result_ids=(a2_proof_id,),
        source_run_ids=tuple(
            list(preliminary.source_run_ids)
            + [
                f"github-actions-run:{os.environ.get('GITHUB_RUN_ID', '')}:"
                f"attempt:{os.environ.get('GITHUB_RUN_ATTEMPT', '')}:"
                "job:OVC merge readiness"
            ]
        ),
        supersedes_assurance_generation_id=preliminary_assurance_id,
    )

    freeze = build_live_transaction_freeze(
        lineage_record=frontier,
        pr_number=pr_number,
        base_sha=base_sha,
        head_sha=source_head_sha,
        base_tree=base_tree,
        head_tree=prospective_tree,
        workflow_run_id=os.environ.get("GITHUB_RUN_ID", ""),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", ""),
    )
    # The historical freeze builder remains API-compatible, but this transaction
    # is observed in the late SIQ lane only after A2 has qualified the exact
    # prospective tree.  Do not mislabel it as routing-preflight evidence.
    freeze["freeze_provenance"]["source"] = "SIQ_PHYSICAL_LANE_AFTER_A2"

    # The late transaction freeze carries one closed, reconstructible ledger
    # envelope.  Post-merge A3 decodes, revalidates and persists each canonical
    # record separately through the existing content-addressed ReceiptStore.
    ledger_envelope = build_frontier_ledger_envelope(
        frontier_lineage=frontier,
        assurance_generation=final_assurance,
        a2_proof=a2_proof,
    )
    freeze["frontier_ledger_envelope"] = ledger_envelope
    freeze_marker = encode_freeze_marker(freeze)
    transaction = freeze["transaction"]
    if str(freeze.get("pip_id")) != lineage.pip_id:
        raise RuntimeError("PRVITR_TRANSACTION_PIP_MISMATCH")
    if str(freeze.get("generation_id")) != lineage.generation_id:
        raise RuntimeError("PRVITR_TRANSACTION_GENERATION_MISMATCH")
    if str(freeze.get("placement_id")) != lineage.placement_id:
        raise RuntimeError("PRVITR_TRANSACTION_PLACEMENT_MISMATCH")
    if str(transaction["expected_predecessor_commit"]) != base_sha:
        raise RuntimeError("PRVITR_TRANSACTION_PREDECESSOR_COMMIT_MISMATCH")
    if str(transaction["expected_predecessor_tree"]) != base_tree:
        raise RuntimeError("PRVITR_TRANSACTION_PREDECESSOR_TREE_MISMATCH")
    if str(transaction["expected_result_tree"]) != prospective_tree:
        raise RuntimeError("PRVITR_TRANSACTION_RESULT_TREE_MISMATCH")

    grt = ShadowGRTProof(
        result_tree=prospective_tree,
        proof_id=(
            f"exact-prospective-tree:{os.environ.get('GITHUB_RUN_ID', 'unknown')}:"
            f"{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
        ),
        constitution_id="GRT-v0.2-exact-prospective-tree",
        state="PASS",
    )
    source = SourceHead(**dict(resolution["source_head"]))
    receipt = FrontierIntegrationAdmissionReceipt(
        assurance_generation_id=final_assurance.assurance_generation_id,
        transaction_id=str(freeze["transaction_id"]),
        source_head_id=source.source_head_id,
        source_head_commit=source_head_sha,
        pip_id=lineage.pip_id,
        vit_generation_id=lineage.generation_id,
        placement_id=lineage.placement_id,
        predecessor_commit=base_sha,
        predecessor_tree=base_tree,
        prospective_result_tree=prospective_tree,
        grt_proof_binding_id=grt.proof_binding_id,
        disposition="FRONTIER_READY",
        reason_codes=(
            "SAME_PIP_SOURCE_HEAD_RETAINED",
            "A0_PIP_BOUND",
            "A1_RECOMPOSITION_EXACT",
            "A2_PROSPECTIVE_TREE_EXACT",
            "PREDECESSOR_STABLE_INSIDE_LEASE",
        ),
    )
    print(
        "OVC_FRONTIER_A2_PROOF="
        + json.dumps(a2_proof, sort_keys=True, separators=(",", ":"))
    )
    print(
        "OVC_FRONTIER_INTEGRATION_ASSURANCE_GENERATION="
        + json.dumps(asdict(final_assurance), sort_keys=True, separators=(",", ":"))
    )
    print(
        "OVC_FRONTIER_INTEGRATION_ADMISSION_RECEIPT="
        + json.dumps(asdict(receipt), sort_keys=True, separators=(",", ":"))
    )
    # Exactly one late physical transaction freeze is emitted for post-merge A3.
    print(freeze_marker)
    _write_output("admission_receipt_id", receipt.receipt_id)
    _write_output("assurance_generation_id", final_assurance.assurance_generation_id)
    _write_output("a2_proof_id", a2_proof_id)
    _write_output("grt_proof_binding_id", grt.proof_binding_id)
    _write_output("transaction_id", str(freeze["transaction_id"]))
    _write_output("frontier_ledger_envelope_id", str(ledger_envelope["record_id"]))
    print(
        f"OVC_FINAL_INTEGRATION_WINDOW_PASS: source_head={source_head_sha} "
        f"generation={lineage.generation_id} qualified prospective tree={prospective_tree} "
        f"while {base_ref} remained {base_sha}/{base_tree}."
    )
    print(
        f"OVC_SIQ_BASE_SENSITIVE_LEASE_RELEASED: {source_head_sha}; "
        "physical write remains serialized and A3 must prove the resulting main tree."
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
        print(f"::error title=PRVITR frontier-decoupled live admission::{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
