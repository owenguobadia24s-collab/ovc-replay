#!/usr/bin/env python3
"""Run A2 on an exact prospective VIT tree while physical main is frozen.

The source PR head is provenance only.  The checked-out commit is a deterministic
local-only commit whose tree equals the qualified VIT prospective result.  The
lease freezes the physical predecessor, generation and result tree; a predecessor
move terminates A2 and requires recomposition of the same PIP, not a replacement PR.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from typing import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


EXIT_BASE_MOVED = 86
EXIT_LEASE_OBSERVABILITY = 87
DEFAULT_POLL_SECONDS = 3.0
MAX_CONSECUTIVE_OBSERVATION_FAILURES = 3


class LeaseError(RuntimeError):
    """Raised when a required lease cannot be observed or validated."""


def _truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise LeaseError(f"required environment variable {name} is empty")
    return value


def _current_branch_sha(
    *,
    repository: str,
    branch: str,
    token: str,
    timeout_seconds: float = 15.0,
) -> str:
    if "/" not in repository:
        raise LeaseError(f"invalid GITHUB_REPOSITORY value {repository!r}")
    owner, repo = repository.split("/", 1)
    url = (
        "https://api.github.com/repos/"
        f"{quote(owner, safe='')}/{quote(repo, safe='')}/branches/{quote(branch, safe='')}"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ovc-required-assurance-lease/v2",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LeaseError(f"cannot observe {repository}:{branch}: {exc}") from exc
    try:
        sha = str(payload["commit"]["sha"]).strip()
    except (KeyError, TypeError) as exc:
        raise LeaseError("branch response did not contain commit.sha") from exc
    if len(sha) != 40:
        raise LeaseError(f"branch response returned invalid SHA {sha!r}")
    return sha


def _git_rev_parse(value: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", value],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LeaseError(
            f"cannot resolve {value}: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def _terminate_process_group(process: subprocess.Popen[object]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if process.poll() is None:
            try:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except ProcessLookupError:
                pass
            process.wait(timeout=5)


def run_with_lease(command: Sequence[str]) -> int:
    if not command:
        raise LeaseError("no command supplied after --")

    if not _truthy(os.environ.get("OVC_LEASE_REQUIRED")):
        return subprocess.call(list(command))

    base_sha = _required_env("OVC_LEASE_BASE_SHA")
    source_head_sha = os.environ.get("OVC_LEASE_SOURCE_HEAD_SHA", "").strip()
    prospective_commit = (
        os.environ.get("OVC_LEASE_PROSPECTIVE_COMMIT_SHA", "").strip()
        or os.environ.get("OVC_LEASE_HEAD_SHA", "").strip()
    )
    result_tree = os.environ.get("OVC_LEASE_RESULT_TREE", "").strip()
    branch = _required_env("OVC_LEASE_BRANCH")
    repository = _required_env("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN", "")
    poll_seconds = float(os.environ.get("OVC_LEASE_POLL_SECONDS", DEFAULT_POLL_SECONDS))

    if len(prospective_commit) != 40:
        raise LeaseError("OVC_LEASE_PROSPECTIVE_COMMIT_SHA is invalid")
    if source_head_sha and len(source_head_sha) != 40:
        raise LeaseError("OVC_LEASE_SOURCE_HEAD_SHA is invalid")
    if result_tree and len(result_tree) != 40:
        raise LeaseError("OVC_LEASE_RESULT_TREE is invalid")

    checkout = _git_rev_parse("HEAD")
    if checkout != prospective_commit:
        raise LeaseError(
            "checked-out prospective generation does not match shared lease: "
            f"HEAD={checkout}, prospective_commit={prospective_commit}, "
            f"source_head={source_head_sha or 'UNRECORDED'}"
        )
    observed_tree = _git_rev_parse("HEAD^{tree}")
    if result_tree and observed_tree != result_tree:
        raise LeaseError(
            "checked-out prospective commit tree does not match lease result tree: "
            f"observed={observed_tree}, expected={result_tree}"
        )

    current = _current_branch_sha(
        repository=repository,
        branch=branch,
        token=token,
    )
    if current != base_sha:
        print(
            "::error title=VIT predecessor moved before A2::"
            "PREDECESSOR_MOVED: "
            f"{branch} moved from {base_sha} to {current} before A2 started for "
            f"source {source_head_sha or 'UNRECORDED'}; recompose the same PIP.",
            flush=True,
        )
        return EXIT_BASE_MOVED

    popen_kwargs: dict[str, object] = {}
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True
    elif hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    process = subprocess.Popen(list(command), **popen_kwargs)
    consecutive_observation_failures = 0

    while process.poll() is None:
        time.sleep(max(0.5, poll_seconds))
        try:
            current = _current_branch_sha(
                repository=repository,
                branch=branch,
                token=token,
            )
        except LeaseError as exc:
            consecutive_observation_failures += 1
            print(
                "::warning title=VIT predecessor observation retry::"
                f"{exc}; attempt {consecutive_observation_failures}/"
                f"{MAX_CONSECUTIVE_OBSERVATION_FAILURES}.",
                flush=True,
            )
            if consecutive_observation_failures < MAX_CONSECUTIVE_OBSERVATION_FAILURES:
                continue
            _terminate_process_group(process)
            print(
                "::error title=VIT physical lease unobservable::"
                "OVC_REQUIRED_ASSURANCE_LEASE_OBSERVABILITY_FAILED: "
                f"could not prove {branch}@{base_sha} remained the physical predecessor; "
                "A2 was terminated fail-closed.",
                flush=True,
            )
            return EXIT_LEASE_OBSERVABILITY

        consecutive_observation_failures = 0
        if current != base_sha:
            _terminate_process_group(process)
            print(
                "::error title=VIT predecessor moved during A2::"
                "OVC_REQUIRED_ASSURANCE_LEASE_INVALIDATED: PREDECESSOR_MOVED: "
                f"{branch} moved from {base_sha} to {current} while A2 was running "
                f"for source {source_head_sha or 'UNRECORDED'}. The exact prospective "
                "run was terminated; recompose the same PIP on the new frontier.",
                flush=True,
            )
            return EXIT_BASE_MOVED

    return int(process.returncode or 0)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    try:
        return run_with_lease(command)
    except (LeaseError, ValueError) as exc:
        print(
            "::error title=Required VIT lease invalid::"
            f"OVC_REQUIRED_ASSURANCE_LEASE_INVALID: {exc}",
            flush=True,
        )
        return EXIT_LEASE_OBSERVABILITY


if __name__ == "__main__":
    raise SystemExit(main())
