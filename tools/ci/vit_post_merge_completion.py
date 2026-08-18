#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from ovc.development.dsai3v_live_trace import build_observed_completion_trace
from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_frontier_decoupling import (
    validate_frontier_ledger_envelope,
)
from ovc.development.skills.vit_local_completion_executor import (
    FREEZE_MARKER_PREFIX,
    complete_frozen_transaction,
    decode_freeze_marker,
)
from ovc.development.skills.vit_materialisation import ReceiptStore
from ovc_evidence_store.external_root import resolve_external_root


class PostMergeCompletionError(RuntimeError):
    pass


class _StripAuthorizationOnRedirect(HTTPRedirectHandler):
    """Follow GitHub's signed log redirect without forwarding GitHub auth."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            redirected.remove_header("Authorization")
        return redirected


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise PostMergeCompletionError(proc.stderr.strip() or "git command failed")
    return proc.stdout.strip()


def _headers(token: str, *, accept: str = "application/vnd.github+json") -> dict[str, str]:
    return {
        "Accept": accept,
        "Authorization": f"Bearer {token}",
        "User-Agent": "ovc-vit-local-post-merge-completion/v2",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _request(url: str, token: str, *, accept: str = "application/vnd.github+json") -> bytes:
    try:
        with urlopen(Request(url, headers=_headers(token, accept=accept)), timeout=30) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise PostMergeCompletionError(f"GitHub request failed: {url}: {exc}") from exc


def _request_job_log(url: str, token: str) -> bytes:
    """Download one Actions job log through GitHub's authenticated signed redirect."""
    opener = build_opener(_StripAuthorizationOnRedirect())
    request = Request(url, headers=_headers(token))
    try:
        with opener.open(request, timeout=30) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise PostMergeCompletionError(f"GitHub job-log request failed: {url}: {exc}") from exc


