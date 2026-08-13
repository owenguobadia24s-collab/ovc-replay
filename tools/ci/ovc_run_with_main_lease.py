#!/usr/bin/env python3
"""Run one required-assurance command while an exact main-bound lease remains valid.

The lease is read-only and supplied by the final-integration admission job as
``{head_sha, base_sha, base_branch}``.  The child command is never started when
the current base already differs.  If the base advances while the command is
running, the child process group is terminated and the recognised
``OVC_BASE_MOVED_DURING_READINESS`` reason is emitted so the existing bounded
reconciliation/requeue path can create a fresh immutable candidate.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
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
        "User-Agent": "ovc-required-assurance-lease/v1",
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


def _checkout_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LeaseError(f"cannot resolve checked-out HEAD: {completed.stderr.strip()}")
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
    head_sha = _required_env("OVC_LEASE_HEAD_SHA")
    branch = _required_env("OVC_LEASE_BRANCH")
    repository = _required_env("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN", "")
    poll_seconds = float(os.environ.get("OVC_LEASE_POLL_SECONDS", DEFAULT_POLL_SECONDS))

    checkout = _checkout_head()
    if checkout != head_sha:
        raise LeaseError(
            "checked-out candidate does not match shared lease: "
            f"HEAD={checkout}, lease_head={head_sha}"
        )

    current = _current_branch_sha(
        repository=repository,
        branch=branch,
        token=token,
    )
    if current != base_sha:
        print(
            "::error title=Required assurance lease stale before command::"
            "OVC_BASE_MOVED_BEFORE_READINESS: "
            f"{branch} moved from lease base {base_sha} to {current} before "
            f"required command for {head_sha} started.",
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
                "::warning title=Required assurance lease observation retry::"
                f"{exc}; attempt "
                f"{consecutive_observation_failures}/"
                f"{MAX_CONSECUTIVE_OBSERVATION_FAILURES}.",
                flush=True,
            )
            if consecutive_observation_failures < MAX_CONSECUTIVE_OBSERVATION_FAILURES:
                continue
            _terminate_process_group(process)
            print(
                "::error title=Required assurance lease unobservable::"
                "OVC_REQUIRED_ASSURANCE_LEASE_OBSERVABILITY_FAILED: "
                f"could not prove {branch}@{base_sha} remained current for "
                f"{head_sha}; required work was terminated fail-closed.",
                flush=True,
            )
            return EXIT_LEASE_OBSERVABILITY

        consecutive_observation_failures = 0
        if current != base_sha:
            _terminate_process_group(process)
            print(
                "::error title=Required assurance lease invalidated::"
                "OVC_REQUIRED_ASSURANCE_LEASE_INVALIDATED: "
                "OVC_BASE_MOVED_DURING_READINESS: "
                f"{branch} moved from {base_sha} to {current} while required "
                f"assurance was running for {head_sha}. The stale command was "
                "terminated; create a fresh immutable reconciliation candidate.",
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
            "::error title=Required assurance lease invalid::"
            f"OVC_REQUIRED_ASSURANCE_LEASE_INVALID: {exc}",
            flush=True,
        )
        return EXIT_LEASE_OBSERVABILITY


if __name__ == "__main__":
    raise SystemExit(main())
