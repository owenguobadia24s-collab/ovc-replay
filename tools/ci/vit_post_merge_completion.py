#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import VitContractError
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
        "User-Agent": "ovc-vit-local-post-merge-completion/v1",
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


def _freeze_from_prewrite_logs(
    *, repository: str, head_sha: str, pr_number: int, token: str
) -> Mapping[str, Any]:
    owner, repo = repository.split("/", 1)
    query = urlencode(
        {
            "head_sha": head_sha,
            "event": "pull_request",
            "status": "completed",
            "per_page": "100",
        }
    )
    runs = _json(
        f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/runs?{query}",
        token,
    )
    if not isinstance(runs, Mapping):
        raise PostMergeCompletionError("workflow run response invalid")
    candidates = [
        row
        for row in runs.get("workflow_runs", [])
        if isinstance(row, Mapping)
        and row.get("name") == "tests"
        and row.get("conclusion") == "success"
    ]
    candidates.sort(key=lambda row: int(row.get("id", 0)), reverse=True)
    markers: list[Mapping[str, Any]] = []
    for run in candidates:
        run_id = int(run["id"])
        jobs = _json(
            f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/runs/{run_id}/jobs?per_page=100",
            token,
        )
        for job in jobs.get("jobs", []) if isinstance(jobs, Mapping) else []:
            if (
                isinstance(job, Mapping)
                and job.get("name") == "VIT routing preflight"
                and job.get("conclusion") == "success"
            ):
                text = _request_job_log(
                    f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/jobs/{int(job['id'])}/logs",
                    token,
                ).decode("utf-8", errors="replace")
                if FREEZE_MARKER_PREFIX in text:
                    markers.append(decode_freeze_marker(text))
        if markers:
            break
    if len(markers) != 1:
        raise PostMergeCompletionError(
            f"expected one pre-write transaction freeze for PR #{pr_number}, found {len(markers)}"
        )
    freeze = markers[0]
    if int(freeze.get("pr_number", -1)) != int(pr_number):
        raise PostMergeCompletionError("pre-write freeze PR mismatch")
    if str(freeze.get("head_sha")) != head_sha:
        raise PostMergeCompletionError("pre-write freeze head mismatch")
    return freeze


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
    freeze = _freeze_from_prewrite_logs(
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
            "physical tree does not match frozen transaction"
        )

    external_root = resolve_external_root(
        repository_root=repo_root,
        environ=os.environ,
        create=False,
    )
    receipt_store = ReceiptStore(external_root / "receipts")
    proof = complete_frozen_transaction(
        freeze=freeze,
        observed_commit=merge_sha,
        observed_tree=observed_tree,
        receipt_store=receipt_store,
        siq_receipts=_siq_observations(repository, head_sha, token),
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