def _json(url: str, token: str) -> Any:
    try:
        return json.loads(_request(url, token).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise PostMergeCompletionError(f"GitHub response was not JSON: {url}") from exc


def _associated_pr(repository: str, merge_sha: str, token: str) -> Mapping[str, Any]:
    owner, repo = repository.split("/", 1)
    rows = _json(
        f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/commits/{merge_sha}/pulls",
        token,
    )
    if not isinstance(rows, list):
        raise PostMergeCompletionError("associated PR response is not a list")
    candidates = [
        row
        for row in rows
        if isinstance(row, Mapping)
        and str((row.get("base") or {}).get("ref")) == "main"
        and bool(row.get("merged_at"))
    ]
    if len(candidates) != 1:
        raise PostMergeCompletionError(
            f"expected exactly one merged main PR for {merge_sha}, found {len(candidates)}"
        )
    return candidates[0]


def _pr_head_workflow_observations(
    repository: str,
    head_sha: str,
    token: str,
) -> tuple[tuple[Mapping[str, Any], ...], dict[int, tuple[Mapping[str, Any], ...]]]:
    """Fetch completed PR-head Actions runs/jobs for observed DEVOBS timing only."""
    owner, repo = repository.split("/", 1)
    query = urlencode(
        {
            "head_sha": head_sha,
            "event": "pull_request",
            "status": "completed",
            "per_page": "100",
        }
    )
    payload = _json(
        f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/runs?{query}",
        token,
    )
    if not isinstance(payload, Mapping):
        raise PostMergeCompletionError("workflow timing response invalid")
    runs = tuple(
        dict(row)
        for row in payload.get("workflow_runs", [])
        if isinstance(row, Mapping)
    )
    jobs_by_run: dict[int, tuple[Mapping[str, Any], ...]] = {}
    for run in runs:
        try:
            run_id = int(run["id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PostMergeCompletionError("workflow timing run id invalid") from exc
        jobs_payload = _json(
            f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/runs/{run_id}/jobs?per_page=100",
            token,
        )
        if not isinstance(jobs_payload, Mapping):
            raise PostMergeCompletionError("workflow timing jobs response invalid")
        jobs_by_run[run_id] = tuple(
            dict(job)
            for job in jobs_payload.get("jobs", [])
            if isinstance(job, Mapping)
        )
    return runs, jobs_by_run


def _workflow_runs_for_head(
    *, repository: str, head_sha: str, token: str
) -> list[Mapping[str, Any]]:
    owner, repo = repository.split("/", 1)
    query = urlencode(
        {
            "head_sha": head_sha,
            "event": "pull_request",
            "status": "completed",
            "per_page": "100",
        }
    )
    payload = _json(
        f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/runs?{query}",
        token,
    )
    if not isinstance(payload, Mapping):
        raise PostMergeCompletionError("workflow run response invalid")
    return [
        row
        for row in payload.get("workflow_runs", [])
        if isinstance(row, Mapping)
    ]


def _freeze_markers_from_job(
    *, repository: str, job: Mapping[str, Any], token: str
) -> list[Mapping[str, Any]]:
    owner, repo = repository.split("/", 1)
    text = _request_job_log(
        f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/jobs/{int(job['id'])}/logs",
        token,
    ).decode("utf-8", errors="replace")
    tokens = re.findall(
        re.escape(FREEZE_MARKER_PREFIX) + r"([A-Za-z0-9_\-=]+)",
        text,
    )
    return [
        decode_freeze_marker(FREEZE_MARKER_PREFIX + marker_token)
        for marker_token in tokens
    ]


def _freeze_from_physical_lane_logs(
    *, repository: str, head_sha: str, pr_number: int, token: str
) -> Mapping[str, Any]:
    """Resolve the single late SIQ physical transaction freeze.

    Frontier-decoupled transactions are emitted only by the successful
    ``OVC merge readiness`` job after the physical lease and A2 exact prospective
    assurance.  The historical tests/VIT-routing location remains a read-only
    fallback for already-merged pre-cutover packets.
    """

    runs = _workflow_runs_for_head(
        repository=repository, head_sha=head_sha, token=token
    )
    search_order = (
        ("OVC tiered test selection shadow", "OVC merge readiness"),
        ("tests", "VIT routing preflight"),  # historical recovery only
    )
    for workflow_name, job_name in search_order:
        candidates = [
            row
            for row in runs
            if row.get("name") == workflow_name
            and row.get("conclusion") == "success"
        ]
        candidates.sort(key=lambda row: int(row.get("id", 0)), reverse=True)
        for run in candidates:
            owner, repo = repository.split("/", 1)
            jobs = _json(
                f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/runs/{int(run['id'])}/jobs?per_page=100",
                token,
            )
            matching_jobs = [
                job
                for job in (jobs.get("jobs", []) if isinstance(jobs, Mapping) else [])
                if isinstance(job, Mapping)
                and job.get("name") == job_name
                and job.get("conclusion") == "success"
            ]
            matching_jobs.sort(key=lambda row: int(row.get("id", 0)), reverse=True)
            for job in matching_jobs:
                markers = _freeze_markers_from_job(
                    repository=repository, job=job, token=token
                )
                if not markers:
                    continue
                if len(markers) != 1:
                    raise PostMergeCompletionError(
                        f"expected one physical transaction freeze in {workflow_name}/{job_name}, found {len(markers)}"
                    )
                freeze = markers[0]
                if int(freeze.get("pr_number", -1)) != int(pr_number):
                    raise PostMergeCompletionError("physical transaction freeze PR mismatch")
                if str(freeze.get("head_sha")) != head_sha:
                    raise PostMergeCompletionError("physical transaction freeze source-head mismatch")
                return freeze
    raise PostMergeCompletionError(
        f"expected one late physical transaction freeze for PR #{pr_number}, found none"
    )


def _persist_frontier_ledger(
    *, freeze: Mapping[str, Any], receipt_store: ReceiptStore
) -> Mapping[str, str] | None:
    """Persist the canonical frontier lineage/A2 assurance records after A3.

    Historical pre-cutover freezes legitimately omit this envelope.  New
    frontier-decoupled freezes fail closed when an envelope is present but invalid.
    """

    raw = freeze.get("frontier_ledger_envelope")
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise PostMergeCompletionError("frontier ledger envelope is not an object")
    decoded = validate_frontier_ledger_envelope(raw)
    receipt_store.put_record(
        decoded["frontier_lineage"], decoded["frontier_lineage_record_id"]
    )
    receipt_store.put_record(
        decoded["assurance_generation"], decoded["assurance_generation_id"]
    )
    receipt_store.put_record(decoded["a2_proof"], decoded["a2_proof_id"])
    receipt_store.put_record(
        decoded["envelope_record"], decoded["envelope_record_id"]
    )
    return {
        "frontier_lineage_record_id": str(decoded["frontier_lineage_record_id"]),
        "assurance_generation_id": str(decoded["assurance_generation_id"]),
        "a2_proof_id": str(decoded["a2_proof_id"]),
        "frontier_ledger_envelope_id": str(decoded["envelope_record_id"]),
    }


def _check_runs(repository: str, head_sha: str, token: str) -> list[Mapping[str, Any]]:
    owner, repo = repository.split("/", 1)
    rows = _json(
        f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/commits/{head_sha}/check-runs?per_page=100",
        token,
    )
    return [
        row
        for row in (rows.get("check_runs", []) if isinstance(rows, Mapping) else [])
        if isinstance(row, Mapping)
    ]


def _siq_observations(repository: str, head_sha: str, token: str) -> tuple[Mapping[str, Any], ...]:
    checks = _check_runs(repository, head_sha, token)
    wanted = {
        "SIQ READY admission": "SIQ_READY",
        "OVC merge readiness": "PASS",
    }
    result = []
    for name, status in wanted.items():
        matches = sorted(
            (
                row
                for row in checks
                if row.get("name") == name
                and row.get("status") == "completed"
                and row.get("conclusion") == "success"
            ),
            key=lambda row: int(row.get("id", 0)),
            reverse=True,
        )
        if not matches:
            raise PostMergeCompletionError(f"required observed check missing: {name}")
        row = matches[0]
        logical = {
            "schema": "ovc-github-check-observation/v1",
            "check_run_id": int(row["id"]),
            "name": name,
            "head_sha": head_sha,
            "status": status,
            "conclusion": "success",
        }
        result.append(
            {
                **logical,
                "record_id": canonical_sha256(
                    logical, role="DSAI3V_GITHUB_CHECK_OBSERVATION"
                ),
            }
        )
    return tuple(result)


def run(repo_root: Path, merge_sha: str) -> Mapping[str, Any]:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if "/" not in repository or not token:
        raise PostMergeCompletionError("GITHUB_REPOSITORY/GITHUB_TOKEN are required")
    merge_sha = _git(repo_root, "rev-parse", merge_sha)
    observed_tree = _git(repo_root, "rev-parse", f"{merge_sha}^{{tree}}")
    observed_parent = _git(repo_root, "rev-parse", f"{merge_sha}^")

    pr = _associated_pr(repository, merge_sha, token)
    pr_number = int(pr["number"])
    head_sha = str((pr.get("head") or {}).get("sha") or "")
    merged_at = str(pr.get("merged_at") or "")
    if not merged_at:
        raise PostMergeCompletionError("associated PR merged_at is required")
    freeze = _freeze_from_physical_lane_logs(
        repository=repository,
        head_sha=head_sha,
        pr_number=pr_number,
        token=token,
    )
    transaction = freeze["transaction"]
    if str(transaction["expected_predecessor_commit"]) != observed_parent:
        raise PostMergeCompletionError(
            "physical predecessor does not match frozen transaction"
        )
    if str(transaction["expected_result_tree"]) != observed_tree:
        raise PostMergeCompletionError(
            "physical tree does not match frozen qualified prospective result"
        )

    external_root = resolve_external_root(
        repository_root=repo_root,
        environ=os.environ,
        create=False,
    )
    receipt_store = ReceiptStore(external_root / "receipts")

    trace_bundle: Mapping[str, Any] | None = None
    context = freeze.get("completion_context")
    if isinstance(context, Mapping):
        try:
            workflow_runs, jobs_by_run = _pr_head_workflow_observations(
                repository,
                head_sha,
                token,
            )
            trace_bundle = build_observed_completion_trace(
                programme_id=str(context["programme_id"]),
                packet_id=str(context["packet_id"]),
                pr_number=pr_number,
                head_sha=head_sha,
                merged_at_utc=merged_at,
                workflow_runs=workflow_runs,
                jobs_by_run=jobs_by_run,
            )
        except (PostMergeCompletionError, ValueError, KeyError) as exc:
            print(
                "::warning title=DEVOBS routine trace unavailable::"
                f"observed workflow timing could not be attached; canonical completion remains fail-honest: {exc}",
                flush=True,
            )

    if trace_bundle is not None:
        for event in trace_bundle.get("trace_events", []):
            if not isinstance(event, Mapping):
                raise PostMergeCompletionError("DEVOBS trace event invalid")
            record_id = event.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                raise PostMergeCompletionError("DEVOBS trace event id missing")
            receipt_store.put(dict(event), record_id)

    frontier_ledger_ids = _persist_frontier_ledger(
        freeze=freeze, receipt_store=receipt_store
    )

    proof = complete_frozen_transaction(
        freeze=freeze,
        observed_commit=merge_sha,
        observed_tree=observed_tree,
        receipt_store=receipt_store,
        siq_receipts=_siq_observations(repository, head_sha, token),
        trace_summary=(
            trace_bundle.get("trace_summary") if trace_bundle is not None else None
        ),
        async_assurance_metrics=(
            trace_bundle.get("async_assurance_metrics")
            if trace_bundle is not None
            else None
        ),
    )
    safe = {
        "schema": proof["schema"],
        "proof_id": proof["proof_id"],
        "transaction_id": proof["transaction_id"],
        "observed_commit": proof["observed_commit"],
        "observed_tree": proof["observed_tree"],
        "exact_tree_equal": proof["exact_tree_equal"],
        "four_content_addressed_receipts_present": proof[
            "four_content_addressed_receipts_present"
        ],
        "receipt_ids": proof["receipt_ids"],
        "authority_effect": proof["authority_effect"],
    }
    if frontier_ledger_ids is not None:
        safe["frontier_ledger_ids"] = dict(frontier_ledger_ids)
    if proof.get("trace_summary_id"):
        safe["trace_summary_id"] = proof["trace_summary_id"]
    print("OVC_VIT_POST_MERGE_COMPLETION_PROOF " + json.dumps(safe, sort_keys=True))
    return safe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--merge-sha", required=True)
    args = parser.parse_args()
    try:
        run(Path(args.repo_root).resolve(), args.merge_sha)
        return 0
    except (PostMergeCompletionError, VitContractError, ValueError, KeyError) as exc:
        print(
            "::error title=DSAI3V post-merge completion failed::"
            f"OVC_VIT_POST_MERGE_COMPLETION_FAILED: {exc}",
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
